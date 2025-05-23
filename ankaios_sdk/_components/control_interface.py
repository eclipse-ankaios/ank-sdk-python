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
This script defines the ControlInterface class that handles the writing
and reading of data to and from the Ankaios control interface.

Classes
-------

- ControlInterface:
    Handles the interaction with the Ankaios control interface.

Enums
-----

- ControlInterfaceState:
    Represents the state of the control interface.

Usage
-----

- Create a Control Interface instance, connect and disconnect.
    .. code-block:: python

        ci = ControlInterface(<callbacks from Ankaios>)
        ci.connect()
        ...
        ci.disconnect()

- Change the state of the control interface.
    .. code-block:: python

        ci.change_state(ControlInterfaceState.TERMINATED)
"""


__all__ = ["ControlInterface", "ControlInterfaceState"]


import os
import select
import time
import threading
from typing import Callable
from enum import Enum
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from .._protos import _control_api
from .request import Request
from .response import Response, ResponseException, ResponseType
from ..exceptions import ControlInterfaceException, ConnectionClosedException
from ..utils import DEFAULT_CONTROL_INTERFACE_PATH, get_logger, ANKAIOS_VERSION


class ControlInterfaceState(Enum):
    """ The state of the control interface. """
    INITIALIZED = 1
    "(int): Connection established state."
    TERMINATED = 2
    "(int): Connection stopped state."
    AGENT_DISCONNECTED = 3
    "(int): Agent disconnected state."
    CONNECTION_CLOSED = 4
    "(int): Connection closed state."

    def __str__(self) -> str:
        """
        Returns the string representation of the state.

        Returns:
            str: The state as a string.
        """
        return self.name


# pylint: disable=too-many-instance-attributes
class ControlInterface:
    """
    This class handles the interaction with the Ankaios control interface.
    It provides methods to send and receive data to and from the control
    interface pipes.
    """
    ANKAIOS_CONTROL_INTERFACE_BASE_PATH = DEFAULT_CONTROL_INTERFACE_PATH
    "(str): The base path for the Ankaios control interface."

    def __init__(self,
                 add_response_callback: Callable
                 ) -> None:
        """
        Initialize the ControlInterface object. This is used
        to interact with the control interface.

        Args:
            add_response_callback (Callable): The callback function to add
                a response to the Ankaios class.
            state_changed_callback (Callable): The callback function to
                to call when the state of the control interface changes.
        """
        self._input_file = None
        self._output_file = None
        # The state of the control interface must not be changed directly.
        # Use the change_state method instead.
        self._state = ControlInterfaceState.TERMINATED
        self._read_thread = None
        self._disconnect_event = threading.Event()

        self._add_response_callback = add_response_callback

        self._logger = get_logger()

    def connect(self) -> None:
        """
        Connect to the control interface by starting to read
        from the input fifo and opening the output fifo.

        Raises:
            ControlInterfaceException: If an error occurred.
        """
        if self._state == ControlInterfaceState.INITIALIZED:
            raise ControlInterfaceException("Already connected.")

        if not os.path.exists(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input"):
            raise ControlInterfaceException(
                "Control interface input fifo does not exist."
            )

        if not os.path.exists(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output"):
            raise ControlInterfaceException(
                "Control interface output fifo does not exist."
            )

        # pylint: disable=consider-using-with
        try:
            self._output_file = open(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab"
            )
        except Exception as e:
            self._logger.error("Error while opening output fifo: %s", e)
            raise ControlInterfaceException(
                "Error while opening output fifo."
            ) from e

        self._read_thread = threading.Thread(
            target=self._read_from_control_interface,
            daemon=True
        )
        self._read_thread.start()
        self.change_state(ControlInterfaceState.INITIALIZED)
        self._send_initial_hello()

    def disconnect(self) -> None:
        """
        Disconnect from the control interface.
        """
        if not self._state == ControlInterfaceState.INITIALIZED:
            self._logger.debug("Already disconnected.")
            return

        self._logger.debug("Disconnecting..")
        self._disconnect_event.set()
        if self._read_thread is not None:
            self._read_thread.join(timeout=2)
            if self._read_thread.is_alive():
                self._logger.error("Read thread did not stop.")
            self._read_thread = None
        self._cleanup()

    def _cleanup(self) -> None:
        """
        Clean up the resources.
        """
        self.change_state(ControlInterfaceState.TERMINATED)
        if self._output_file is not None:
            self._output_file.close()
            self._output_file = None
        # The input file will be closed by the reading thread.
        # If the thread gets terminated or it's stuck, the input file
        # will be closed here. No cover because it's an exceptional case.
        if self._input_file is not None:  # pragma: no cover
            self._input_file.close()
            self._input_file = None
        self._logger.debug("Cleanup happened")

    def change_state(
            self, state: ControlInterfaceState, info: str = None
            ) -> None:
        """
        Change the state of the control interface.

        Args:
            state (ControlInterfaceState): The new state.
            info (str): Additional information about the state change.
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
            self._logger.debug(
                "State changed to %s: %s", state, info
            )

    # pylint: disable=too-many-statements, too-many-branches
    def _read_from_control_interface(self) -> None:
        """
        Reads from the control interface input fifo.
        This is meant to be run in a separate thread.
        The responses are then sent to the Ankaios class to be handled.

        Raises:
            ControlInterfaceException: If an error occurs
                while reading the fifo.
        """
        # The pragma: no cover is used on small checks that are not expected
        # to fail. This method is difficult to test and testing each check
        # would be redundant.

        # pylint: disable=invalid-name
        MOST_SIGNIFICANT_BIT_MASK = 0b10000000

        # pylint: disable=consider-using-with
        try:
            self._input_file = open(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb"
            )
        except Exception as e:
            self._logger.error("Error while opening input fifo: %s", e)
            self.disconnect()
            raise ControlInterfaceException(
                "Error while opening input fifo."
            ) from e
        os.set_blocking(self._input_file.fileno(), False)

        try:
            self._logger.info("Started reading from the input pipe.")
            while not self._disconnect_event.is_set():
                # The loop continues when data is available or when the
                # timeout of 1 second is reached.
                ready, _, _ = select.select([self._input_file], [], [], 1)
                if not ready:  # pragma: no cover
                    continue

                # Buffer for reading in the byte size of the proto msg
                varint_buffer = bytearray()
                while not self._disconnect_event.is_set():
                    # Consume byte for byte
                    next_byte = self._input_file.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    varint_buffer += next_byte
                    # Check if we reached the last byte
                    if next_byte[0] & MOST_SIGNIFICANT_BIT_MASK == 0:
                        break

                if not varint_buffer:
                    self.change_state(
                        ControlInterfaceState.AGENT_DISCONNECTED)
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
                    next_byte = self._input_file.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    msg_buf += next_byte

                try:
                    response = Response(bytes(msg_buf))
                except ResponseException as e:  # pragma: no cover
                    self._logger.error("Error while reading: %s", e)
                    continue

                self._add_response_callback(response)

                if response.content_type == ResponseType.CONNECTION_CLOSED:
                    self.change_state(
                        ControlInterfaceState.CONNECTION_CLOSED,
                        response.content
                        )
                    raise ConnectionClosedException(response.content)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._logger.error("Error while reading fifo file: %s", e)
        finally:
            self._input_file.close()
            self._input_file = None
            self._cleanup()

    def _agent_gone_routine(self) -> None:
        """
        Method will be called when the agent is gone.
        It will attempt to write the hello message to the agent
        until the agent is connected.
        """
        agent_reconnect_interval = 1  # seconds
        while self._state == ControlInterfaceState.AGENT_DISCONNECTED:
            try:
                self._send_initial_hello()
            except BrokenPipeError as _:
                self._logger.warning(
                    "Waiting for the agent.."
                    )
                time.sleep(agent_reconnect_interval)
            else:
                self.change_state(ControlInterfaceState.INITIALIZED)
                break

    def _write_to_pipe(self, to_ankaios: _control_api.ToAnkaios) -> None:
        """
        Writes the ToAnkaios proto message to the control
        interface output fifo.

        Args:
            to_ankaios (_control_api.ToAnkaios): The ToAnkaios proto message.

        Raises:
            ControlInterfaceException: If the output pipe is None.
        """
        if self._output_file is None:
            self._logger.error(
                "Could not write to pipe, output file handler is None."
            )
            raise ControlInterfaceException(
                "Could not write to pipe, output file handler is None."
            )

        # Adds the byte length of the proto msg
        self._output_file.write(_VarintBytes(to_ankaios.ByteSize()))
        # Adds the proto msg itself
        self._output_file.write(to_ankaios.SerializeToString())
        self._output_file.flush()

    def write_request(self, request: Request) -> None:
        """
        Writes the request into the control interface output fifo.

        Args:
            request (Request): The request object to be written.

        Raises:
            ControlInterfaceException: If not connected.
            ConnectionClosedException: If the connection is closed.
        """
        if self._state == ControlInterfaceState.CONNECTION_CLOSED:
            raise ConnectionClosedException(
                "Could not write to pipe, connection closed."
            )
        if not self._state == ControlInterfaceState.INITIALIZED:
            raise ControlInterfaceException(
                "Could not write to pipe, not connected.")

        request_to_ankaios = _control_api.ToAnkaios(
            request=request._to_proto()
        )
        self._write_to_pipe(request_to_ankaios)

    def _send_initial_hello(self) -> None:
        """
        Send an initial hello message with the version
        to the control interface.

        Raises:
            ControlInterfaceException: If not connected.
        """
        initial_hello = _control_api.ToAnkaios(
            hello=_control_api.Hello(
                protocolVersion=str(ANKAIOS_VERSION)
            )
        )
        self._write_to_pipe(initial_hello)
        self._logger.debug("Sent initial hello message with the version %s",
                           ANKAIOS_VERSION)
