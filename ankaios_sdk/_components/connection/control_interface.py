# Copyright (c) 2024 Elektrobit Automotive GmbH
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
This script defines the ControlInterfaceConnection class that handles
the writing and reading of data to and from the Ankaios control
interface.

Classes
-------

- :class:`ControlInterfaceConnection`:
    Handles the interaction with the Ankaios control interface.

Enums
-----

- :class:`ControlInterfaceState`:
    Represents the state of the control interface connection.

Usage
-----

- Create a ControlInterfaceConnection instance, connect and disconnect.
    .. code-block:: python

        ci = ControlInterfaceConnection(<callbacks from Ankaios>)
        ci.connect()
        ...
        ci.disconnect()

- Change the state of the control interface connection.
    .. code-block:: python

        ci.change_state(ControlInterfaceState.TERMINATED)
"""


__all__ = ["ControlInterfaceConnection", "ControlInterfaceState"]


import os
import select
import threading
from typing import Callable
from enum import Enum
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from ..._protos import _control_api
from ..request import Request
from ..response import Response, ResponseException, ResponseType
from ...exceptions import ConnectionException, ConnectionClosedException
from ...utils import DEFAULT_CONTROL_INTERFACE_PATH, ANKAIOS_VERSION
from .connection import Connection


class ControlInterfaceState(Enum):
    """The state of the control interface connection."""

    INITIALIZED = 1
    "(int): Connection initialized state."
    CONNECTED = 2
    "(int): Connection established state."
    TERMINATED = 3
    "(int): Connection stopped state."
    AGENT_DISCONNECTED = 4
    "(int): Agent disconnected state."
    CONNECTION_CLOSED = 5
    "(int): Connection closed state."

    def __str__(self) -> str:
        """
        Returns the string representation of the state.

        :returns: The state as a string.
        :rtype: str
        """
        return self.name


# pylint: disable=too-many-instance-attributes
class ControlInterfaceConnection(Connection):
    """
    This class handles the interaction with the Ankaios control interface.
    It provides methods to send and receive data to and from the control
    interface pipes.
    """

    ANKAIOS_CONTROL_INTERFACE_BASE_PATH = DEFAULT_CONTROL_INTERFACE_PATH
    "(str): The base path for the Ankaios control interface."

    AGENT_RECONNECT_INTERVAL_SEC = 1
    "(int): Seconds to wait between hello retries while the agent is gone."

    _ACTIVE_STATES = (
        ControlInterfaceState.INITIALIZED,
        ControlInterfaceState.CONNECTED,
        ControlInterfaceState.AGENT_DISCONNECTED,
    )
    "(tuple): The states in which a reader thread is running."

    def __init__(
        self,
        add_response_callback: Callable,
        add_log_callback: Callable,
        add_event_callback: Callable,
    ) -> None:
        """
        Initialize the ControlInterfaceConnection object. This is used
        to interact with the control interface.

        :param add_response_callback: The callback function to add
            a response to the Ankaios class.
        :type add_response_callback: Callable
        :param add_log_callback: The callback function to add
            a log to the Ankaios class.
        :type add_log_callback: Callable
        :param add_event_callback: The callback function to add
            an event to the Ankaios class.
        :type add_event_callback: Callable
        """
        super().__init__(
            add_response_callback, add_log_callback, add_event_callback
        )
        # The state of the control interface must not be changed directly.
        # Use the change_state method instead.
        self._state = ControlInterfaceState.TERMINATED
        # Guards _state, _output_file and _read_thread. Never held across
        # a fifo write or a thread join.
        self._lock = threading.Lock()
        # Held across every framed write and around closing the output
        # file, so a write can never be split by another writer or have
        # its file closed underneath it. Never taken while holding _lock.
        self._write_lock = threading.Lock()
        self._output_file = None
        self._read_thread = None
        self._disconnect_event = threading.Event()

    @property
    def connected(self) -> bool:
        """
        Check if the control interface is connected.

        :returns: True if connected, False otherwise.
        :rtype: bool
        """
        return self._state == ControlInterfaceState.CONNECTED

    def connect(self) -> None:
        """
        Connect to the control interface by starting to read
        from the input fifo and opening the output fifo.

        :raises ConnectionException: If an error occurred.
        """
        with self._lock:
            if self._state in self._ACTIVE_STATES:
                raise ConnectionException("Already connected.")
            # Only one reader thread may ever run: a previous one that did
            # not stop in time would otherwise read the same fifo and tear
            # down this connection's resources when it finally exits.
            if self._read_thread is not None and self._read_thread.is_alive():
                raise ConnectionException(
                    "Previous connection is still shutting down."
                )

            if not os.path.exists(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input"
            ):
                raise ConnectionException(
                    "Control interface input fifo does not exist."
                )

            if not os.path.exists(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output"
            ):
                raise ConnectionException(
                    "Control interface output fifo does not exist."
                )

            # pylint: disable=consider-using-with
            try:
                self._output_file = open(
                    f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output",
                    "ab",
                )
            except Exception as e:
                self._logger.error(
                    "Error while opening output fifo: %s", e
                )
                raise ConnectionException(
                    "Error while opening output fifo."
                ) from e

            # A previous disconnect leaves the event set; clear it so the
            # new reader thread is not stopped immediately.
            self._disconnect_event.clear()
            # Set before the reader starts, so a reader that fails right
            # away cannot have its TERMINATED overwritten.
            self._set_state(ControlInterfaceState.INITIALIZED)
            self._read_thread = threading.Thread(
                target=self._read_from_control_interface, daemon=True
            )
            self._read_thread.start()

        # Sent without holding the lock: the hello write can block on
        # the fifo and must not hold off a concurrent disconnect().
        self._send_initial_hello()

    def disconnect(self) -> None:
        """
        Disconnect from the control interface.
        """
        with self._lock:
            if self._state not in self._ACTIVE_STATES:
                self._logger.debug("Already disconnected.")
                return

            self._logger.debug("Disconnecting..")
            self._disconnect_event.set()
            output_file = self._detach_resources()
            # Kept even if it does not stop in time, so connect() can
            # refuse to start a second reader while it is still alive.
            read_thread = self._read_thread

        # The resources are detached, so the slow teardown runs unlocked.
        if read_thread is not None:
            read_thread.join(timeout=2)
            if read_thread.is_alive():
                self._logger.error("Read thread did not stop.")
        self._close_output_file(output_file)

    def _cleanup(self) -> None:
        """
        Clean up the resources. Called by the reader thread when it
        stops; a no-op if disconnect() already cleaned up.
        """
        with self._lock:
            output_file = self._detach_resources()
        self._close_output_file(output_file)
        self._logger.debug("Cleanup happened")

    def _detach_resources(self):
        """
        Marks the connection as terminated and detaches the output
        file from it. The caller must hold the lock.

        :returns: The detached output file (or None if already
            detached), to be closed once the lock is released.
        """
        self._set_state(ControlInterfaceState.TERMINATED)
        output_file, self._output_file = self._output_file, None
        return output_file

    def _close_output_file(self, output_file) -> None:
        """
        Closes a detached output file, waiting for any write in
        progress on it to finish first.

        :param output_file: The output file to close, or None.
        """
        if output_file is None:
            return
        with self._write_lock:
            output_file.close()

    def change_state(
        self, state: ControlInterfaceState, info: str = None
    ) -> None:
        """
        Change the state of the control interface.

        :param state: The new state.
        :type state: ControlInterfaceState
        :param info: Additional information about the state change.
        :type info: str
        """
        with self._lock:
            self._set_state(state, info)

    def _change_state_from_reader(
        self, state: ControlInterfaceState, info: str = None
    ) -> None:
        """
        Change the state of the control interface on behalf of the
        reader thread, unless a disconnect was requested, so the reader
        cannot overwrite the TERMINATED state set by disconnect().

        :param state: The new state.
        :type state: ControlInterfaceState
        :param info: Additional information about the state change.
        :type info: str
        """
        with self._lock:
            if not self._disconnect_event.is_set():
                self._set_state(state, info)

    def _set_state(
        self, state: ControlInterfaceState, info: str = None
    ) -> None:
        """
        Change the state of the control interface. The caller must
        hold the lock.

        :param state: The new state.
        :type state: ControlInterfaceState
        :param info: Additional information about the state change.
        :type info: str
        """
        if state == self._state:
            self._logger.debug("State is already %s.", state)
            return
        if self._state == ControlInterfaceState.CONNECTION_CLOSED:
            self._logger.debug("State CONNECTION_CLOSED is unrecoverable.")
            return
        self._state = state
        if info is None:
            self._logger.debug("State changed to %s.", state)
        else:
            self._logger.debug("State changed to %s: %s", state, info)

    # pylint: disable=too-many-statements, too-many-branches
    def _read_from_control_interface(self) -> None:
        """
        Reads from the control interface input fifo.
        This is meant to be run in a separate thread.
        The responses are then sent to the Ankaios class to be handled.
        The input fifo is opened and closed by this thread alone.

        :raises ConnectionException: If an error occurs
            while reading the fifo.
        """
        # The pragma: no cover is used on small checks that are not expected
        # to fail. This method is difficult to test and testing each check
        # would be redundant.

        # pylint: disable=invalid-name
        MOST_SIGNIFICANT_BIT_MASK = 0b10000000

        # pylint: disable=consider-using-with
        try:
            input_file = open(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb"
            )
        except Exception as e:
            self._logger.error("Error while opening input fifo: %s", e)
            # Runs on the reader thread itself, so it must tear down
            # directly instead of calling disconnect() (which would join
            # the current thread).
            self._disconnect_event.set()
            self._cleanup()
            raise ConnectionException(
                "Error while opening input fifo."
            ) from e
        os.set_blocking(input_file.fileno(), False)

        try:
            self._logger.debug("Started reading from the input pipe.")
            while not self._disconnect_event.is_set():
                # The loop continues when data is available or when the
                # timeout of 1 second is reached.
                ready, _, _ = select.select([input_file], [], [], 1)
                if not ready:  # pragma: no cover
                    continue

                # Buffer for reading in the byte size of the proto msg
                varint_buffer = bytearray()
                while not self._disconnect_event.is_set():
                    # Consume byte for byte
                    next_byte = input_file.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    varint_buffer += next_byte
                    # Check if we reached the last byte
                    if next_byte[0] & MOST_SIGNIFICANT_BIT_MASK == 0:
                        break

                if not varint_buffer:
                    self._change_state_from_reader(
                        ControlInterfaceState.AGENT_DISCONNECTED
                    )
                    self._logger.warning(
                        "Nothing to read from the input fifo pipe."
                    )
                    self._agent_gone_routine()
                    continue
                # Decode the varint and receive the proto msg length
                msg_len, _ = _DecodeVarint(varint_buffer, 0)

                # Buffer for the proto msg itself
                msg_buf = bytearray()
                for _ in range(msg_len):
                    # Read the message according to the length
                    next_byte = input_file.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    msg_buf += next_byte

                try:
                    response = self._decode_response(bytes(msg_buf))
                except ResponseException as e:  # pragma: no cover
                    self._logger.error("Error while reading: %s", e)
                    continue

                # Handle the response
                self._handle_response(response)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._logger.error("Error while reading fifo file: %s", e)
        finally:
            input_file.close()
            self._cleanup()

    @staticmethod
    def _decode_response(message_buffer: bytes) -> Response:
        """
        Decodes a message read from the control interface's own
        envelope (a length-delimited `_control_api.FromAnkaios`
        message) into a Response, owning the control-interface-
        specific envelope unwrapping so that Response itself only
        needs to know about the shared ank_base.Response payload.

        :param message_buffer: The received message buffer.
        :type message_buffer: bytes

        :returns: The decoded Response object.
        :rtype: Response

        :raises ResponseException: If there is an error parsing the
            message buffer, or if it contains none of the expected
            variants.
        """
        from_ankaios = _control_api.FromAnkaios()
        try:
            from_ankaios.ParseFromString(message_buffer)
        except Exception as e:
            raise ResponseException(f"Parsing error: '{e}'") from e
        if from_ankaios.HasField("response"):
            return Response._from_ank_base_response(from_ankaios.response)
        if from_ankaios.HasField("controlInterfaceAccepted"):
            return Response._control_interface_accepted()
        if from_ankaios.HasField("connectionClosed"):
            return Response._connection_closed(
                from_ankaios.connectionClosed.reason
            )
        raise ResponseException(  # pragma: no cover
            "Invalid response type."
        )

    def _handle_response(self, response: Response) -> None:
        """
        Handle the response received from the control interface.

        :param response: The response object to handle.
        :type response: Response

        :raises ConnectionException:
            If the response is not in a valid state.
        :raises ConnectionClosedException: If the connection is closed.
        """
        # Handle the initialized state
        if self._state == ControlInterfaceState.INITIALIZED:
            if (
                response.content_type
                == ResponseType.CONTROL_INTERFACE_ACCEPTED
            ):
                self._logger.debug(
                    "Received control interface accepted response."
                )
                self._change_state_from_reader(
                    ControlInterfaceState.CONNECTED
                )
            elif response.content_type == ResponseType.CONNECTION_CLOSED:
                self._add_response_callback(response)
                self._change_state_from_reader(
                    ControlInterfaceState.CONNECTION_CLOSED,
                    response.content,
                )
                raise ConnectionClosedException(response.content)
            else:
                self._logger.error(
                    "Received response %s, but expected "
                    "CONTROL_INTERFACE_ACCEPTED. Ignoring..",
                    response.content_type,
                )

        # Handle the connected state
        elif self._state == ControlInterfaceState.CONNECTED:
            if self._dispatch_response(response):
                return

            # Check if the response is connection closed in order to
            # terminate the thread.
            if response.content_type == ResponseType.CONNECTION_CLOSED:
                self._change_state_from_reader(
                    ControlInterfaceState.CONNECTION_CLOSED,
                    response.content,
                )
                raise ConnectionClosedException(response.content)
            if (
                response.content_type
                == ResponseType.CONTROL_INTERFACE_ACCEPTED
            ):
                self._logger.warning(
                    "Received unexpected "
                    "control interface accepted response."
                )
        else:
            self._logger.warning(
                "Received response %s, but not in a valid state. "
                "Ignoring..",
                response.content_type,
            )

    def _agent_gone_routine(self) -> None:
        """
        Method will be called when the agent is gone.
        It will attempt to write the hello message to the agent
        until the agent is connected or a disconnect is requested.
        """
        while (
            not self._disconnect_event.is_set()
            and self._state == ControlInterfaceState.AGENT_DISCONNECTED
        ):
            try:
                self._send_initial_hello()
            except BrokenPipeError as _:
                self._logger.warning("Waiting for the agent..")
                # Wait on the event so a disconnect wakes us immediately.
                self._disconnect_event.wait(
                    self.AGENT_RECONNECT_INTERVAL_SEC
                )
            else:
                self._change_state_from_reader(
                    ControlInterfaceState.INITIALIZED
                )
                break

    def _write_to_pipe(self, to_ankaios: _control_api.ToAnkaios) -> None:
        """
        Writes the ToAnkaios proto message to the control
        interface output fifo.

        :param to_ankaios: The ToAnkaios proto message.
        :type to_ankaios: _control_api.ToAnkaios

        :raises ConnectionException: If the output pipe is None, or
            was closed by a disconnect before the write.
        """
        with self._lock:
            output_file = self._output_file
        if output_file is None:
            self._logger.error(
                "Could not write to pipe, output file handler is None."
            )
            raise ConnectionException(
                "Could not write to pipe, output file handler is None."
            )

        # Held across the whole write so the length prefix and the payload
        # cannot be split by another writer, and so the file cannot be
        # closed mid-write.
        with self._write_lock:
            try:
                # Adds the byte length of the proto msg
                output_file.write(_VarintBytes(to_ankaios.ByteSize()))
                # Adds the proto msg itself
                output_file.write(to_ankaios.SerializeToString())
                output_file.flush()
            except ValueError as e:
                # A disconnect closed the file after we took it.
                raise ConnectionException(
                    "Could not write to pipe, output file closed."
                ) from e

    def write_request(self, request: Request) -> None:
        """
        Writes the request into the control interface output fifo.

        :param request: The request object to be written.
        :type request: Request

        :raises ConnectionException: If not connected.
        :raises ConnectionClosedException: If the connection is closed.
        """
        with self._lock:
            if self._state == ControlInterfaceState.CONNECTION_CLOSED:
                raise ConnectionClosedException(
                    "Could not write to pipe, connection closed."
                )
            if self._state != ControlInterfaceState.CONNECTED:
                raise ConnectionException(
                    "Could not write to pipe, not connected."
                )

        request_to_ankaios = _control_api.ToAnkaios(
            request=request._to_proto()
        )
        self._write_to_pipe(request_to_ankaios)

    def _send_initial_hello(self) -> None:
        """
        Send an initial hello message with the version
        to the control interface.

        :raises ConnectionException: If not connected.
        """
        initial_hello = _control_api.ToAnkaios(
            hello=_control_api.Hello(protocolVersion=str(ANKAIOS_VERSION))
        )
        self._write_to_pipe(initial_hello)
        self._logger.debug(
            "Sent initial hello message with the version %s", ANKAIOS_VERSION
        )
