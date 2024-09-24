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
This script defines the CompleteState class for managing the state of the system.

Classes:
    - CompleteState: Represents the complete state of the system.

Usage:
    - Create a CompleteState instance:
        complete_state = CompleteState()

    - Get the API version of the complete state:
        api_version = complete_state.get_api_version()

    - Add a workload to the complete state:
        complete_state.set_workload(workload)

    - Get a workload from the complete state:
        workload = complete_state.get_workload("nginx")

    - Get a list of workloads from the complete state:
        workloads = complete_state.get_workloads()

    - Get the connected agents:
        agents = complete_state.get_agents()

    - Get the workload states:
        workload_states = complete_state.get_workload_states()
"""

from .._protos import _ank_base
from .Workload import Workload
from .WorkloadState import WorkloadStateCollection


__all__ = ["CompleteState"]
DEFAULT_API_VERSION = "v0.1"


class CompleteState:
    """
    A class to represent the complete state.
    """
    def __init__(self, api_version: str = DEFAULT_API_VERSION) -> None:
        """
        Initializes a CompleteState instance with the given API version.

        Args:
            api_version (str): The API version to set for the complete state.
        """
        self._complete_state = _ank_base.CompleteState()
        self._set_api_version(api_version)
        self._workloads: list[Workload] = []
        self._workload_state_collection = WorkloadStateCollection()

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

    def set_workload(self, workload: Workload) -> None:
        """
        Adds a workload to the complete state.

        Args:
            workload (Workload): The workload to add.
        """
        self._workloads.append(workload)

    def get_workload(self, workload_name: str) -> Workload:
        """
        Gets a workload from the complete state by its name.

        Args:
            workload_name (str): The name of the workload to retrieve.

        Returns:
            Workload: The workload with the specified name, or None if not found.
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

    def get_agents(self) -> list[str]:
        """
        Gets the connected agents.

        Returns:
            list[str]: A list of connected agents.
        """
        # Return keys because the value "AgentAttributes" is not yet implemented
        return list(self._complete_state.agents.agents.keys())

    def _from_dict(self, dict_state: dict) -> None:
        """
        Converts a dictionary to a CompleteState object.

        Args:
            dict_state (dict): The dictionary representing the complete state.
        """
        self._complete_state = _ank_base.CompleteState()
        self._set_api_version(dict_state.get("apiVersion", self.get_api_version()))
        self._workloads = []
        if dict_state.get("workloads") is None:
            return
        for workload_name, workload_dict in dict_state.get("workloads").items():
            self._workloads.append(Workload._from_dict(workload_name, workload_dict))

    def _to_proto(self) -> _ank_base.CompleteState:
        """
        Converts the CompleteState object to a proto message.

        Returns:
            _ank_base.CompleteState: The protobuf message representing the complete state.
        """
        # Clear previous workloads
        for workload in self._workloads:
            self._complete_state.desiredState.workloads.workloads[workload.name]\
                .CopyFrom(workload._to_proto())
        return self._complete_state

    def _from_proto(self, proto: _ank_base.CompleteState) -> None:
        """
        Converts the proto message to a CompleteState object.

        Args:
            proto (_ank_base.CompleteState): The protobuf message representing the complete state.
        """
        self._complete_state = proto
        self._workloads = []
        for workload_name, proto_workload in self._complete_state.desiredState\
                .workloads.workloads.items():
            workload = Workload(workload_name)
            workload._from_proto(proto_workload)
            self._workloads.append(workload)
        self._workload_state_collection._from_proto(self._complete_state.workloadStates)
