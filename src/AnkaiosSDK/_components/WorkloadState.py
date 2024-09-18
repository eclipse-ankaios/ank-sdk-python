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

from typing import TypeAlias
from enum import Enum
from .._protos import _ank_base


__all__ = ["WorkloadStateCollection", "WorkloadState", "WorkloadInstanceName", 
           "WorkloadExecutionState", "WorkloadStateEnum", "WorkloadSubStateEnum"]


class WorkloadStateEnum(Enum):
    AgentDisconnected: int = 0
    Pending: int = 1
    Running: int = 2
    Stopping: int = 3
    Succeeded: int = 4
    Failed: int = 5
    NotScheduled: int = 6
    Removed: int = 7

    def __str__(self) -> str:
        return self.name
    
    @staticmethod
    def _get(field: str) -> "WorkloadStateEnum":
        field = field[0].upper() + field[1:]  # Capitalize the first letter
        return WorkloadStateEnum[field]


class WorkloadSubStateEnum(Enum):
    AGENT_DISCONNECTED: int = 0
    PENDING_INITIAL: int = 1
    PENDING_WAITING_TO_START: int = 2
    PENDING_STARTING: int = 3
    PENDING_STARTING_FAILED: int = 4
    RUNNING_OK: int = 5
    STOPPING: int = 6
    STOPPING_WAITING_TO_STOP: int = 7
    STOPPING_REQUESTED_AT_RUNTIME: int = 8
    STOPPING_DELETE_FAILED: int = 9
    SUCCEEDED_OK: int = 10
    FAILED_EXEC_FAILED: int = 11
    FAILED_UNKNOWN: int = 12
    FAILED_LOST: int = 13
    NOT_SCHEDULED: int = 14
    REMOVED: int = 15

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def _get(state: WorkloadStateEnum, field: _ank_base) -> "WorkloadSubStateEnum":
        proto_mapper = {}
        if state == WorkloadStateEnum.AgentDisconnected:
            proto_mapper = {
                _ank_base.AGENT_DISCONNECTED: WorkloadSubStateEnum.AGENT_DISCONNECTED
            }
        elif state == WorkloadStateEnum.Pending:
            proto_mapper = {
                _ank_base.PENDING_INITIAL: WorkloadSubStateEnum.PENDING_INITIAL,
                _ank_base.PENDING_WAITING_TO_START: WorkloadSubStateEnum.PENDING_WAITING_TO_START,
                _ank_base.PENDING_STARTING: WorkloadSubStateEnum.PENDING_STARTING,
                _ank_base.PENDING_STARTING_FAILED: WorkloadSubStateEnum.PENDING_STARTING_FAILED
            }
        elif state == WorkloadStateEnum.Running:
            proto_mapper = {
                _ank_base.RUNNING_OK: WorkloadSubStateEnum.RUNNING_OK
            }
        elif state == WorkloadStateEnum.Stopping:
            proto_mapper = {
                _ank_base.STOPPING: WorkloadSubStateEnum.STOPPING,
                _ank_base.STOPPING_WAITING_TO_STOP: WorkloadSubStateEnum.STOPPING_WAITING_TO_STOP,
                _ank_base.STOPPING_REQUESTED_AT_RUNTIME: WorkloadSubStateEnum.STOPPING_REQUESTED_AT_RUNTIME,
                _ank_base.STOPPING_DELETE_FAILED: WorkloadSubStateEnum.STOPPING_DELETE_FAILED
            }
        elif state == WorkloadStateEnum.Succeeded:
            proto_mapper = {
                _ank_base.SUCCEEDED_OK: WorkloadSubStateEnum.SUCCEEDED_OK
            }
        elif state == WorkloadStateEnum.Failed:
            proto_mapper = {
                _ank_base.FAILED_EXEC_FAILED: WorkloadSubStateEnum.FAILED_EXEC_FAILED,
                _ank_base.FAILED_UNKNOWN: WorkloadSubStateEnum.FAILED_UNKNOWN,
                _ank_base.FAILED_LOST: WorkloadSubStateEnum.FAILED_LOST
            }
        elif state == WorkloadStateEnum.NotScheduled:
            proto_mapper = {
                _ank_base.NOT_SCHEDULED: WorkloadSubStateEnum.NOT_SCHEDULED
            }
        elif state == WorkloadStateEnum.Removed:
            proto_mapper = {
                _ank_base.REMOVED: WorkloadSubStateEnum.REMOVED
            }
        if field not in proto_mapper:
            raise ValueError(f"No corresponding WorkloadSubStateEnum value for enum: {field}")
        return proto_mapper[field]
    
    def _sub_state2ank_base(self) -> _ank_base:
        try:
            return getattr(_ank_base, self.name)
        except AttributeError:  # pragma: no cover
            raise ValueError(f"No corresponding ank_base value for enum: {self.name}")


class WorkloadExecutionState:
    def __init__(self, state: _ank_base.ExecutionState) -> None:
        self.state: WorkloadStateEnum = None
        self.substate: WorkloadSubStateEnum = None
        self.info: str = None

        self._interpret_state(state)
    
    def _interpret_state(self, exec_state: _ank_base.ExecutionState) -> None:
        self.info = str(exec_state.additionalInfo)

        field = exec_state.WhichOneof("ExecutionStateEnum")
        if field is None:
            raise ValueError("Invalid state for workload.")

        self.state = WorkloadStateEnum._get(field)
        self.substate = WorkloadSubStateEnum._get(self.state, exec_state.__getattribute__(field))


class WorkloadInstanceName:
    def __init__(self, agent_name: str, workload_name: str, workload_id: str) -> None:
        self.agent_name = agent_name
        self.workload_name = workload_name
        self.workload_id = workload_id

    def __str__(self) -> str:
        return f"{self.agent_name}.{self.workload_name}.{self.workload_id}"


class WorkloadState:
    def __init__(self, agent_name: str, workload_name: str, workload_id: str, state: _ank_base.ExecutionState) -> None:
        self.execution_state = WorkloadExecutionState(state)
        self.workload_instance_name = WorkloadInstanceName(agent_name, workload_name, workload_id)


class WorkloadStateCollection:
    ExecutionsStatesForId: TypeAlias = dict[str, WorkloadExecutionState]
    ExecutionsStatesOfWorkload: TypeAlias = dict[str, ExecutionsStatesForId]
    WorkloadStatesMap: TypeAlias = dict[str, ExecutionsStatesOfWorkload]

    def __init__(self) -> None:
        self._workload_states: list[WorkloadState] = []

    def add_workload_state(self, state: WorkloadState) -> None:
        self._workload_states.append(state)

    def get_as_dict(self) -> WorkloadStatesMap:
        return_dict = self.WorkloadStatesMap()
        for state in self._workload_states:

            agent_name = state.workload_instance_name.agent_name
            if agent_name not in return_dict:
                return_dict[agent_name] = self.ExecutionsStatesOfWorkload()

            workload_name = state.workload_instance_name.workload_name
            if workload_name not in return_dict[agent_name]:
                return_dict[agent_name][workload_name] = self.ExecutionsStatesForId()

            workload_id = state.workload_instance_name.workload_id
            return_dict[agent_name][workload_name][workload_id] = state.execution_state
        return return_dict

    def get_as_list(self) -> list[WorkloadState]:
        return self._workload_states
    
    def _from_proto(self, state: _ank_base.WorkloadStatesMap) -> None:
        for agent_name in state.agentStateMap:
            for workload_name in state.agentStateMap[agent_name].wlNameStateMap:
                for workload_id in state.agentStateMap[agent_name].wlNameStateMap[workload_name].idStateMap:
                    self.add_workload_state(WorkloadState(
                        agent_name,
                        workload_name,
                        workload_id,
                        state.agentStateMap[agent_name].wlNameStateMap[workload_name].idStateMap[workload_id]
                    ))


# Example usage
if __name__ == "__main__":
    # Create a WorkloadState object
    workload_state = WorkloadExecutionState(_ank_base.ExecutionState(
        additionalInfo="Info about pending",
        pending=_ank_base.PENDING_STARTING
    ))

    # Print the state, substate, and info
    print(workload_state.state)  # Will get a WorkloadStateEnum object
    print(workload_state.substate)  # Will get a WorkloadSubStateEnum object
    print(workload_state.info)
