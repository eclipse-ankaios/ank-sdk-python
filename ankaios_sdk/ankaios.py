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
This script defines the Ankaios class for interacting with the
Ankaios control interface.

Classes
-------

- Ankaios:
    Handles the interaction with the Ankaios control interface.

Enums
-----

- AnkaiosLogLevel:
    Represents the log levels for the Ankaios class.

Usage
-----

- Create an Ankaios object and connect to the control interface:
    .. code-block:: python

        with Ankaios() as ankaios:
            pass

- Apply a manifest:
    .. code-block:: python

        if ankaios.apply_manifest(manifest):
            print("Manifest applied successfully.")

- Delete a manifest:
    .. code-block:: python

        if ankaios.delete_manifest(manifest):
            print("Manifest deleted successfully.")

- Run a workload:
    .. code-block:: python

        if ankaios.run_workload(workload):
            print("Workload started successfully.")

- Delete a workload:
    .. code-block:: python

        if ankaios.delete_workload(workload_name):
            print("Workload deleted successfully.")

- Get a workload:
    .. code-block:: python

        workload = ankaios.get_workload(workload_name)

- Get the state:
    .. code-block:: python

        state = ankaios.get_state()

- Get the agents:
    .. code-block:: python

        agents = ankaios.get_agents()

- Get the workload states:
    .. code-block:: python

        workload_states = ankaios.get_workload_states()

- Get the workload states on an agent:
    .. code-block:: python

        workload_states = ankaios.get_workload_states_on_agent(agent_name)

- Get the workload states on a workload name:
    .. code-block:: python

        workload_states =
            ankaios.get_workload_states_on_workload_name(workload_name)
"""

__all__ = ["Ankaios", "AnkaiosLogLevel"]

import logging
from typing import Union
from enum import Enum
import threading
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from ._protos import _control_api
from ._components import Workload, CompleteState, Request, Response, \
                         ResponseEvent, WorkloadStateCollection, Manifest


class AnkaiosLogLevel(Enum):
    """ Ankaios log levels. """
    FATAL = logging.FATAL
    "(int): Fatal log level."
    ERROR = logging.ERROR
    "(int): Error log level."
    WARN = logging.WARN
    "(int): Warning log level."
    INFO = logging.INFO
    "(int): Info log level."
    DEBUG = logging.DEBUG
    "(int): Debug log level."


# pylint: disable=too-many-public-methods
class Ankaios:
    """
    This class is used to interact with the Ankaios using an intuitive API.
    The class automatically handles the session creation and the requests
    and responses sent and received over the Ankaios Control Interface.

    Attributes:
        logger (logging.Logger): The logger for the Ankaios class.
        path (str): The path to the control interface.
    """
    ANKAIOS_CONTROL_INTERFACE_BASE_PATH = "/run/ankaios/control_interface"
    "(str): The base path for the Ankaios control interface."

    DEFAULT_TIMEOUT = 5.0
    "(float): The default timeout, if not manually provided."

    def __init__(self) -> None:
        """Initialize the Ankaios object."""
        self.logger = None
        self.path = self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH

        self._read_thread = None
        self._connected = False
        self._responses_lock = threading.Lock()
        self._responses: dict[str, ResponseEvent] = {}

        self._create_logger()

    def __enter__(self) -> "Ankaios":
        """
        Connect to the control interface.

        Returns:
            Ankaios: The Ankaios object.
        """
        self._connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Disconnect from the control interface.

        Args:
            exc_type (type): The exception type.
            exc_value (Exception): The exception instance.
            traceback (traceback): The traceback object.
        """
        if exc_type is not None:  # pragma: no cover
            self.logger.error("An exception occurred: %s, %s, %s",
                              exc_type, exc_value, traceback)
        self._disconnect()

    def _create_logger(self) -> None:
        """Create a logger with custom format and default log level."""
        formatter = logging.Formatter('%(asctime)s %(message)s',
                                      datefmt="%FT%TZ")
        self.logger = logging.getLogger("Ankaios logger")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.set_logger_level(AnkaiosLogLevel.INFO)

    def _read_from_control_interface(self) -> None:
        """
        Reads from the control interface input fifo and saves the response.
        This is meant to be run in a separate thread.
        It reads the response from the control interface and saves it in the
        responses dictionary, by triggering the corresponding ResponseEvent.
        """
        # pylint: disable=consider-using-with
        f = open(f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb")

        try:
            while self._connected:
                # Buffer for reading in the byte size of the proto msg
                varint_buffer = bytearray()
                while True:
                    # Consume byte for byte
                    next_byte = f.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    varint_buffer += next_byte
                    # Stop if the most significant bit is 0
                    # (indicating the last byte of the varint)
                    if next_byte[0] & 0b10000000 == 0:
                        break
                # Decode the varint and receive the proto msg length
                msg_len, _ = _DecodeVarint(varint_buffer, 0)

                # Buffer for the proto msg itself
                msg_buf = bytearray()
                for _ in range(msg_len):
                    # Read the message according to the length
                    next_byte = f.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    msg_buf += next_byte

                try:
                    response = Response(bytes(msg_buf))
                except ValueError as e:  # pragma: no cover
                    self.logger.error("Error while reading: %s", e)
                    continue

                request_id = response.get_request_id()
                with self._responses_lock:
                    if request_id in self._responses:
                        self._responses[request_id].set_response(response)
                    else:
                        self._responses[request_id] = ResponseEvent(response)
                        self._responses[request_id].set()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error while reading fifo file: %s", e)
        finally:
            f.close()

    def _get_response_by_id(self, request_id: str,
                            timeout: float = DEFAULT_TIMEOUT) -> Response:
        """
        Returns the response by the request id.

        Args:
            request_id (str): The ID of the request.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            Response: The response object.
        """
        if not self._connected:
            raise ValueError("Reading from the control interface "
                             + "is not started.")

        with self._responses_lock:
            if request_id in self._responses:
                return self._responses.pop(request_id).get_response()
            self._responses[request_id] = ResponseEvent()

        return self._responses[request_id].wait_for_response(timeout)

    def _write_to_pipe(self, request: Request) -> None:
        """
        Writes the request into the control interface output fifo.

        Args:
            request (Request): The request object to be written.
        """
        with open(f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/output",
                  "ab") as f:
            request_to_ankaios = _control_api.ToAnkaios(
                request=request._to_proto()
            )
            # Send the byte length of the proto msg
            f.write(_VarintBytes(request_to_ankaios.ByteSize()))
            # Send the proto msg itself
            f.write(request_to_ankaios.SerializeToString())
            f.flush()

    def _send_request(self, request: Request,
                      timeout: float = DEFAULT_TIMEOUT) -> Response:
        """
        Send a request and wait for the response.

        Args:
            request (Request): The request object to be sent.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            Response: The response object.
        """
        if not self._connected:
            raise ValueError("Cannot request if not connected.")
        self._write_to_pipe(request)

        try:
            response = self._get_response_by_id(request.get_id(), timeout)
        except TimeoutError as e:
            raise e
        return response

    def set_logger_level(self, level: AnkaiosLogLevel) -> None:
        """
        Set the log level of the logger.

        Args:
            level (AnkaiosLogLevel): The log level to be set.
        """
        self.logger.setLevel(level.value)

    def _connect(self) -> None:
        """
        Connect to the control interface by starting to read
        from the input fifo.

        Raises:
            ValueError: If already connected.
        """
        if self._connected:
            raise ValueError("Already connected.")
        self._connected = True
        self._read_thread = threading.Thread(
            target=self._read_from_control_interface
        )
        self._read_thread.start()

    def _disconnect(self) -> None:
        """
        Disconnect from the control interface by stopping to read
        from the input fifo.

        Raises:
            ValueError: If already disconnected.
        """
        if not self._connected:
            raise ValueError("Already disconnected.")
        self._connected = False
        self._read_thread.join()

    def apply_manifest(self, manifest: Manifest) -> bool:
        """
        Send a request to apply a manifest.

        Args:
            manifest (Manifest): The manifest object to be applied.

        Returns:
            bool: True if the manifest was applied successfully,
                False otherwise.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(manifest.generate_complete_state())
        request.set_masks(manifest._calculate_masks())

        # Send request
        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            return False

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to apply manifest: %s",
                              content)
        elif content_type == "update_state_success":
            self.logger.info(
                "Update successfull: %s added workloads, "
                + "%s deleted workloads.",
                content["added_workloads"], content["deleted_workloads"]
            )
            return True
        return False

    def delete_manifest(self, manifest: Manifest) -> bool:
        """
        Send a request to delete a manifest.

        Args:
            manifest (Manifest): The manifest object to be deleted.

        Returns:
            bool: True if the manifest was deleted successfully,
                False otherwise.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.set_masks(manifest._calculate_masks())

        # Send request
        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            return False

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete manifest: %s",
                              content)
        elif content_type == "update_state_success":
            self.logger.info(
                "Update successfull: %s added workloads, "
                + "%s deleted workloads.",
                content["added_workloads"], content["deleted_workloads"]
            )
            return True
        return False

    def run_workload(self, workload: Workload) -> bool:
        """
        Send a request to run a workload.

        Args:
            workload (Workload): The workload object to be run.

        Returns:
            bool: True if the workload was run successfully, False otherwise.
        """
        complete_state = CompleteState()
        complete_state.set_workload(workload)

        # Create the request
        request = Request(request_type="update_state")
        request.set_complete_state(complete_state)
        request.set_masks(workload.masks)

        # Send request
        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            return False

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to run workload: %s",
                              content)
        elif content_type == "update_state_success":
            self.logger.info(
                "Update successfull: %s added workloads, "
                + "%s deleted workloads.",
                content["added_workloads"], content["deleted_workloads"]
            )
            return True
        return False

    def delete_workload(self, workload_name: str) -> bool:
        """
        Send a request to delete a workload.

        Args:
            workload_name (str): The name of the workload to be deleted.

        Returns:
            bool: True if the workload was deleted successfully,
                False otherwise.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.add_mask(f"desiredState.workloads.{workload_name}")

        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            return False

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete workload: %s",
                              content)
        elif content_type == "update_state_success":
            self.logger.info(
                "Update successfull: %s added workloads, "
                + "%s deleted workloads.",
                content["added_workloads"], content["deleted_workloads"]
            )
            return True
        return False

    def get_workload(self, workload_name: str,
                     state: CompleteState = None,
                     timeout: float = DEFAULT_TIMEOUT) -> Workload:
        """
        Get the workload from the requested complete state.

        Args:
            workload_name (str): The name of the workload.
            state (CompleteState): The complete state to get the workload from.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            Workload: The workload object.
        """
        if state is None:
            state = self.get_state(
                timeout, [f"desiredState.workloads.{workload_name}"]
            )
        return state.get_workload(workload_name) if state is not None else None

    def set_configs_from_file(self, configs_path: str) -> bool:
        """
        Set the configs from a file.
        The configs file should have a dictionary as the top level object.
        The names will be the keys of the dictionary.

        Args:
            config_path (str): The path to the configs file.

        Returns:
            bool: True if the configs were set successfully, False otherwise.
        """
        # with open(configs_path, "r", encoding="utf-8") as f:
        #     configs = f.read()
        #     self.set_configs(configs)
        raise NotImplementedError(
            "set_configs_from_file is not implemented yet."
            )

    def set_configs(self, configs: dict) -> bool:
        """
        Set the configs. The names will be the keys of the dictionary.

        Args:
            configs (dict): The configs dictionary.

        Returns:
            bool: True if the configs were set successfully, False otherwise.
        """
        raise NotImplementedError("set_configs is not implemented yet.")

    def set_config_from_file(self, name: str, config_path: str) -> bool:
        """
        Set the config from a file, with the provided name.
        If the config exists, it will be replaced.

        Args:
            name (str): The name of the config.
            config_path (str): The path to the config file.

        Returns:
            bool: True if the config was set successfully, False otherwise.
        """
        raise NotImplementedError(
            "set_config_from_file is not implemented yet."
            )

    def set_config(self, name: str, config: Union[dict, list, str]) -> bool:
        """
        Set the config with the provided name.
        If the config exists, it will eb replaced.

        Args:
            name (str): The name of the config.
            config (Union[dict, list, str]): The config dictionary.

        Returns:
            bool: True if the config was set successfully, False otherwise.
        """
        raise NotImplementedError("set_config is not implemented yet.")

    def get_configs(self) -> dict:
        """
        Get the configs. The keys will be the names.

        Returns:
            dict: The configs dictionary.
        """
        raise NotImplementedError("get_configs is not implemented yet.")

    def get_config(self, name: str) -> Union[dict, list, str]:
        """
        Get the config with the provided name.

        Args:
            name (str): The name of the config.

        Returns:
            Union[dict, list, str]: The config.
        """
        raise NotImplementedError("get_config is not implemented yet.")

    def delete_configs(self) -> bool:
        """
        Delete all the configs.

        Returns:
            bool: True if the configs were deleted successfully,
                False otherwise.
        """
        raise NotImplementedError("delete_configs is not implemented yet.")

    def delete_config(self, name: str) -> bool:
        """
        Delete the config.

        Args:
            name (str): The name of the config.

        Returns:
            bool: True if the config was deleted successfully, False otherwise.
        """
        raise NotImplementedError("delete_config is not implemented yet.")

    def get_state(self, timeout: float = DEFAULT_TIMEOUT,
                  field_masks: list[str] = None) -> CompleteState:
        """
        Send a request to get the complete state.

        Args:
            timeout (float): The maximum time to wait for the response,
                in seconds.
            field_masks (list[str]): The list of field masks to filter
                the state.

        Returns:
            CompleteState: The complete state object.
        """
        request = Request(request_type="get_state")
        if field_masks is not None:
            request.set_masks(field_masks)
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            return None

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to get the state: %s",
                              content)
            return None

        return content

    def get_agents(self, state: CompleteState = None,
                   timeout: float = DEFAULT_TIMEOUT) -> list[str]:
        """
        Get the agents from the requested complete state.

        Args:
            state (CompleteState): The complete state to get the agents from.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            list[str]: The list of agent names.
        """
        if state is None:
            state = self.get_state(timeout)
        return state.get_agents() if state is not None else None

    def get_workload_states(self,
                            state: CompleteState = None,
                            timeout: float = DEFAULT_TIMEOUT
                            ) -> WorkloadStateCollection:
        """
        Get the workload states from the requested complete state.
        If a state is not provided, it will be requested.

        Args:
            state (CompleteState): The complete state to get
                the workload states from.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states.
        """
        if state is None:
            state = self.get_state(timeout)
        return state.get_workload_states() if state is not None else None

    def get_workload_states_on_agent(self, agent_name: str,
                                     state: CompleteState = None,
                                     timeout: float = DEFAULT_TIMEOUT
                                     ) -> WorkloadStateCollection:
        """
        Get the workload states on a specific agent from the requested
        complete state.
        If a state is not provided, it will be requested.

        Args:
            agent_name (str): The name of the agent.
            state (CompleteState): The complete state to get
                the workload states from.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states on the
                specified agent.
        """
        if state is None:
            state = self.get_state(timeout, ["workloadStates." + agent_name])
        return state.get_workload_states() if state is not None else None

    def get_workload_states_on_workload_name(self, workload_name: str,
                                             state: CompleteState = None,
                                             timeout: float = DEFAULT_TIMEOUT
                                             ) -> WorkloadStateCollection:
        """
        Get the workload states on a specific workload name from the requested
        complete state.
        If a state is not provided, it will be requested.

        Args:
            workload_name (str): The name of the workload.
            state (CompleteState): The complete state to get
                the workload states from.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states on the
                specified workload name.
        """
        if state is None:
            state = self.get_state(
                timeout, ["workloadStates." + workload_name]
            )
        return state.get_workload_states() if state is not None else None
