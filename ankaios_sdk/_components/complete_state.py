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
This script defines the CompleteState class for managing
the state of the Ankaios cluster.

Classes
-------

- :class:`CompleteState`:
    Represents the complete state of the Ankaios cluster.
- :class:`AgentAttributes`:
    Represents the attributes of an agent in the Ankaios cluster.

Usage
-----

- Create a CompleteState instance:
    .. code-block:: python

        complete_state = CompleteState()

- Create a CompleteState instance from a Manifest:
    .. code-block:: python

        manifest = Manifest()
        complete_state = CompleteState(manifest=manifest)

- Get the API version of the complete state:
    .. code-block:: python

        api_version = complete_state.get_api_version()

- Get a workload from the complete state:
    .. code-block:: python

        workload = complete_state.get_workload("nginx")

- Get the entire list of workloads from the complete state:
    .. code-block:: python

        workloads = complete_state.get_workloads()

- Get the agents and their attributes:
    .. code-block:: python

        agents = complete_state.get_agents()

- Get the workload states:
    .. code-block:: python

        workload_states = complete_state.get_workload_states()

- Get the tags and status of a specific agent:
    .. code-block:: python

        agent_attributes = AgentAttributes()
        tags = agent_attributes.tags
        status = agent_attributes.status
"""

__all__ = ["CompleteState", "AgentAttributes"]

from typing import Union
from .._protos import _ank_base
from .workload import Workload
from .workload_state import WorkloadStateCollection
from .manifest import Manifest
from ..utils import SUPPORTED_API_VERSION, _to_config_item, get_logger


logger = get_logger()


class CompleteState:
    """
    A class to represent the complete state.
    """

    def __init__(
        self,
        manifest: Manifest = None,
        configs: dict = None,
        workloads: list[Workload] = None,
        _proto: _ank_base.CompleteState = None,
    ) -> None:
        """
        Initializes a CompleteState instance with the provided data.

        :param manifest: The manifest to initialize the complete state.
        :type manifest: Manifest
        :param configs: The configurations to set in the complete state.
        :type configs: dict
        :param workloads: The workloads to set in the complete state.
        :type workloads: list[Workload]
        :param _proto: The proto message to initialize the complete state.
        :type _proto: _ank_base.CompleteState
        """
        self._complete_state = _ank_base.CompleteState()
        self._complete_state.desiredState.workloads.workloads.clear()
        self._set_api_version(SUPPORTED_API_VERSION)
        if _proto:
            self._complete_state = _proto
            logger.debug("CompleteState initialized from proto message")
            return
        if manifest:
            self._complete_state.desiredState.CopyFrom(
                manifest._to_desired_state()
            )
            logger.debug("CompleteState initialized from manifest")
            return
        if configs:
            self.set_configs(configs)
            logger.debug("CompleteState initialized from configs")
            return
        if workloads:
            self._complete_state.desiredState.workloads.workloads.clear()
            for workload in workloads:
                self._complete_state.desiredState.workloads.workloads[
                    workload.name
                ].CopyFrom(workload._to_proto())
            logger.debug("CompleteState initialized from workloads")
            return

    def __str__(self) -> str:
        """
        Returns the string representation of the complete state.

        :returns: The string representation of the complete state.
        :rtype: str
        """
        return str(self._to_proto())

    def _set_api_version(self, version: str) -> None:
        """
        Sets the API version for the complete state.

        :param version: The API version to set.
        :type version: str
        """
        self._complete_state.desiredState.apiVersion = version

    def get_api_version(self) -> str:
        """
        Gets the API version of the complete state.

        :returns: The API version of the complete state.
        :rtype: str
        """
        return str(self._complete_state.desiredState.apiVersion)

    def get_workload(self, workload_name: str) -> Workload:
        """
        Gets a workload from the complete state by its name.

        :param workload_name: The name of the workload to retrieve.
        :type workload_name: str

        :returns: The workload with the specified name, or None if not found.
        :rtype: Workload
        """
        if (
            workload_name
            in self._complete_state.desiredState.workloads.workloads.keys()
        ):
            proto_workload = (
                self._complete_state.desiredState.workloads.workloads[
                    workload_name
                ]
            )
            workload = Workload(workload_name)
            workload._from_proto(proto_workload)
            return workload
        return None

    def get_workloads(self) -> list[Workload]:
        """
        Gets a list of workloads from the complete state.

        :returns: A list of workloads in the complete state.
        :rtype: list[Workload]
        """
        workloads = []
        for (
            wl_name,
            proto_workload,
        ) in self._complete_state.desiredState.workloads.workloads.items():
            workload = Workload(wl_name)
            workload._from_proto(proto_workload)
            workloads.append(workload)
        return workloads

    def get_workload_states(self) -> WorkloadStateCollection:
        """
        Gets the workload states.

        :returns: The collection of workload states.
        :rtype: WorkloadStateCollection
        """
        workload_state_collection = WorkloadStateCollection()
        workload_state_collection._from_proto(
            self._complete_state.workloadStates
        )
        return workload_state_collection

    def get_agents(self) -> dict[str, "AgentAttributes"]:
        """
        Gets the connected agents and their attributes.

        :returns: A dict with the agents and their attributes.
        :rtype: dict[str, AgentAttributes]
        """
        agents = {}
        for name, attributes in self._complete_state.agents.agents.items():
            agents[name] = AgentAttributes._from_proto(attributes)
        return agents

    def set_agent_tags(self, agent_name: str, tags: dict[str, str]) -> None:
        """
        Sets the tags for a specific agent.

        :param agent_name: The name of the agent.
        :type agent_name: str
        :param tags: The tags to set for the agent.
        :type tags: dict[str, str]
        """
        agent_attributes = self._complete_state.agents.agents[agent_name]
        agent_attributes.tags.tags.clear()
        for key, value in tags.items():
            agent_attributes.tags.tags[key] = value

    def set_configs(self, configs: dict) -> None:
        """
        Sets the configurations in the complete state.

        :param configs: The configurations to set in the complete state.
        :type configs: dict
        """
        self._complete_state.desiredState.configs.configs.clear()
        for key, value in configs.items():
            self._complete_state.desiredState.configs.configs[key].CopyFrom(
                _to_config_item(value)
            )

    def get_configs(self) -> dict:
        """
        Gets the configurations from the complete state.

        :returns: The configurations from the complete state.
        :rtype: dict
        """

        def _from_config_item(
            item: _ank_base.ConfigItem,
        ) -> Union[str, list, dict]:
            if item.HasField("String"):
                return item.String
            if item.HasField("array"):
                return [
                    _from_config_item(value) for value in item.array.values
                ]
            if item.HasField("object"):
                return {
                    key: _from_config_item(value)
                    for key, value in item.object.fields.items()
                }
            return None  # pragma: no cover

        configs = {}
        for (
            key,
            value,
        ) in self._complete_state.desiredState.configs.configs.items():
            configs[key] = _from_config_item(value)
        return configs

    def to_dict(self) -> dict:
        """
        Returns the CompleteState as a dictionary.

        :returns: The CompleteState as a dictionary.
        :rtype: dict
        """
        data = {
            "desired_state": {
                "api_version": self.get_api_version(),
                "workloads": {},
                "configs": self.get_configs(),
            },
            "workload_states": {},
            "agents": {},
        }
        for workload in self.get_workloads():
            data["desired_state"]["workloads"][
                workload.name
            ] = workload.to_dict()
        wl_states = self.get_workload_states().get_as_dict()
        for agent_name, exec_states in wl_states.items():
            data["workload_states"][agent_name] = {}
            for workload_name, exec_states_id in exec_states.items():
                data["workload_states"][agent_name][workload_name] = {}
                for workload_id, exec_state in exec_states_id.items():
                    data["workload_states"][agent_name][workload_name][
                        workload_id
                    ] = exec_state.to_dict()
        data["agents"] = {}
        for agent_name, agent_attributes in self.get_agents().items():
            data["agents"][agent_name] = agent_attributes.to_dict()
        return data

    def _to_proto(self) -> _ank_base.CompleteState:
        """
        Returns the CompleteState as a proto message.

        :returns: The protobuf message representing the complete state.
        :rtype: _ank_base.CompleteState
        """
        return self._complete_state


class AgentAttributes:
    """
    A class to represent the attributes of an agent.

    :var dict[str, str] tags:
        The agent's tags
    """

    def __init__(self) -> None:
        """
        Initializes an AgentAttributes instance.
        """
        self.tags: dict[str, str] = {}
        self._status: _ank_base.AgentStatus = _ank_base.AgentStatus()

    @property
    def status(self) -> dict[str, str]:
        """
        Gets the status of the agent.

        :returns: The status of the agent.
        :rtype: dict[str, str]
        """
        status = {
            "cpu_usage": int(self._status.cpu_usage.cpu_usage),
            "free_memory": self._status.free_memory.free_memory,
        }
        return status

    def to_dict(self) -> dict[str, Union[dict, str]]:
        """
        Returns the AgentAttributes as a dictionary.

        :returns: The AgentAttributes as a dictionary.
        :rtype: dict[str, Union[dict, str]]
        """
        data = {
            "tags": self.tags,
            "status": self.status,
        }
        return data

    @staticmethod
    def _from_proto(proto: _ank_base.AgentAttributes) -> "AgentAttributes":
        """
        Initializes the AgentAttributes instance from a proto message.

        :param proto: The proto message to initialize the agent attributes.
        :type proto: _ank_base.AgentAttributes
        """
        obj = AgentAttributes()
        obj.tags = dict(proto.tags.tags)
        obj._status = proto.status
        return obj
