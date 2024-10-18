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

        ret = ankaios.apply_manifest(manifest)
        if ret is not None:
            print("Manifest applied successfully.")
            print(ret["added_workloads"])
            print(ret["deleted_workloads"])

- Delete a manifest:
    .. code-block:: python

        ret = ankaios.delete_manifest(manifest)
        if ret is not None:
            print("Manifest deleted successfully.")
            print(ret["deleted_workloads"])

- Run a workload:
    .. code-block:: python

        ret = ankaios.run_workload(workload)
        if ret is not None:
            print("Workload started successfully.")
            print(ret["added_workloads"])

- Delete a workload:
    .. code-block:: python

        ret = ankaios.delete_workload(workload_name)
        if ret is not None:
            print("Workload deleted successfully.")
            print(ret["deleted_workloads"])

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

- Get the workload states:
    .. code-block:: python

        workload_states = ankaios.get_workload_states()

- Get the workload execution state for instance name:
    .. code-block:: python

        ret = ankaios.get_execution_state_for_instance_name(instance_name)
        if ret is not None:
            print(f"State: {ret.state}, substate: {ret.substate}")

- Wait for a workload to reach a state:
    .. code-block:: python

        ret = ankaios.wait_for_workload_to_reach_state(
            instance_name,
            WorkloadStateEnum.RUNNING
        )
        if ret:
            print(f"State reached.")
"""

__all__ = ["Ankaios", "AnkaiosLogLevel"]

import logging
import time
from typing import Union
from enum import Enum
import threading
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from ._protos import _control_api
from .exceptions import AnkaiosConnectionException, AnkaiosException, \
                        ResponseException
from ._components import Workload, CompleteState, Request, Response, \
                         ResponseEvent, WorkloadStateCollection, Manifest, \
                         WorkloadInstanceName, WorkloadStateEnum, \
                         WorkloadExecutionState


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

        Raises:
            AnkaiosConnectionException: If an exception occurred.
        """
        self._disconnect()
        if exc_type is not None:  # pragma: no cover
            self.logger.error("An exception occurred: %s, %s, %s",
                              exc_type, exc_value, traceback)
            raise AnkaiosConnectionException(
                f"An exception occurred: {exc_type}, {exc_value}, {traceback}")

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

        Raises:
            AnkaiosConnectionException: If an error occurs
                while reading the fifo.
        """
        try:
            # pylint: disable=consider-using-with
            input_fifo = open(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb")

            while self._connected:
                # Buffer for reading in the byte size of the proto msg
                varint_buffer = bytearray()
                while True:
                    # Consume byte for byte
                    next_byte = input_fifo.read(1)
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
                    next_byte = input_fifo.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    msg_buf += next_byte

                try:
                    response = Response(bytes(msg_buf))
                except ResponseException as e:  # pragma: no cover
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
            input_fifo.close()

    def _get_response_by_id(self, request_id: str,
                            timeout: float = DEFAULT_TIMEOUT) -> Response:
        """
        Returns the response by the request id.

        Args:
            request_id (str): The ID of the request.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            AnkaiosConnectionException: The response object.

        Raises:
            AnkaiosConnectionException: If reading from the control interface
                is not started.
        """
        if not self._connected:
            raise AnkaiosConnectionException(
                "Reading from the control interface is not started.")

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
            # Adds the byte length of the proto msg
            f.write(_VarintBytes(request_to_ankaios.ByteSize()))
            # Adds the proto msg itself
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

        Raises:
            AnkaiosConnectionException: If not connected.
        """
        if not self._connected:
            raise AnkaiosConnectionException(
                "Cannot request if not connected."
                )
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
            AnkaiosConnectionException: If already connected.
        """
        if self._connected:
            raise AnkaiosConnectionException("Already connected.")
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
            AnkaiosConnectionException: If already disconnected.
        """
        if not self._connected:
            raise AnkaiosConnectionException("Already disconnected.")
        self._connected = False
        self._read_thread.join()

    def apply_manifest(self, manifest: Manifest) -> dict:
        """
        Send a request to apply a manifest.

        Args:
            manifest (Manifest): The manifest object to be applied.

        Returns:
            dict: a dict with the added and deleted workloads.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while applying
                the manifest.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(manifest.generate_complete_state())
        request.set_masks(manifest._calculate_masks())

        # Send request
        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to apply manifest: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        self.logger.info(
            "Update successfull: %s added workloads, "
            + "%s deleted workloads.",
            len(content["added_workloads"]),
            len(content["deleted_workloads"])
        )
        return content

    def delete_manifest(self, manifest: Manifest) -> dict:
        """
        Send a request to delete a manifest.

        Args:
            manifest (Manifest): The manifest object to be deleted.

        Returns:
            dict: a dict with the added and deleted workloads.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while deleting
                the manifest.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.set_masks(manifest._calculate_masks())

        # Send request
        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete manifest: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        self.logger.info(
            "Update successfull: %s added workloads, "
            + "%s deleted workloads.",
            len(content["added_workloads"]),
            len(content["deleted_workloads"])
        )
        return content

    def run_workload(self, workload: Workload) -> dict:
        """
        Send a request to run a workload.

        Args:
            workload (Workload): The workload object to be run.

        Returns:
            dict: a dict with the added and deleted workloads.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while running the workload.
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
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to run workload: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        self.logger.info(
            "Update successfull: %s added workloads, "
            + "%s deleted workloads.",
            len(content["added_workloads"]),
            len(content["deleted_workloads"])
        )
        return content

    def delete_workload(self, workload_name: str) -> dict:
        """
        Send a request to delete a workload.

        Args:
            workload_name (str): The name of the workload to be deleted.

        Returns:
            dict: a dict with the added and deleted workloads.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while deleting the workload.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.add_mask(f"desiredState.workloads.{workload_name}")

        try:
            response = self._send_request(request)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete workload: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        self.logger.info(
            "Update successfull: %s added workloads, "
            + "%s deleted workloads.",
            len(content["added_workloads"]),
            len(content["deleted_workloads"])
        )
        return content

    def get_workload_with_instance_name(
            self, instance_name: WorkloadInstanceName,
            timeout: float = DEFAULT_TIMEOUT
            ) -> Workload:
        """
        Get the workload from the requested complete state, filtered
        with the provided instance name.

        Args:
            instance_name (instance_name): The instance name of the workload.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            Workload: The workload object.
        """
        return self.get_state(
            timeout, [f"desiredState.workloads.{str(instance_name)}"]
        ).get_workloads()[0]

    def set_configs(self, configs: dict) -> bool:
        """
        Set the configs. The names will be the keys of the dictionary.

        Args:
            configs (dict): The configs dictionary.

        Returns:
            bool: True if the configs were set successfully, False otherwise.
        """
        raise NotImplementedError("set_configs is not implemented yet.")

    def set_config(self, name: str, config: Union[dict, list, str]) -> bool:
        """
        Set the config with the provided name.
        If the config exists, it will be replaced.

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

    def delete_all_configs(self) -> bool:
        """
        Delete all the configs.

        Returns:
            bool: True if the configs were deleted successfully,
                False otherwise.
        """
        raise NotImplementedError("delete_all_configs is not implemented yet.")

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

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while getting the state.
        """
        request = Request(request_type="get_state")
        if field_masks is not None:
            request.set_masks(field_masks)
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to get the state: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")

        return content

    def get_agents(
            self, timeout: float = DEFAULT_TIMEOUT
            ) -> list[str]:
        """
        Get the agents from the requested complete state.

        Args:
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            list[str]: The list of agent names.
        """
        return self.get_state(timeout).get_agents()

    def get_workload_states(self,
                            timeout: float = DEFAULT_TIMEOUT
                            ) -> WorkloadStateCollection:
        """
        Get the workload states from the requested complete state.

        Args:
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states.
        """
        return self.get_state(timeout).get_workload_states()

    def get_execution_state_for_instance_name(
            self,
            instance_name: WorkloadInstanceName,
            timeout: float = DEFAULT_TIMEOUT
            ) -> WorkloadExecutionState:
        """
        Get the workload states for a specific workload instance name from the
        requested complete state.

        Args:
            instance_name (WorkloadInstanceName): The instance name of the
                workload.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadExecutionState: The specified workload's execution state.

        Raises:
            AnkaiosException: If the workload state was not
                retrieved successfully.
        """
        state = self.get_state(timeout, [instance_name.get_filter_mask()])
        workload_states = state.get_workload_states().get_as_list()
        if len(workload_states) != 1:
            self.logger.error("Expected exactly one workload state "
                              + "for instance name %s, but got %s",
                              instance_name, len(workload_states))
            raise AnkaiosException(
                "Expected exactly one workload state for instance name "
                + f"{instance_name}, but got {len(workload_states)}")
        return workload_states[0].execution_state

    def get_workload_states_on_agent(self, agent_name: str,
                                     timeout: float = DEFAULT_TIMEOUT
                                     ) -> WorkloadStateCollection:
        """
        Get the workload states on a specific agent from the requested
        complete state.

        Args:
            agent_name (str): The name of the agent.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states.
        """
        state = self.get_state(timeout, ["workloadStates." + agent_name])
        return state.get_workload_states()

    def get_workload_states_for_name(self, workload_name: str,
                                     timeout: float = DEFAULT_TIMEOUT
                                     ) -> WorkloadStateCollection:
        """
        Get the workload states for a specific workload name from the
        requested complete state.

        Args:
            workload_name (str): The name of the workload.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states.
        """
        state = self.get_state(
            timeout, ["workloadStates"]
        )
        workload_states = state.get_workload_states().get_as_list()
        workload_states_for_name = WorkloadStateCollection()
        for workload_state in workload_states:
            if workload_state.name == workload_name:
                workload_states_for_name.add_workload_state(workload_state)
        return workload_states_for_name

    def wait_for_workload_to_reach_state(self,
                                         instance_name: WorkloadInstanceName,
                                         state: WorkloadStateEnum,
                                         timeout: float = DEFAULT_TIMEOUT
                                         ) -> None:
        """
        Waits for the workload to reach the specified state.

        Args:
            instance_name (WorkloadInstanceName): The instance name of the
                workload.
            state (WorkloadStateEnum): The state to wait for.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Raises:
            TimeoutError: If the state was not reached in time.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            workload_state = self.get_execution_state_for_instance_name(
                instance_name
            )
            if workload_state is not None and workload_state.state == state:
                return
            time.sleep(0.1)
        raise TimeoutError(
            "Timeout while waiting for workload to reach state."
            )
