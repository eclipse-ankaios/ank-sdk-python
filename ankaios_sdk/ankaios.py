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
        del ankaios

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

        try:
            ankaios.wait_for_workload_to_reach_state(
                instance_name,
                WorkloadStateEnum.RUNNING
            )
        except TimeoutError:
            print(f"State not reached in time.")
        else:
            print(f"State reached.")
"""

__all__ = ["Ankaios"]

import time
from typing import Union, Callable
from datetime import datetime
from queue import Queue, Empty

from .exceptions import (
    AnkaiosProtocolException,
    AnkaiosResponseError,
    ConnectionClosedException,
)
from ._components import (
    Workload,
    CompleteState,
    Request,
    UpdateStateRequest,
    GetStateRequest,
    Response,
    ResponseType,
    UpdateStateSuccess,
    WorkloadStateCollection,
    Manifest,
    WorkloadInstanceName,
    WorkloadStateEnum,
    WorkloadExecutionState,
    ControlInterface,
    LogCampaignResponse,
    LogQueue,
    LogResponse,
    LogsRequest,
)
from .utils import (
    AnkaiosLogLevel,
    get_logger,
    WORKLOADS_PREFIX,
    CONFIGS_PREFIX,
)


# pylint: disable=too-many-public-methods, too-many-instance-attributes
# pylint: disable=too-many-lines
class Ankaios:
    """
    This class is used to interact with the Ankaios using an intuitive API.
    The class automatically handles the session creation and the requests
    and responses sent and received over the Ankaios Control Interface.

    Attributes:
        logger (logging.Logger): The logger for the Ankaios class.
    """

    DEFAULT_TIMEOUT = 5.0
    "(float): The default timeout, if not manually provided."

    def __init__(
        self, log_level: AnkaiosLogLevel = AnkaiosLogLevel.INFO
    ) -> None:
        """
        Initialize the Ankaios object. The logger will be created and
        the connection to the control interface will be established.

        Args:
            log_level (AnkaiosLogLevel): The log level to be set.

        Raises:
            ConnectionClosedException: If the connection is closed
                at startup.
        """
        # Thread safe queue for responses and logs
        self._responses: Queue = Queue()
        self._logs_callbacks: dict[str, Callable] = {}

        self.logger = get_logger()
        self.set_logger_level(log_level)

        # Connect to the control interface
        self._control_interface = ControlInterface(
            add_response_callback=self._add_response,
            add_log_callback=self._add_logs,
        )
        self._control_interface.connect()

        # Wait for the connection to be established
        start_time = time.time()
        while not self._control_interface.connected:
            if time.time() - start_time > self.DEFAULT_TIMEOUT:
                self.logger.error(
                    "Connection to the control interface timed out."
                )
                self._control_interface.disconnect()
                raise ConnectionClosedException(
                    "Connection to the control interface timed out."
                )
            time.sleep(0.1)

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
            self.logger.error(
                "An exception occurred: %s, %s, %s",
                exc_type,
                exc_value,
                traceback,
            )
        self._control_interface.disconnect()

    def _add_response(self, response: Response) -> None:
        """
        Method will be called automatically from the Control Interface
        when a response is received.
        """
        request_id = response.get_request_id()
        self.logger.debug("Received a response with the id %s", request_id)
        self._responses.put(response)

    def _add_logs(self, request_id: str, logs: list[LogResponse]) -> None:
        """
        Method will be called automatically from the Control Interface
        when a log is received.
        """
        if request_id in self._logs_callbacks:
            for log in logs:
                self._logs_callbacks[request_id](log)
        else:
            self.logger.warning(
                "Received logs for unknown request id %s", request_id
            )

    def _get_response_by_id(
        self, request_id: str, timeout: float = DEFAULT_TIMEOUT
    ) -> Response:
        """
        Returns the response by the request id.

        Args:
            request_id (str): The ID of the request.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            Response: The response object.

        Raises:
            TimeoutError: If response is not received within the timeout.
            ConnectionClosedException: If the connection is closed.
        """
        response: Response = None
        response_id = None
        while True:
            try:
                response = self._responses.get(timeout=timeout)
                response_id = response.get_request_id()
            except Empty as exc:
                self.logger.error("Timeout while waiting for response.")
                raise TimeoutError(
                    "Timeout while waiting for response."
                ) from exc

            if response.content_type == ResponseType.CONNECTION_CLOSED:
                self.logger.error("Connection closed.")
                raise ConnectionClosedException(response.content)

            if response_id != request_id:
                self.logger.warning(
                    "Received a response with the wrong id: %s", response_id
                )
                continue
            break
        return response

    def _send_request(
        self, request: Request, timeout: float = DEFAULT_TIMEOUT
    ) -> Response:
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
            ControlInterfaceException: If not connected.
            ConnectionClosedException: If the connection is closed.
        """
        self._control_interface.write_request(request)
        response = self._get_response_by_id(request.get_id(), timeout)
        return response

    def set_logger_level(self, level: AnkaiosLogLevel) -> None:
        """
        Set the log level of the logger.

        Args:
            level (AnkaiosLogLevel): The log level to be set.
        """
        self.logger.setLevel(level.value)

    def apply_manifest(
        self, manifest: Manifest, timeout: float = DEFAULT_TIMEOUT
    ) -> UpdateStateSuccess:
        """
        Send a request to apply a manifest.

        Args:
            manifest (Manifest): The manifest object to be applied.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(manifest=manifest), manifest._calculate_masks()
        )

        # Send request
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to apply manifest: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads),
            )
            return content
        raise AnkaiosProtocolException("Received unexpected content type.")

    def delete_manifest(
        self, manifest: Manifest, timeout: float = DEFAULT_TIMEOUT
    ) -> UpdateStateSuccess:
        """
        Send a request to delete a manifest.

        Args:
            manifest (Manifest): The manifest object to be deleted.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(), manifest._calculate_masks()
        )

        # Send request
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to delete manifest: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads),
            )
            return content
        raise AnkaiosProtocolException("Received unexpected content type.")

    def apply_workload(
        self, workload: Workload, timeout: float = DEFAULT_TIMEOUT
    ) -> UpdateStateSuccess:
        """
        Send a request to run a workload.

        Args:
            workload (Workload): The workload object to be run.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(workloads=[workload]), workload.masks
        )

        # Send request
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to run workload: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads),
            )
            return content
        raise AnkaiosProtocolException("Received unexpected content type.")

    def get_workload(
        self, workload_name: str, timeout: float = DEFAULT_TIMEOUT
    ) -> list[Workload]:
        """
        Get the workload with the provided name from the
        requested complete state.

        Args:
            workload_name (str): The name of the workload.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            list[Workload]: The workloads that match the name.

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        return self.get_state(
            [f"{WORKLOADS_PREFIX}.{workload_name}"], timeout
        ).get_workloads()

    def delete_workload(
        self, workload_name: str, timeout: float = DEFAULT_TIMEOUT
    ) -> UpdateStateSuccess:
        """
        Send a request to delete a workload.

        Args:
            workload_name (str): The name of the workload to be deleted.
            timeout (float): The maximum time to wait for the response.

        Returns:
            UpdateStateSuccess: The update state success object.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(), [f"{WORKLOADS_PREFIX}.{workload_name}"]
        )

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to delete workload: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info(
                "Update successful: %s added workloads, "
                + "%s deleted workloads.",
                len(content.added_workloads),
                len(content.deleted_workloads),
            )
            return content
        raise AnkaiosProtocolException("Received unexpected content type.")

    def update_configs(self, configs: dict, timeout: float = DEFAULT_TIMEOUT):
        """
        Update the configs. The names will be the keys of the dictionary.

        Args:
            configs (dict): The configs dictionary.
            timeout (float): The maximum time to wait for the response.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(configs=configs), [CONFIGS_PREFIX]
        )

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to set the configs: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info("Update successful")
            return
        raise AnkaiosProtocolException("Received unexpected content type.")

    def add_config(
        self,
        name: str,
        config: Union[dict, list, str],
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Adds the config with the provided name.
        If the config exists, it will be replaced.

        Args:
            name (str): The name of the config.
            config (Union[dict, list, str]): The config dictionary.
            timeout (float): The maximum time to wait for the response.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(configs={name: config}), [f"{CONFIGS_PREFIX}.{name}"]
        )

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to add the config: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info("Update successful")
            return
        raise AnkaiosProtocolException("Received unexpected content type.")

    def get_configs(self, timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the configs. The keys will be the names.

        Returns:
            dict: The configs dictionary.

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        return (
            self.get_state(field_masks=[CONFIGS_PREFIX]).get_configs(),
            timeout,
        )

    def get_config(self, name: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the config with the provided name.

        Args:
            name (str): The name of the config.

        Returns:
            dict: The config in a dict format.

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        return (
            self.get_state(
                field_masks=[f"{CONFIGS_PREFIX}.{name}"]
            ).get_configs(),
            timeout,
        )

    def delete_all_configs(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Delete all the configs.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(CompleteState(), [CONFIGS_PREFIX])

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to delete all configs: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info("Update successful")
            return
        raise AnkaiosProtocolException("Received unexpected content type.")

    def delete_config(self, name: str, timeout: float = DEFAULT_TIMEOUT):
        """
        Delete the config.

        Args:
            name (str): The name of the config.
            timeout (float): The maximum time to wait for the response.

        Raises:
            ControlInterfaceException: If not connected.
            TimeoutError: If the request timed out.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If the response has unexpected
                content type.
            ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(), [f"{CONFIGS_PREFIX}.{name}"]
        )

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to delete config: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info("Update successful")
            return
        raise AnkaiosProtocolException("Received unexpected content type.")

    def get_state(
        self,
        field_masks: list[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> CompleteState:
        """
        Send a request to get the complete state.

        Args:
            field_masks (list[str]): The list of field masks to filter
                the state.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            CompleteState: The complete state object.

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        request = GetStateRequest(
            field_masks if field_masks is not None else []
        )
        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error("Error while trying to get state: %s", content)
            raise AnkaiosResponseError(content)
        if content_type == ResponseType.COMPLETE_STATE:
            return content
        raise AnkaiosProtocolException("Received unexpected content type.")

    def get_agents(self, timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the agents from the requested complete state.

        Args:
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            dict: The agents dictionary.

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        return self.get_state(None, timeout).get_agents()

    def get_workload_states(
        self, timeout: float = DEFAULT_TIMEOUT
    ) -> WorkloadStateCollection:
        """
        Get the workload states from the requested complete state.

        Args:
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            WorkloadStateCollection: The collection of workload states.

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        return self.get_state(
            ["workloadStates"], timeout
        ).get_workload_states()

    def get_execution_state_for_instance_name(
        self,
        instance_name: WorkloadInstanceName,
        timeout: float = DEFAULT_TIMEOUT,
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
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        state = self.get_state([instance_name.get_filter_mask()], timeout)
        workload_states = state.get_workload_states().get_as_list()
        if len(workload_states) != 1:
            self.logger.error(
                "Expected exactly one workload state "
                + "for instance name %s, but got %s",
                instance_name,
                len(workload_states),
            )
            raise AnkaiosProtocolException(
                "Expected exactly one workload state for instance name "
                + f"{instance_name}, but got {len(workload_states)}"
            )
        return workload_states[0].execution_state

    def get_workload_states_on_agent(
        self, agent_name: str, timeout: float = DEFAULT_TIMEOUT
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

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        state = self.get_state(["workloadStates." + agent_name], timeout)
        return state.get_workload_states()

    def get_workload_states_for_name(
        self, workload_name: str, timeout: float = DEFAULT_TIMEOUT
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

        Raises:
            TimeoutError: If the request timed out.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
        """
        state = self.get_state(["workloadStates"], timeout)
        workload_states = state.get_workload_states().get_as_list()
        workload_states_for_name = WorkloadStateCollection()
        for workload_state in workload_states:
            if (
                workload_state.workload_instance_name.workload_name
                == workload_name
            ):
                workload_states_for_name.add_workload_state(workload_state)
        return workload_states_for_name

    def wait_for_workload_to_reach_state(
        self,
        instance_name: WorkloadInstanceName,
        state: WorkloadStateEnum,
        timeout: float = DEFAULT_TIMEOUT,
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
            TimeoutError: If the request timed out or if the workload
                did not reach the state in time.
            ControlInterfaceException: If not connected.
            AnkaiosResponseError: If the response is an error.
            AnkaiosProtocolException: If an error occurred while getting
                the state.
            ConnectionClosedException: If the connection is closed.
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

    # pylint: disable=too-many-arguments
    def request_logs(
        self,
        workload_names: list[WorkloadInstanceName],
        *,
        follow: bool = False,
        tail: int = -1,
        since: Union[str, datetime] = "",
        until: Union[str, datetime] = "",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> LogCampaignResponse:
        """
        Request logs for the specified workloads.

        Args:
            workload_names (list[WorkloadInstanceName]): The workload
                instance names for which to get logs.
            follow (bool): If true, the logs will be continuously streamed.
            tail (int): The number of lines to display from
                the end of the logs.
            since (str / datetime): The start time for the logs. If string,
                it must be in the RFC3339 format.
            until (str / datetime): The end time for the logs. If string,
                it must be in the RFC3339 format.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Returns:
            LogCampaignResponse: The log campaign response object.

        Raises:
            ControlInterfaceException: If not connected.
            ConnectionClosedException: If the connection is closed.
        """

        logs_request = LogsRequest(
            workload_names=workload_names,
            follow=follow,
            tail=tail,
            since=since,
            until=until,
        )

        # Create the logs queue and get the request
        log_queue = LogQueue(logs_request)
        request = log_queue._get_request()

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to set the configs: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.LOGS_REQUEST_ACCEPTED:
            self.logger.info("Logs request accepted, waiting for logs.")
            self._logs_callbacks[request.get_id()] = log_queue.put
            return LogCampaignResponse(
                queue=log_queue, accepted_workload_names=content
            )
        raise AnkaiosProtocolException("Received unexpected content type.")

    def stop_receiving_logs(
        self,
        log_campaign: LogCampaignResponse,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """
        Stop receiving logs from the specified LogCampaignResponse.

        Args:
            log_campaign (LogCampaignResponse): The log campaign response.
            timeout (float): The maximum time to wait for the response,
                in seconds.

        Raises:
            ControlInterfaceException: If not connected.
            ConnectionClosedException: If the connection is closed.
        """
        # Get the cancel request
        request = log_campaign.queue._get_cancel_request()

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to set the configs: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.LOGS_CANCEL_ACCEPTED:
            self.logger.info("Logs cancel request accepted.")
            self._logs_callbacks.pop(request.get_id(), None)
            return None
        raise AnkaiosProtocolException("Received unexpected content type.")
