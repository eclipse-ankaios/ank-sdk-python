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

from .._protos import _ank_base
from .Workload import Workload
from .WorkloadState import WorkloadStateCollection


__all__ = ["CompleteState"]
DEFAULT_API_VERSION = "v0.1"


class CompleteState:
    """
    A class to represent the complete state
    """
    def __init__(self, api_version: str = DEFAULT_API_VERSION) -> None:
        self._complete_state = _ank_base.CompleteState()
        self._set_api_version(api_version)
        self._workloads: list[Workload] = []
        self._workload_state_collection = WorkloadStateCollection()

    def __str__(self) -> str:
        return str(self._to_proto())

    def _set_api_version(self, version: str) -> None:
        """Set the API version for the complete state."""
        self._complete_state.desiredState.apiVersion = version

    def set_workload(self, workload: Workload) -> None:
        """Add a workload to the complete state."""
        self._workloads.append(workload)

    def get_workload(self, workload_name: str) -> Workload:
        """Get a workload from the complete state by it's name."""
        for wl in self._workloads:
            if wl.name == workload_name:
                return wl
        return None

    def get_workloads(self) -> list[Workload]:
        """Get a workloads dict from the complete state."""
        return self._workloads
    
    def get_workload_states(self) -> WorkloadStateCollection:
        """Get the workload states."""
        return self._workload_state_collection

    def get_agents(self) -> list[str]:
        """Get the connected agents."""
        # Return keys because the value "AgentAttributes" is not yet implemented
        return self._complete_state.agents.keys()
    
    def _from_dict(self, dict_state: dict) -> None:
        """Convert a dictionary to a CompleteState object."""
        self._complete_state = _ank_base.CompleteState()
        self._set_api_version(dict_state.get("apiVersion", DEFAULT_API_VERSION))
        self._workloads = []
        for workload_name, workload_dict in dict_state.get("workloads").items():
            self._workloads.append(Workload._from_dict(workload_name, workload_dict))

    def _to_proto(self) -> _ank_base.CompleteState:
        """Convert the CompleteState object to a proto message."""
        # Clear previous workloads
        for workload in self._workloads:
            self._complete_state.desiredState.workloads.workloads[workload.name].CopyFrom(workload._to_proto())
        return self._complete_state

    def _from_proto(self, proto: _ank_base.CompleteState) -> None:
        """Convert the proto message to a CompleteState object."""
        self._complete_state = proto
        self._workloads = {}
        for workload_name, proto_workload in self._complete_state.desiredState.workloads.workloads.items():
            workload = Workload(workload_name)
            workload._from_proto(proto_workload)
            self._workloads.append(workload)
        self._workload_state_collection._from_proto(self._complete_state.workloadStates)


if __name__ == "__main__":
    complete_state = CompleteState()

    # Create workload
    workload = Workload.builder().workload_name("nginx").build()
    workload2 = Workload.builder().workload_name("dyn_nginx").build()

    # Add workload to complete state
    complete_state.set_workload(workload)
    complete_state.set_workload(workload2)

    print(complete_state)

    new_complete_state = CompleteState()
    new_complete_state._from_proto(complete_state._to_proto())
    print(new_complete_state)

    complete_state_workload_states = CompleteState()
    complete_state_workload_states._from_proto(_ank_base.CompleteState(
        workloadStates=_ank_base.WorkloadStatesMap(agentStateMap={
            "agent_A": _ank_base.ExecutionsStatesOfWorkload(wlNameStateMap={
                "nginx": _ank_base.ExecutionsStatesForId(idStateMap={
                    "1234": _ank_base.ExecutionState(
                        additionalInfo="Random info",
                        succeeded=_ank_base.SUCCEEDED_OK,
                        )
                    })
                }),
            "agent_B": _ank_base.ExecutionsStatesOfWorkload(wlNameStateMap={
                "nginx": _ank_base.ExecutionsStatesForId(idStateMap={
                    "5678": _ank_base.ExecutionState(
                        additionalInfo="Random info",
                        pending=_ank_base.PENDING_WAITING_TO_START,
                        )
                    }),
                "dyn_nginx": _ank_base.ExecutionsStatesForId(idStateMap={
                    "9012": _ank_base.ExecutionState(
                        additionalInfo="Random info",
                        stopping=_ank_base.STOPPING_WAITING_TO_STOP,
                        )
                    })
                })
            })
        )
    )

    print(complete_state_workload_states._complete_state.workloadStates)

    print("\nFor agent_B:")
    workload_states_by_agent = complete_state_workload_states.get_workload_states_on_agent("agent_B")
    for key in workload_states_by_agent:
        print(f"Workload ID: {key}, workload name: {workload_states_by_agent[key][0]}, state: {workload_states_by_agent[key][1]}")

    print("\nFor nginx workloads:")
    workload_states_by_name = complete_state_workload_states.get_workload_states_on_workload_name("nginx")
    for key in workload_states_by_name:
        print(f"Workload ID: {key}, agent name: {workload_states_by_name[key][0]}, state: {workload_states_by_name[key][1]}")
