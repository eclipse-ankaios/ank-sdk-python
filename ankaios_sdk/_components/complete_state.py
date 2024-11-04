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

- CompleteState:
    Represents the complete state of the Ankaios cluster.

Usage
-----

- Create a CompleteState instance:
    .. code-block:: python

        complete_state = CompleteState()

- Get the API version of the complete state:
    .. code-block:: python

        api_version = complete_state.get_api_version()

- Add a workload to the complete state:
    .. code-block:: python

        complete_state.add_workload(workload)

- Get a workload from the complete state:
    .. code-block:: python

        workload = complete_state.get_workload("nginx")

- Get the entire list of workloads from the complete state:
    .. code-block:: python

        workloads = complete_state.get_workloads()

- Get the connected agents:
    .. code-block:: python

        agents = complete_state.get_agents()

- Get the workload states:
    .. code-block:: python

        workload_states = complete_state.get_workload_states()

- Create a CompleteState instance from a Manifest:
    .. code-block:: python

        complete_state = CompleteState.from_manifest(manifest)
"""

__all__ = ["CompleteState"]

from typing import Union
from .._protos import _ank_base
from .workload import Workload
from .workload_state import WorkloadStateCollection
from .manifest import Manifest
from ..utils import SUPPORTED_API_VERSION


class CompleteState:
    """
    A class to represent the complete state.
    """
    def __init__(self) -> None:
        """
        Initializes an empty CompleteState instance with the given API version.
        """
        self._complete_state = _ank_base.CompleteState()
        self._set_api_version(SUPPORTED_API_VERSION)
        self._workloads: list[Workload] = []
        self._workload_state_collection = WorkloadStateCollection()
        self._configs = {}

    def __str__(self) -> str:
        """
        Returns the string representation of the complete state.

        Returns:
            str: The string representation of the complete state.
        """
        return str(self._to_proto())

    def _set_api_version(self, version: str) -> None:
        """
        Sets the API version for the complete state.

        Args:
            version (str): The API version to set.
        """
        self._complete_state.desiredState.apiVersion = version

    def get_api_version(self) -> str:
        """
        Gets the API version of the complete state.

        Returns:
            str: The API version of the complete state.
        """
        return str(self._complete_state.desiredState.apiVersion)

    def add_workload(self, workload: Workload) -> None:
        """
        Adds a workload to the complete state.

        Args:
            workload (Workload): The workload to add.
        """
        self._workloads.append(workload)
        self._complete_state.desiredState.workloads.\
            workloads[workload.name].CopyFrom(workload._to_proto())

    def get_workload(self, workload_name: str) -> Workload:
        """
        Gets a workload from the complete state by its name.

        Args:
            workload_name (str): The name of the workload to retrieve.

        Returns:
            Workload: The workload with the specified name,
                or None if not found.
        """
        for wl in self._workloads:
            if wl.name == workload_name:
                return wl
        return None

    def get_workloads(self) -> list[Workload]:
        """
        Gets a list of workloads from the complete state.

        Returns:
            list[Workload]: A list of workloads in the complete state.
        """
        return self._workloads

    def get_workload_states(self) -> WorkloadStateCollection:
        """
        Gets the workload states.

        Returns:
            WorkloadStateCollection: The collection of workload states.
        """
        return self._workload_state_collection

    def get_agents(self) -> dict[str, dict]:
        """
        Gets the connected agents and their attributes.

        Returns:
            dict[str, dict]: A dict with the agents and their attributes.
        """
        agents = {}
        for name, attributes in self._complete_state.agents.agents.items():
            agents[name] = {
                "cpu_usage": int(attributes.cpu_usage.cpu_usage),
                "free_memory": attributes.free_memory.free_memory,
            }
        return agents

    def set_configs(self, configs: dict) -> None:
        """
        Sets the configurations in the complete state.

        Args:
            configs (dict): The configurations to set in the complete state.
        """
        def _to_config_item(item: Union[str, list, dict]
                            ) -> _ank_base.ConfigItem:
            config_item = _ank_base.ConfigItem()
            if isinstance(item, str):
                config_item.String = item
            elif isinstance(item, list):
                for value in [_to_config_item(value) for value in item]:
                    config_item.array.values.append(value)
            elif isinstance(item, dict):
                for key, value in item.items():
                    config_item.object.fields[key]. \
                        CopyFrom(_to_config_item(value))
            return config_item

        self._configs = configs
        self._complete_state.desiredState.configs.configs.clear()
        for key, value in self._configs.items():
            self._complete_state.desiredState.configs.configs[key].CopyFrom(
                _to_config_item(value)
            )

    def get_configs(self) -> dict:
        """
        Gets the configurations from the complete state.

        Returns:
            dict: The configurations from the complete state
        """
        return self._configs

    @staticmethod
    def from_manifest(manifest: Manifest) -> 'CompleteState':
        """
        Creates a CompleteState instance from a Manifest.

        Args:
            manifest (Manifest): The manifest to create the
                complete state from.
        """
        state = CompleteState()
        state._complete_state = _ank_base.CompleteState()
        dict_state = manifest._manifest
        state._set_api_version(
            dict_state.get("apiVersion", state.get_api_version())
        )
        state._workloads = []
        if dict_state.get("workloads") is not None:
            for workload_name, workload_dict in \
                    dict_state.get("workloads").items():
                state._workloads.append(
                    Workload._from_dict(workload_name, workload_dict)
                )
        if dict_state.get("configs") is not None:
            state.set_configs(dict_state.get("configs"))
        return state

    def to_dict(self) -> dict:
        """
        Returns the CompleteState as a dictionary

        Returns:
            dict: The CompleteState as a dictionary.
        """
        data = {
            "desired_state": {
                "api_version": self.get_api_version(),
                "workloads": {},
                "configs": self._configs
            },
            "workload_states": {},
            "agents": {}
        }
        for wl in self._workloads:
            data["desired_state"]["workloads"][wl.name] = \
                wl.to_dict()
        wl_states = self._workload_state_collection.get_as_dict()
        for agent_name, exec_states in wl_states.items():
            data["workload_states"][agent_name] = {}
            for workload_name, exec_states_id in exec_states.items():
                data["workload_states"][agent_name][workload_name] = {}
                for workload_id, exec_state in exec_states_id.items():
                    data["workload_states"][agent_name][workload_name][
                        workload_id] = exec_state.to_dict()
        data["agents"] = self.get_agents()
        return data

    def _to_proto(self) -> _ank_base.CompleteState:
        """
        Returns the CompleteState as a proto message.

        Returns:
            _ank_base.CompleteState: The protobuf message representing
                the complete state.
        """
        for workload in self._workloads:
            self._complete_state.desiredState.workloads.\
                workloads[workload.name].CopyFrom(workload._to_proto())
        return self._complete_state

    def _from_proto(self, proto: _ank_base.CompleteState) -> None:
        """
        Converts the proto message to a CompleteState object.

        Args:
            proto (_ank_base.CompleteState): The protobuf message representing
                the complete state.
        """
        def _from_config_item(item: _ank_base.ConfigItem
                              ) -> Union[str, list, dict]:
            if item.HasField("String"):
                return item.String
            if item.HasField("array"):
                return [_from_config_item(value)
                        for value in item.array.values]
            if item.HasField("object"):
                return {key: _from_config_item(value)
                        for key, value in item.object.fields.items()}
            return None  # pragma: no cover

        self._complete_state = proto
        self._workloads = []
        for workload_name, proto_workload in self._complete_state. \
                desiredState.workloads.workloads.items():
            workload = Workload(workload_name)
            workload._from_proto(proto_workload)
            self._workloads.append(workload)
        self._workload_state_collection._from_proto(
            self._complete_state.workloadStates
        )
        configs = {}
        for key, value in self._complete_state.desiredState. \
                configs.configs.items():
            configs[key] = _from_config_item(value)
        self.set_configs(configs)
