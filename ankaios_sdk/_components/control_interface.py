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
"""


__all__ = ["ControlInterface", "ControlInterfaceState"]


import os
import select
import threading
from typing import Callable
from enum import Enum
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from .._protos import _control_api
from .request import Request
from .response import Response, ResponseException
from ..exceptions import AnkaiosConnectionException, ConnectionClosedException
from ..utils import DEFAULT_CONTROL_INTERFACE_PATH, get_logger, ANKAIOS_VERSION


class ControlInterfaceState(Enum):
    """ The state of the control interface. """
    CONNECTED = 1
    "(int): Connected state."
    DISCONNECTED = 2
    "(int): Disconnected state."
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


class ControlInterface:
    """
    This class handles the interaction with the Ankaios control interface.
    It provides method to send and receive data to and from the control
    interface pipes.

    Attributes:
        logger (logging.Logger): The logger for the Ankaios class.
        path (str): The path to the control interface.
    """
    ANKAIOS_CONTROL_INTERFACE_BASE_PATH = "/run/ankaios/control_interface"
    "(str): The base path for the Ankaios control interface."

    def __init__(self,
                 add_response_callback: Callable,
                 state_changed_callback: Callable
                 ) -> None:
        """
        Initialize the ControlInterface object. This will also connect to
        the control interface pipes.
        """
        self.path = DEFAULT_CONTROL_INTERFACE_PATH
        self._input_file = None
        self._output_file = None
        self.state = ControlInterfaceState.DISCONNECTED
        self._read_thread = None
        self._disconnect_event = threading.Event()

        self._add_response_callback = add_response_callback
        self._state_changed_callback = state_changed_callback

        self.logger = get_logger()

    def connect(self) -> None:
        """
        Connect to the control interface by starting to read
        from the input fifo and opening the output fifo.

        Raises:
            AnkaiosConnectionException: If an error occurred.
        """
        if self.state == ControlInterfaceState.CONNECTED:
            raise AnkaiosConnectionException("Already connected.")

        if not os.path.exists(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input"):
            raise AnkaiosConnectionException(
                "Control interface input fifo does not exist."
            )

        if not os.path.exists(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output"):
            raise AnkaiosConnectionException(
                "Control interface output fifo does not exist."
            )

        # pylint: disable=consider-using-with
        try:
            self._output_file = open(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab"
            )
        except Exception as e:
            self.logger.error("Error while opening output fifo: %s", e)
            self.disconnect()
            raise AnkaiosConnectionException(
                "Error while opening output fifo."
            ) from e

        self._read_thread = threading.Thread(
            target=self._read_from_control_interface,
            daemon=True
        )
        self.change_state(ControlInterfaceState.CONNECTED)
        self._read_thread.start()
        self._send_initial_hello()

    def disconnect(self) -> None:
        """
        Disconnect from the control interface.
        """
        if not self.state == ControlInterfaceState.DISCONNECTED:
            self.logger.debug("Already disconnected.")
            return

        self.logger.debug("Disconnecting..")
        self._disconnect_event.set()
        if self._read_thread is not None:
            self._read_thread.join(timeout=2)
            if self._read_thread.is_alive():
                self.logger.error("Read thread did not stop.")
            self._read_thread = None
        self._cleanup()

    def _cleanup(self) -> None:
        """
        Clean up the resources.
        """
        self.change_state(ControlInterfaceState.DISCONNECTED)
        if self._output_file is not None:
            self._output_file.close()
            self._output_file = None
        self.logger.debug("Cleanup happened")

    def change_state(self, state: ControlInterfaceState) -> None:
        """
        Change the state of the control interface.

        Args:
            state (ControlInterfaceState): The new state.
        """
        self.state = state
        self._state_changed_callback(state)

        if self.state == ControlInterfaceState.AGENT_DISCONNECTED:
            self._disconnect_event.set()
            self._cleanup()

    def _read_from_control_interface(self) -> None:
        """
        Reads from the control interface input fifo.
        This is meant to be run in a separate thread.
        The responses are then sent to the Ankaios class to be handled.

        Raises:
            AnkaiosConnectionException: If an error occurs
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
            self.logger.error("Error while opening input fifo: %s", e)
            self.disconnect()
            raise AnkaiosConnectionException(
                "Error while opening input fifo."
            ) from e
        os.set_blocking(self._input_file.fileno(), False)

        try:
            self.logger.info("Started reading from the input pipe.")

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

                if not varint_buffer:  # pragma: no cover
                    self.change_state(ControlInterfaceState.AGENT_DISCONNECTED)

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
                    self.logger.error("Error while reading: %s", e)
                    continue
                except ConnectionClosedException as e:  # pragma: no cover
                    self.logger.error("Connection closed: %s", e)
                    self.change_state(ControlInterfaceState.CONNECTION_CLOSED)
                    break

                self._add_response_callback(response)
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error while reading fifo file: %s", e)
        finally:
            if self.state == ControlInterfaceState.CONNECTED:
                self.change_state(ControlInterfaceState.DISCONNECTED)
            self._input_file.close()
            self._cleanup()

    def _write_to_pipe(self, to_ankaios: _control_api.ToAnkaios) -> None:
        """
        Writes the ToAnkaios proto message to the control
        interface output fifo.

        Args:
            to_ankaios (_control_api.ToAnkaios): The ToAnkaios proto message.
        """
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
            AnkaiosConnectionException: If not connected.
        """
        if not self.state == ControlInterfaceState.CONNECTED:
            raise AnkaiosConnectionException(
                "Could not write to pipe, not connected.")

        request_to_ankaios = _control_api.ToAnkaios(
            request=request._to_proto()
        )
        self._write_to_pipe(request_to_ankaios)

    def _send_initial_hello(self) -> None:
        """
        Send an initial hello message to the control interface with
        the version in order to check it.

        Raises:
            AnkaiosConnectionException: If an error occurred.
        """
        initial_hello = _control_api.ToAnkaios(
            hello=_control_api.Hello(
                protocolVersion=str(ANKAIOS_VERSION)
            )
        )
        self._write_to_pipe(initial_hello)
        self.logger.debug("Sent initial hello message with the version %s",
                          ANKAIOS_VERSION)
    