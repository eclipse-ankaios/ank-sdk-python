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

import logging
from threading import Thread, Lock
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from ._protos import _control_api
from ._components import Workload, CompleteState, Request, Response, ResponseEvent, WorkloadStateCollection


__all__ = ["Ankaios", "AnkaiosLogLevel"]


"""Ankaios log levels."""
class AnkaiosLogLevel:
    FATAL = logging.FATAL
    ERROR = logging.ERROR
    WARN = logging.WARN
    INFO = logging.INFO
    DEBUG = logging.DEBUG


"""
Ankaios SDK for Python to interact with the Ankaios control interface.

This SDK provides the functionality to interact with the Ankaios control interface
by sending requests to add a new workload dynamically and to request the workload states.
"""
class Ankaios:
    ANKAIOS_CONTROL_INTERFACE_BASE_PATH = "/run/ankaios/control_interface"
    WAITING_TIME_IN_SEC = 5

    def __init__(self) -> None:
        """Initialize the Ankaios object."""
        self.logger = None
        self.path = self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH

        self._read_thread = None
        self._read = False
        self._responses_lock = Lock()
        self._responses: dict[str, ResponseEvent] = {}

        self._create_logger()

    def __enter__(self) -> "Ankaios":
        """Connect to the control interface."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Disconnect from the control interface."""
        self.disconnect()
        pass

    def __del__(self) -> None:
        """Destroy the Ankaios object."""
        self.logger.debug("Destroyed object of %s", str(self.__class__.__name__))

    def _create_logger(self) -> None:
        """Create a logger with custom format and default log level."""
        formatter = logging.Formatter('%(asctime)s %(message)s', datefmt="%FT%TZ")
        self.logger = logging.getLogger("Ankaios logger")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.set_logger_level(AnkaiosLogLevel.INFO)

    def _read_from_control_interface(self) -> None:
        """Reads from the control interface input fifo and saves the response."""

        with open(f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb") as f:

            while self._read:
                # Buffer for reading in the byte size of the proto msg
                varint_buffer = b''
                while True:
                    # Consume byte for byte
                    next_byte = f.read(1)
                    if not next_byte:
                        break
                    varint_buffer += next_byte
                    # Stop if the most significant bit is 0 (indicating the last byte of the varint)
                    if next_byte[0] & 0b10000000 == 0:
                        break
                # Decode the varint and receive the proto msg length
                msg_len, _ = _DecodeVarint(varint_buffer, 0)

                # Buffer for the proto msg itself
                msg_buf = b''
                for _ in range(msg_len):
                    # Read exact amount of byte according to the calculated proto msg length
                    next_byte = f.read(1)
                    if not next_byte:
                        break
                    msg_buf += next_byte

                try:
                    response = Response(msg_buf)
                except ValueError as e:
                    print(f"{e}")
                    continue

                request_id = response.get_request_id()
                with self._responses_lock:
                    if request_id in self._responses:
                        self._responses[request_id].set_response(response)
                    else:
                        self._responses[request_id] = ResponseEvent(response)
                        self._responses[request_id].set()

    def _get_response_by_id(self, request_id: str, timeout: int = 10) -> Response:
        """Returns the response by the request id."""
        if not self._read:
            raise ValueError("Reading from the control interface is not started.")

        with self._responses_lock:
            if request_id in self._responses:
                return self._responses.pop(request_id).get_response()
            self._responses[request_id] = ResponseEvent()

        return self._responses[request_id].wait_for_response(timeout)

    def _write_to_pipe(self, request: Request) -> None:
        """Writes the request into the control interface output fifo"""
        with open(f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output", "ab") as f:
            request_to_ankaios = _control_api.ToAnkaios(request=request._get())
            # Send the byte length of the proto msg
            f.write(_VarintBytes(request_to_ankaios.ByteSize()))
            # Send the proto msg itself
            f.write(request_to_ankaios.SerializeToString())
            f.flush()

    def _send_request(self, request: Request, timeout: int = 10) -> Response:
        """Send a request and wait for the response."""
        if not self._read:
            raise ValueError("Cannot request if not connected.")
        self._write_to_pipe(request)

        try:
            response = self._get_response_by_id(request.get_id(), timeout)
        except TimeoutError as e:
            raise e
        return response

    def set_logger_level(self, level: AnkaiosLogLevel) -> None:
        """Set the log level of the logger."""
        self.logger.setLevel(level)

    def connect(self) -> None:
        """Connect to the control interface by starting to read from the input fifo."""
        if self._read:
            raise ValueError("Reading from the control interface is already started.")
        self._read_thread = Thread(target=self._read_from_control_interface)
        self._read_thread.start()
        self._read = True

    def disconnect(self) -> None:
        """Disconnect from the control interface by stopping to read from the input fifo."""
        if not self._read:
            raise ValueError("Reading from the control interface is not started.")
        self._read = False
        self._read_thread.join()

    def apply_manifest(self, manifest: dict) -> None:
        # TODO apply_manifest - ank apply
        pass

    def delete_manifest(self, manifest: dict) -> None:
        # TODO delete_manifest
        pass

    def run_workload(self, workload_name: str, workload: Workload) -> None:
        """Send a request to run a workload."""
        complete_state = CompleteState()
        complete_state.set_workload(workload_name, workload)

        # Create the request
        request = Request(request_type="update_state")
        request.set_complete_state(complete_state)
        request.add_mask(f"desiredState.workloads.{workload_name}")

        # Send request
        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error(f"{e}")
            return

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error(f"Error while trying to run workload: {content}")
        elif content_type == "update_state_success":
            self.logger.info("Update successfull: {} added workloads, {} deleted workloads.".
                             format(content["added_workloads"], content["deleted_workloads"]))

    def delete_workload(self, workload_name: str) -> None:
        """Send a request to delete a workload."""
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.add_mask(f"desiredState.workloads.{workload_name}")

        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error(f"{e}")
            return

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error(f"Error while trying to delete workload: {content}")
        elif content_type == "update_state_success":
            self.logger.info("Update successfull: {} added workloads, {} deleted workloads.".
                             format(content["added_workloads"], content["deleted_workloads"]))

    def get_workload(self, workload_name: str, timeout: int = 10) -> Workload:
        """Get the workload from the requested complete state."""
        state = self.get_state(timeout, [f"desiredState.workloads.{workload_name}"])
        if state is not None:
            return state.get_workload(workload_name)

    def set_config_from_file(self, name: str, config_path: str) -> None:
        """Set the config from a file."""
        with open(config_path, "r") as f:
            config = f.read()
            self.set_config(name, config)

    def set_config(self, name: str, config: dict) -> None:
        # TODO set_config - not yet implemented
        raise NotImplementedError("set_config is not implemented yet.")

    def get_config(self, name: str) -> dict:
        # TODO get_config - not yet implemented
        raise NotImplementedError("get_config is not implemented yet.")

    def delete_config(self, name: str) -> None:
        # TODO delete_config - not yet implemented
        raise NotImplementedError("delete_config is not implemented yet.")

    def get_state(self, timeout: int = 10, field_mask: list[str] = list()) -> CompleteState:
        """Send a request to get the complete state"""
        request = Request(request_type="get_state")
        for mask in field_mask:
            request.add_mask(mask)
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error(f"{e}")
            return None

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error(f"Error while trying to get the state: {content}")
            return None

        complete_state = CompleteState(content)
        return complete_state

    def get_agents(self, timeout: int = 10) -> list[str]:
        """Get the agents from the requested complete state."""
        state = self.get_state(timeout)
        if state is not None:
            return state.get_agents()

    def get_workload_states(self, timeout: int = 10) -> WorkloadStateCollection:
        state = self.get_state(timeout)
        if state is not None:
            return state.get_workload_states()

    def get_workload_states_on_agent(self, agent_name: str, timeout: int = 10) -> WorkloadStateCollection:
        state = self.get_state(timeout, ["workloadStates." + agent_name])
        if state is not None:
            return state.get_workload_states()

    def get_workload_states_on_workload_name(self, workload_name: str, timeout: int = 10) -> WorkloadStateCollection:
        state = self.get_state(timeout, ["workloadStates." + workload_name])
        if state is not None:
            return state.get_workload_states()


if __name__ == "__main__":
    with Ankaios() as ankaios:
        # Create workload
        workload = Workload(
            agent_name="agent_A",
            runtime="podman",
            restart_policy="NEVER",
            runtime_config="image: docker.io/library/nginx\ncommandOptions: [\"-p\", \"8080:80\"]"
        )

        # Run workload
        ankaios.run_workload("dynamic_nginx", workload)

        # Get state
        complete_state = ankaios.get_state(field_mask=["workloadStates.agent_A.dynamic_nginx"])
        print(complete_state)

        # Delete workload
        ankaios.delete_workload("dynamic_nginx")
