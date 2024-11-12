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

Usage
-----

- Create an Ankaios object, connect and disconnect from the control interface:
    .. code-block:: python

        ankaios = Ankaios()
        ...
        ankaios.disconnect()

- Connect and disconnect using a context manager:
    .. code-block:: python

        with Ankaios() as ankaios:
            ...

- Apply a manifest:
    .. code-block:: python

        ret = ankaios.apply_manifest(manifest)
        print(ret.to_dict())

- Delete a manifest:
    .. code-block:: python

        ret = ankaios.delete_manifest(manifest)
        print(ret.to_dict())

- Run a workload:
    .. code-block:: python

        ret = ankaios.apply_workload(workload)
        print(ret.to_dict())

- Get a workload:
    .. code-block:: python

        workload = ankaios.get_workload(workload_name)

- Delete a workload:
    .. code-block:: python

        ret = ankaios.delete_workload(workload_name)
        print(ret.to_dict())

- Get the state:
    .. code-block:: python

        state = ankaios.get_state()

- Get the agents:
    .. code-block:: python

        agents = ankaios.get_agents()

- Get the workload states:
    .. code-block:: python

        workload_states = ankaios.get_workload_states()

- Get the workload states for workloads with a specific name:
    .. code-block:: python

        workload_states = ankaios.get_workload_states_for_name(workload_name)

- Get the workload states for a specific agent:
    .. code-block:: python

        workload_states = ankaios.get_workload_states_on_agent(agent_name)

- Get the workload execution state for instance name:
    .. code-block:: python

        ret = ankaios.get_execution_state_for_instance_name(instance_name)
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

import os
import time
from typing import Union
import threading
import select
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint

from ._protos import _control_api
from .exceptions import AnkaiosConnectionException, AnkaiosException, \
                        ResponseException, ConnectionClosedException
from ._components import Workload, CompleteState, Request, Response, \
                         UpdateStateSuccess, ResponseEvent, \
                         WorkloadStateCollection, Manifest, \
                         WorkloadInstanceName, WorkloadStateEnum, \
                         WorkloadExecutionState
from .utils import AnkaiosLogLevel, get_logger, \
    WORKLOADS_PREFIX, ANKAIOS_VERSION, CONFIGS_PREFIX


# pylint: disable=too-many-public-methods, too-many-instance-attributes
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

    def __init__(self,
                 log_level: AnkaiosLogLevel = AnkaiosLogLevel.INFO
                 ) -> None:
        """
        Initialize the Ankaios object. The logger will be created and
        the connection to the control interface will be established.
        """
        self.path = self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH

        self._read_thread = None
        self._connected = False
        self._disconnect_event = threading.Event()
        self._output_file = None
        self._responses_lock = threading.Lock()
        self._responses: dict[str, ResponseEvent] = {}

        self.logger = get_logger()
        self.set_logger_level(log_level)
        self._connect()

    def __enter__(self) -> "Ankaios":
        """
        Used for context management.

        Returns:
            Ankaios: The current object.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Used for context management. Disconnects from the control interface.

        Args:
            exc_type (type): The exception type.
            exc_value (Exception): The exception instance.
            traceback (traceback): The traceback object.
        """
        if exc_type is not None:  # pragma: no cover
            self.logger.error("An exception occurred: %s, %s, %s",
                              exc_type, exc_value, traceback)
        self.disconnect()

    def _connect(self) -> None:
        """
        Connect to the control interface by starting to read
        from the input fifo and opening the output fifo.

        Raises:
            AnkaiosConnectionException: If an error occurred.
        """
        if self._connected:
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
        self._connected = True
        self._read_thread.start()
        self._send_initial_hello()

    def disconnect(self) -> None:
        """
        Disconnect from the control interface by stopping to read
        from the input fifo.
        """
        self.logger.debug("Disconnecting..")
        self._connected = False
        self._disconnect_event.set()
        if self._read_thread is not None:
            self._read_thread.join(timeout=2)
            if self._read_thread.is_alive():
                self.logger.error("Read thread did not stop.")
            self._read_thread = None
        if self._output_file is not None:
            self._output_file.close()
            self._output_file = None

    # pylint: disable=too-many-branches
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
        # pylint: disable=invalid-name
        MOST_SIGNIFICANT_BIT_MASK = 0b10000000
        try:
            # pylint: disable=consider-using-with
            input_fifo = open(
                f"{self.ANKAIOS_CONTROL_INTERFACE_BASE_PATH}/input", "rb"
            )
            os.set_blocking(input_fifo.fileno(), False)

            self.logger.info("Started reading from the input pipe.")
            while not self._disconnect_event.is_set():
                # The loop continues when data is available or when the
                # timeout of 1 second is reached.
                ready, _, _ = select.select([input_fifo], [], [], 1)
                if not ready:  # pragma: no cover
                    continue

                # Buffer for reading in the byte size of the proto msg
                varint_buffer = bytearray()
                while True:
                    # Consume byte for byte
                    next_byte = input_fifo.read(1)
                    if not next_byte:  # pragma: no cover
                        break
                    varint_buffer += next_byte
                    # Check if we reached the last byte
                    if next_byte[0] & MOST_SIGNIFICANT_BIT_MASK == 0:
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
                self.logger.debug("Received a response with the id %s",
                                  request_id)
                with self._responses_lock:
                    if request_id in self._responses:
                        self.logger.debug(
                            "Setting response for existing request.")
                        self._responses[request_id].set_response(response)
                    else:
                        self.logger.debug(
                            "Adding early response.")
                        self._responses[request_id] = ResponseEvent(response)
                        self._responses[request_id].set()
        except ConnectionClosedException as e:  # pragma: no cover
            self.logger.error("Connection closed: %s", e)
            self.disconnect()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error while reading fifo file: %s", e)
            raise e
        finally:
            input_fifo.close()

    def _write_to_pipe(self, to_ankaios: _control_api.ToAnkaios) -> None:
        """
        Writes the ToAnkaios proto message to the control
        interface output fifo.

        Args:
            to_ankaios (_control_api.ToAnkaios): The ToAnkaios proto message.

        Raises:
            AnkaiosConnectionException: If not connected.
        """
        if not self._connected:
            raise AnkaiosConnectionException(
                "Could not write to pipe, not connected.")

        # Adds the byte length of the proto msg
        self._output_file.write(_VarintBytes(to_ankaios.ByteSize()))
        # Adds the proto msg itself
        self._output_file.write(to_ankaios.SerializeToString())
        self._output_file.flush()

    def _write_request(self, request: Request) -> None:
        """
        Writes the request into the control interface output fifo.

        Args:
            request (Request): The request object to be written.
        """
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

        Raises:
            AnkaiosConnectionException: If reading from the control interface
                is not started.
        """
        if not self._connected:
            raise AnkaiosConnectionException("Not connected.")

        with self._responses_lock:
            if request_id in self._responses:
                self.logger.debug("Immediate response available.")
                return self._responses.pop(request_id).get_response()
            self._responses[request_id] = ResponseEvent()

        self.logger.debug("Waiting on response.")
        return self._responses[request_id].wait_for_response(timeout)

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
            TimeoutError: If the request timed out.
            AnkaiosConnectionException: If not connected.
        """
        self._write_request(request)

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

    def apply_manifest(self, manifest: Manifest,
                       timeout: float = DEFAULT_TIMEOUT
                       ) -> UpdateStateSuccess:
        """
        Send a request to apply a manifest.

        Args:
            manifest (Manifest): The manifest object to be applied.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while applying
                the manifest.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState.from_manifest(manifest))
        request.set_masks(manifest._calculate_masks())

        # Send request
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to apply manifest: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads)
            )
            return content
        raise AnkaiosException("Received unexpected content type.")

    def delete_manifest(self, manifest: Manifest,
                        timeout: float = DEFAULT_TIMEOUT
                        ) -> UpdateStateSuccess:
        """
        Send a request to delete a manifest.

        Args:
            manifest (Manifest): The manifest object to be deleted.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

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
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete manifest: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads)
            )
            return content
        raise AnkaiosException("Received unexpected content type.")

    def apply_workload(self, workload: Workload,
                       timeout: float = DEFAULT_TIMEOUT
                       ) -> UpdateStateSuccess:
        """
        Send a request to run a workload.

        Args:
            workload (Workload): The workload object to be run.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while running the workload.
        """
        complete_state = CompleteState()
        complete_state.add_workload(workload)

        # Create the request
        request = Request(request_type="update_state")
        request.set_complete_state(complete_state)
        request.set_masks(workload.masks)

        # Send request
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to run workload: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads)
            )
            return content
        raise AnkaiosException("Received unexpected content type.")

    def get_workload(self, workload_name: str,
                     timeout: float = DEFAULT_TIMEOUT) -> Workload:
        """
        Get the workload with the provided name from the
        requested complete state.

        Args:
            workload_name (str): The name of the workload.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            Workload: The workload object.
        """
        return self.get_state(
            timeout, [f"{WORKLOADS_PREFIX}.{workload_name}"]
        ).get_workloads()[0]

    def delete_workload(self, workload_name: str,
                        timeout: float = DEFAULT_TIMEOUT
                        ) -> UpdateStateSuccess:
        """
        Send a request to delete a workload.

        Args:
            workload_name (str): The name of the workload to be deleted.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred while deleting the workload.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.add_mask(f"{WORKLOADS_PREFIX}.{workload_name}")

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete workload: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads)
            )
            return content
        raise AnkaiosException("Received unexpected content type.")

    def update_configs(self, configs: dict,
                       timeout: float = DEFAULT_TIMEOUT):
        """
        Update the configs. The names will be the keys of the dictionary.

        Args:
            configs (dict): The configs dictionary.
            timeout (float): The maximum time to wait for the response.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred.
        """
        complete_state = CompleteState()
        complete_state.set_configs(configs)

        request = Request(request_type="update_state")
        request.set_complete_state(complete_state)
        request.add_mask(CONFIGS_PREFIX)

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to set the configs: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info("Update successful")
            return
        raise AnkaiosException("Received unexpected content type.")

    def add_config(self, name: str, config: Union[dict, list, str],
                   timeout: float = DEFAULT_TIMEOUT):
        """
        Adds the config with the provided name.
        If the config exists, it will be replaced.

        Args:
            name (str): The name of the config.
            config (Union[dict, list, str]): The config dictionary.
            timeout (float): The maximum time to wait for the response.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred.
        """
        complete_state = CompleteState()
        complete_state.set_configs({name: config})

        request = Request(request_type="update_state")
        request.set_complete_state(complete_state)
        request.add_mask(f"{CONFIGS_PREFIX}.{name}")

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to add the config: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info("Update successful")
            return
        raise AnkaiosException("Received unexpected content type.")

    def get_configs(self,
                    timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the configs. The keys will be the names.

        Returns:
            dict: The configs dictionary.
        """
        return self.get_state(
            timeout, field_masks=[CONFIGS_PREFIX]).get_configs()

    def get_config(self, name: str,
                   timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the config with the provided name.

        Args:
            name (str): The name of the config.

        Returns:
            dict: The config in a dict format.
        """
        return self.get_state(
            timeout, field_masks=[f"{CONFIGS_PREFIX}.{name}"]).get_configs()

    def delete_all_configs(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Delete all the configs.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.add_mask(CONFIGS_PREFIX)

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete all configs: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info("Update successful")
            return
        raise AnkaiosException("Received unexpected content type.")

    def delete_config(self, name: str, timeout: float = DEFAULT_TIMEOUT):
        """
        Delete the config.

        Args:
            name (str): The name of the config.
            timeout (float): The maximum time to wait for the response.

        Raises:
            TimeoutError: If the request timed out.
            AnkaiosException: If an error occurred.
        """
        request = Request(request_type="update_state")
        request.set_complete_state(CompleteState())
        request.add_mask(f"{CONFIGS_PREFIX}.{name}")

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == "error":
            self.logger.error("Error while trying to delete all configs: %s",
                              content)
            raise AnkaiosException(f"Received error: {content}")
        if content_type == "update_state_success":
            self.logger.info("Update successful")
            return
        raise AnkaiosException("Received unexpected content type.")

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
        if content_type == "complete_state":
            return content
        raise AnkaiosException("Received unexpected content type.")

    def get_agents(
            self, timeout: float = DEFAULT_TIMEOUT
            ) -> dict:
        """
        Get the agents from the requested complete state.

        Args:
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            dict: The agents dictionary.
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
            if workload_state.workload_instance_name.workload_name == \
                    workload_name:
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
