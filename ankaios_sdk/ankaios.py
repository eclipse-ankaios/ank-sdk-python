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

- :class:`Ankaios`:
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

Field masks
-----------

Some of the methods support field masks to filter the state.
Some examples of field masks include:
- "desiredState.workloads"  # All workloads in the desired state
- "desiredState.workloads.<workload_name>"  # Workload with the specific name
- "desiredState.configs"  # All configs in the desired state
- "workloadStates"  # All workload states
- "workloadStates.<agent_name>.<workload_name>"  # State of a specific workload
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
    AgentAttributes,
    WorkloadInstanceName,
    WorkloadStateEnum,
    WorkloadExecutionState,
    ControlInterface,
    LogCampaignResponse,
    LogQueue,
    LogResponse,
    LogsRequest,
    LogsCancelRequest,
    EventsRequest,
    EventsCancelRequest,
    EventQueue,
    EventEntry,
)
from .utils import (
    AnkaiosLogLevel,
    get_logger,
    AGENTS_PREFIX,
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

    :var logging.Logger logger:
        The logger for the Ankaios class.
    """

    DEFAULT_TIMEOUT = 5.0
    "(float): The default timeout, if not manually provided."

    def __init__(
        self, log_level: AnkaiosLogLevel = AnkaiosLogLevel.INFO
    ) -> None:
        """
        Initialize the Ankaios object. The logger will be created and
        the connection to the control interface will be established.

        :param log_level: The log level to be set.
        :type log_level: AnkaiosLogLevel

        :raises ConnectionClosedException: If the connection is closed
            at startup.
        """
        # Thread safe queue for responses and logs
        self._responses: Queue = Queue()
        self._logs_callbacks: dict[str, Callable] = {}
        self._events_callbacks: dict[str, Callable] = {}

        self.logger = get_logger()
        self.set_logger_level(log_level)

        # Connect to the control interface
        self._control_interface = ControlInterface(
            add_response_callback=self._add_response,
            add_log_callback=self._add_logs,
            add_event_callback=self._add_events,
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

        :returns: The current object.
        :rtype: Ankaios
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Used for context management. Disconnects from the control interface.

        :param exc_type: The exception type.
        :type exc_type: type
        :param exc_value: The exception instance.
        :type exc_value: Exception
        :param traceback: The traceback object.
        :type traceback: traceback
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

        :param response: The received response.
        :type response: Response
        """
        request_id = response.get_request_id()
        self.logger.debug("Received a response with the id %s", request_id)
        self._responses.put(response)

    def _add_logs(self, request_id: str, logs: list[LogResponse]) -> None:
        """
        Method will be called automatically from the Control Interface
        when a log is received.

        :param request_id: The request id of the logs campaign.
        :type request_id: str
        :param logs: The received logs.
        :type logs: list[`LogResponse`]
        """
        if request_id in self._logs_callbacks:
            for log in logs:
                self._logs_callbacks[request_id](log)
        else:
            self.logger.warning(
                "Received logs for unknown request id %s", request_id
            )

    def _add_events(self, request_id: str, event: EventEntry) -> None:
        """
        Method will be called automatically from the Control Interface
        when an event is received.

        :param request_id: The request id of the event campaign.
        :type request_id: str
        :param event: The event entry.
        :type event: EventEntry
        """
        if request_id in self._events_callbacks:
            self._events_callbacks[request_id](event)
        else:
            self.logger.warning(
                "Received event with unknown request id %s", request_id
            )

    def _get_response_by_id(
        self, request_id: str, timeout: float = DEFAULT_TIMEOUT
    ) -> Response:
        """
        Returns the response by the request id.

        :param request_id: The ID of the request.
        :type request_id: str
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The response object.
        :rtype: Response

        :raises TimeoutError: If response is not received within the timeout.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param request: The request object to be sent.
        :type request: Request
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The response object.
        :rtype: Response

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises ConnectionClosedException: If the connection is closed.
        """
        self._control_interface.write_request(request)
        response = self._get_response_by_id(request.get_id(), timeout)
        return response

    def set_logger_level(self, level: AnkaiosLogLevel) -> None:
        """
        Set the log level of the logger.

        :param level: The log level to be set.
        :type level: AnkaiosLogLevel
        """
        self.logger.setLevel(level.value)

    def apply_manifest(
        self, manifest: Manifest, timeout: float = DEFAULT_TIMEOUT
    ) -> UpdateStateSuccess:
        """
        Send a request to apply a manifest.

        :param manifest: The manifest object to be applied.
        :type manifest: Manifest
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :returns: The update state success object.
        :rtype: UpdateStateSuccess

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param manifest: The manifest object to be deleted.
        :type manifest: Manifest
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :returns: The update state success object.
        :rtype: UpdateStateSuccess

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param workload: The workload object to be run.
        :type workload: Workload
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :returns: The update state success object.
        :rtype: UpdateStateSuccess

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        request = UpdateStateRequest(
            CompleteState(workloads=[workload]), workload._masks
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

        :param workload_name: The name of the workload.
        :type workload_name: str
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The workloads that match the name.
        :rtype: list[Workload]

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
        """
        return self.get_state(
            [f"{WORKLOADS_PREFIX}.{workload_name}"], timeout
        ).get_workloads()

    def delete_workload(
        self, workload_name: str, timeout: float = DEFAULT_TIMEOUT
    ) -> UpdateStateSuccess:
        """
        Send a request to delete a workload.

        :param workload_name: The name of the workload to be deleted.
        :type workload_name: str
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :returns: The update state success object.
        :rtype: UpdateStateSuccess

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param configs: The configs dictionary.
        :type configs: dict
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param name: The name of the config.
        :type name: str
        :param config: The config dictionary.
        :type config: Union[dict, list, str]
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :returns: The configs dictionary.
        :rtype: dict

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
        """
        return (
            self.get_state(field_masks=[CONFIGS_PREFIX]).get_configs(),
            timeout,
        )

    def get_config(self, name: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the config with the provided name.

        :param name: The name of the config.
        :type name: str
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :returns: The config in a dict format.
        :rtype: dict

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param name: The name of the config.
        :type name: str
        :param timeout: The maximum time to wait for the response.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param field_masks: The list of field masks to filter the state.
        :type field_masks: list[str]
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The complete state object.
        :rtype: CompleteState

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
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

    def set_agent_tags(
        self,
        agent_name: str,
        tags: dict[str, str],
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Set the tags for a specific agent.

        :param agent_name: The name of the agent.
        :type agent_name: str
        :param tags: The tags to be set.
        :type tags: dict[str, str]
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
        """
        # Create the request
        complete_state = CompleteState()
        complete_state.set_agent_tags(agent_name, tags)
        request = UpdateStateRequest(
            complete_state, [f"{AGENTS_PREFIX}.{agent_name}.tags"]
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
                "Error while trying to set agent tags: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.UPDATE_STATE_SUCCESS:
            self.logger.info("Update successful")
            return
        raise AnkaiosProtocolException("Received unexpected content type.")

    def get_agents(self, timeout: float = DEFAULT_TIMEOUT) -> dict:
        """
        Get the agents and their attributes.

        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The agents dictionary.
        :rtype: dict

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
        """
        return self.get_state([f"{AGENTS_PREFIX}"], timeout).get_agents()

    def get_agent(
        self, agent_name: str, timeout: float = DEFAULT_TIMEOUT
    ) -> AgentAttributes:
        """
        Get the attributes of a specific agent.

        :param agent_name: The name of the agent.
        :type agent_name: str
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The attributes of the agent.
        :rtype: AgentAttributes

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state or the agent is not found.
        :raises ConnectionClosedException: If the connection is closed.
        """
        agents = self.get_state(
            field_masks=[f"{AGENTS_PREFIX}.{agent_name}"], timeout=timeout
        ).get_agents()

        if agent_name not in agents:
            self.logger.error("Agent %s not found", agent_name)
            raise AnkaiosProtocolException(f"Agent {agent_name} not found")
        return agents[agent_name]

    def get_workload_states(
        self, timeout: float = DEFAULT_TIMEOUT
    ) -> WorkloadStateCollection:
        """
        Get the workload states from the requested complete state.

        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The collection of workload states.
        :rtype: WorkloadStateCollection

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param instance_name: The instance name of the workload.
        :type instance_name: WorkloadInstanceName
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The specified workload's execution state.
        :rtype: WorkloadExecutionState

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param agent_name: The name of the agent.
        :type agent_name: str
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The collection of workload states.
        :rtype: WorkloadStateCollection

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
        """
        state = self.get_state(["workloadStates." + agent_name], timeout)
        return state.get_workload_states()

    def get_workload_states_for_name(
        self, workload_name: str, timeout: float = DEFAULT_TIMEOUT
    ) -> WorkloadStateCollection:
        """
        Get the workload states for a specific workload name from the
        requested complete state.

        :param workload_name: The name of the workload.
        :type workload_name: str
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The collection of workload states.
        :rtype: WorkloadStateCollection

        :raises TimeoutError: If the request timed out.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param instance_name: The instance name of the workload.
        :type instance_name: WorkloadInstanceName
        :param state: The state to wait for.
        :type state: WorkloadStateEnum
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :raises TimeoutError: If the request timed out or if the workload
            did not reach the state in time.
        :raises ControlInterfaceException: If not connected.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If an error occurred while getting
            the state.
        :raises ConnectionClosedException: If the connection is closed.
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

        :param workload_names: The workload instance names
            for which to get logs.
        :type workload_names: list[WorkloadInstanceName]
        :param follow: If true, the logs will be continuously streamed.
        :type follow: bool
        :param tail: The number of lines to display from the end of the logs.
        :type tail: int
        :param since: The start time for the logs. If string, it must be in
            the RFC3339 format.
        :type since: Union[str, datetime]
        :param until: The end time for the logs. If string, it must be in
            the RFC3339 format.
        :type until: Union[str, datetime]
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The log campaign response object.
        :rtype: LogCampaignResponse

        :raises ControlInterfaceException: If not connected.
        :raises ConnectionClosedException: If the connection is closed.
        """

        request = LogsRequest(
            workload_names=workload_names,
            follow=follow,
            tail=tail,
            since=since,
            until=until,
        )

        # Create the logs queue and get the request id
        log_queue = LogQueue(request.get_id())

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

        :param log_campaign: The log campaign response.
        :type log_campaign: LogCampaignResponse
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises ConnectionClosedException: If the connection is closed.
        """
        request = LogsCancelRequest(request_id=log_campaign.queue._request_id)

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

    def register_event(
        self, field_masks: list[str], timeout: float = DEFAULT_TIMEOUT
    ) -> "EventQueue":
        """
        Register an event.

        :param field_masks: The masks to filter the state for events.
        :type field_masks: list[str]
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :returns: The event queue.
        :rtype: EventQueue

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
        """
        request = EventsRequest(masks=field_masks)

        # Create the event queue and get the request id
        event_queue = EventQueue(request.get_id())

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to register event: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.COMPLETE_STATE:
            self.logger.info("Event registered successfully, state received.")
            self._events_callbacks[request.get_id()] = event_queue.add_event
            return event_queue
        raise AnkaiosProtocolException("Received unexpected content type.")

    def unregister_event(
        self, event_queue: "EventQueue", timeout: float = DEFAULT_TIMEOUT
    ) -> None:
        """
        Unregister an event.

        :param event_queue: The event queue to be unregistered.
        :type event_queue: EventQueue
        :param timeout: The maximum time to wait for the response, in seconds.
        :type timeout: float

        :raises ControlInterfaceException: If not connected.
        :raises TimeoutError: If the request timed out.
        :raises AnkaiosResponseError: If the response is an error.
        :raises AnkaiosProtocolException: If the response has unexpected
            content type.
        :raises ConnectionClosedException: If the connection is closed.
        """
        request = EventsCancelRequest(request_id=event_queue._request_id)

        try:
            response = self._send_request(request, timeout)
        except TimeoutError as e:
            self.logger.error("%s", e)
            raise e

        # Interpret response
        (content_type, content) = response.get_content()
        if content_type == ResponseType.ERROR:
            self.logger.error(
                "Error while trying to unregister event: %s", content
            )
            raise AnkaiosResponseError(f"Received error: {content}")
        if content_type == ResponseType.EVENT_CANCEL_ACCEPTED:
            self.logger.info("Event unregister request accepted.")
            self._events_callbacks.pop(request.get_id(), None)
            return None
        raise AnkaiosProtocolException("Received unexpected content type.")
