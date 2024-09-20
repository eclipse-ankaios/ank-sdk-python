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
This module defines various classes and enumerations related to the state of workloads.
It provides functionality to interpret and manage the states and sub-states of workloads, 
including converting between different representations and handling collections of workload states.

Classes:
    WorkloadExecutionState: Represents the execution state and sub-state of a workload.
    WorkloadInstanceName: Represents the name of a workload instance.
    WorkloadState: Represents the state of a workload (execution state and name).
    WorkloadStateCollection: A collection of workload states.

Enums:
    WorkloadStateEnum: Enumeration for different states of a workload.
    WorkloadSubStateEnum: Enumeration for different sub-states of a workload.

Usage:
    - Get all workload states:
        workload_state_collection = WorkloadStateCollection()
        list_of_workload_states = workload_state_collection.get_as_list()
        dict_of_workload_states = workload_state_collection.get_as_dict()

    - Unpack a workload state:
        workload_state = WorkloadState()
        agent_name = workload_state.workload_instance_name.agent_name
        workload_name = workload_state.workload_instance_name.workload_name
        state = workload_state.execution_state.state
        substate = workload_state.execution_state.substate
        info = workload_state.execution_state.info
"""

from typing import TypeAlias
from enum import Enum
from .._protos import _ank_base


__all__ = ["WorkloadStateCollection", "WorkloadState", "WorkloadInstanceName",
           "WorkloadExecutionState", "WorkloadStateEnum", "WorkloadSubStateEnum"]


class WorkloadStateEnum(Enum):
    """
    Enumeration for different states of a workload.

    Attributes:
        AgentDisconnected (int): The agent is disconnected.
        Pending (int): The workload is pending.
        Running (int): The workload is running.
        Stopping (int): The workload is stopping.
        Succeeded (int): The workload has succeeded.
        Failed (int): The workload has failed.
        NotScheduled (int): The workload is not scheduled.
        Removed (int): The workload has been removed.
    """
    AgentDisconnected: int = 0
    Pending: int = 1
    Running: int = 2
    Stopping: int = 3
    Succeeded: int = 4
    Failed: int = 5
    NotScheduled: int = 6
    Removed: int = 7

    def __str__(self) -> str:
        """
        Return the name of the enumeration member.

        Returns:
            str: The name of the enumeration member.
        """
        return self.name

    @staticmethod
    def _get(field: str) -> "WorkloadStateEnum":
        """
        Get the enumeration member corresponding to the given field name.

        Args:
            field (str): The field name to look up.

        Returns:
            WorkloadStateEnum: The enumeration member corresponding to the field name.

        Raises:
            KeyError: If the field name does not correspond to any enumeration member.
        """
        field = field[0].upper() + field[1:]  # Capitalize the first letter
        return WorkloadStateEnum[field]


class WorkloadSubStateEnum(Enum):
    """
    Enumeration for different sub-states of a workload.

    Attributes:
        AGENT_DISCONNECTED (int): The agent is disconnected.
        PENDING_INITIAL (int): The workload is in the initial pending state.
        PENDING_WAITING_TO_START (int): The workload is waiting to start.
        PENDING_STARTING (int): The workload is starting.
        PENDING_STARTING_FAILED (int): The workload failed to start.
        RUNNING_OK (int): The workload is running successfully.
        STOPPING (int): The workload is stopping.
        STOPPING_WAITING_TO_STOP (int): The workload is waiting to stop.
        STOPPING_REQUESTED_AT_RUNTIME (int): The workload stop was requested at runtime.
        STOPPING_DELETE_FAILED (int): The workload stop failed to delete.
        SUCCEEDED_OK (int): The workload succeeded successfully.
        FAILED_EXEC_FAILED (int): The workload failed due to execution failure.
        FAILED_UNKNOWN (int): The workload failed due to an unknown reason.
        FAILED_LOST (int): The workload failed because it was lost.
        NOT_SCHEDULED (int): The workload is not scheduled.
        REMOVED (int): The workload has been removed.
    """
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
        """
        Return the name of the enumeration member.

        Returns:
            str: The name of the enumeration member.
        """
        return self.name

    @staticmethod
    def _get(state: WorkloadStateEnum, field: _ank_base) -> "WorkloadSubStateEnum":
        """
        Get the enumeration member corresponding to the given state and field.

        Args:
            state (WorkloadStateEnum): The state of the workload.
            field (_ank_base): The field to look up.

        Returns:
            WorkloadSubStateEnum: The enumeration member corresponding to the state and field.

        Raises:
            ValueError: If the field does not correspond to any enumeration member.
        """
        proto_mapper = {}
        if state == WorkloadStateEnum.AgentDisconnected:
            proto_mapper = {
                _ank_base.AGENT_DISCONNECTED:
                    WorkloadSubStateEnum.AGENT_DISCONNECTED
            }
        elif state == WorkloadStateEnum.Pending:
            proto_mapper = {
                _ank_base.PENDING_INITIAL:
                    WorkloadSubStateEnum.PENDING_INITIAL,
                _ank_base.PENDING_WAITING_TO_START:
                    WorkloadSubStateEnum.PENDING_WAITING_TO_START,
                _ank_base.PENDING_STARTING:
                    WorkloadSubStateEnum.PENDING_STARTING,
                _ank_base.PENDING_STARTING_FAILED:
                    WorkloadSubStateEnum.PENDING_STARTING_FAILED
            }
        elif state == WorkloadStateEnum.Running:
            proto_mapper = {
                _ank_base.RUNNING_OK: WorkloadSubStateEnum.RUNNING_OK
            }
        elif state == WorkloadStateEnum.Stopping:
            proto_mapper = {
                _ank_base.STOPPING: WorkloadSubStateEnum.STOPPING,
                _ank_base.STOPPING_WAITING_TO_STOP:
                    WorkloadSubStateEnum.STOPPING_WAITING_TO_STOP,
                _ank_base.STOPPING_REQUESTED_AT_RUNTIME:
                    WorkloadSubStateEnum.STOPPING_REQUESTED_AT_RUNTIME,
                _ank_base.STOPPING_DELETE_FAILED:
                    WorkloadSubStateEnum.STOPPING_DELETE_FAILED
            }
        elif state == WorkloadStateEnum.Succeeded:
            proto_mapper = {
                _ank_base.SUCCEEDED_OK:
                    WorkloadSubStateEnum.SUCCEEDED_OK
            }
        elif state == WorkloadStateEnum.Failed:
            proto_mapper = {
                _ank_base.FAILED_EXEC_FAILED:
                    WorkloadSubStateEnum.FAILED_EXEC_FAILED,
                _ank_base.FAILED_UNKNOWN:
                    WorkloadSubStateEnum.FAILED_UNKNOWN,
                _ank_base.FAILED_LOST:
                    WorkloadSubStateEnum.FAILED_LOST
            }
        elif state == WorkloadStateEnum.NotScheduled:
            proto_mapper = {
                _ank_base.NOT_SCHEDULED:
                    WorkloadSubStateEnum.NOT_SCHEDULED
            }
        elif state == WorkloadStateEnum.Removed:
            proto_mapper = {
                _ank_base.REMOVED:
                    WorkloadSubStateEnum.REMOVED
            }
        if field not in proto_mapper:
            raise ValueError(f"No corresponding WorkloadSubStateEnum value for enum: {field}")
        return proto_mapper[field]

    def _sub_state2ank_base(self) -> _ank_base:
        """
        Convert the WorkloadSubStateEnum member to the corresponding _ank_base value.

        Returns:
            _ank_base: The corresponding _ank_base value.

        Raises:
            ValueError: If there is no corresponding _ank_base value for the enumeration member.
        """
        try:
            return getattr(_ank_base, self.name)
        except AttributeError as e:  # pragma: no cover
            raise ValueError(f"No corresponding ank_base value for enum: {self.name}") from e


# pylint: disable=too-few-public-methods
class WorkloadExecutionState:
    """
    Represents the execution state of a workload.

    Attributes:
        state (WorkloadStateEnum): The state of the workload.
        substate (WorkloadSubStateEnum): The sub-state of the workload.
        info (str): Additional information about the workload state.
    """
    def __init__(self, state: _ank_base.ExecutionState) -> None:
        """
        Initializes a WorkloadExecutionState instance.

        Args:
            state (_ank_base.ExecutionState): The execution state to interpret.
        """
        self.state: WorkloadStateEnum = None
        self.substate: WorkloadSubStateEnum = None
        self.info: str = None

        self._interpret_state(state)

    def _interpret_state(self, exec_state: _ank_base.ExecutionState) -> None:
        """
        Interprets the execution state and sets the state, substate, and info attributes.

        Args:
            exec_state (_ank_base.ExecutionState): The execution state to interpret.

        Raises:
            ValueError: If the execution state is invalid.
        """
        self.info = str(exec_state.additionalInfo)

        field = exec_state.WhichOneof("ExecutionStateEnum")
        if field is None:
            raise ValueError("Invalid state for workload.")

        self.state = WorkloadStateEnum._get(field)  # pylint: disable=protected-access
        self.substate = WorkloadSubStateEnum._get(self.state, getattr(exec_state, field))  # pylint: disable=protected-access


# pylint: disable=too-few-public-methods
class WorkloadInstanceName:
    """
    Represents the name of a workload instance.

    Attributes:
        agent_name (str): The name of the agent.
        workload_name (str): The name of the workload.
        workload_id (str): The ID of the workload.
    """
    def __init__(self, agent_name: str, workload_name: str, workload_id: str) -> None:
        """
        Initializes a WorkloadInstanceName instance.

        Args:
            agent_name (str): The name of the agent.
            workload_name (str): The name of the workload.
            workload_id (str): The ID of the workload.
        """
        self.agent_name = agent_name
        self.workload_name = workload_name
        self.workload_id = workload_id

    def __str__(self) -> str:
        """
        Returns the string representation of the workload instance name.

        Returns:
            str: The string representation of the workload instance name.
        """
        return f"{self.agent_name}.{self.workload_name}.{self.workload_id}"


# pylint: disable=too-few-public-methods
class WorkloadState:
    """
    Represents the state of a workload.

    Attributes:
        execution_state (WorkloadExecutionState): The execution state of the workload.
        workload_instance_name (WorkloadInstanceName): The name of the workload instance.
    """
    def __init__(self, agent_name: str, workload_name: str,
                 workload_id: str, state: _ank_base.ExecutionState) -> None:
        """
        Initializes a WorkloadState instance.

        Args:
            agent_name (str): The name of the agent.
            workload_name (str): The name of the workload.
            workload_id (str): The ID of the workload.
            state (_ank_base.ExecutionState): The execution state to interpret.
        """
        self.execution_state = WorkloadExecutionState(state)
        self.workload_instance_name = WorkloadInstanceName(agent_name, workload_name, workload_id)


class WorkloadStateCollection:
    """
    A class that represents a collection of workload states and provides methods to manipulate them.
    """
    ExecutionsStatesForId: TypeAlias = dict[str, WorkloadExecutionState]
    ExecutionsStatesOfWorkload: TypeAlias = dict[str, ExecutionsStatesForId]
    WorkloadStatesMap: TypeAlias = dict[str, ExecutionsStatesOfWorkload]

    def __init__(self) -> None:
        """
        Initializes a WorkloadStateCollection instance.
        """
        self._workload_states: list[WorkloadState] = []

    def add_workload_state(self, state: WorkloadState) -> None:
        """
        Adds a workload state to the collection.

        Args:
            state (WorkloadState): The workload state to add.
        """
        self._workload_states.append(state)

    def get_as_dict(self) -> WorkloadStatesMap:
        """
        Returns the workload states as a list.

        Returns:
            list[WorkloadState]: A list of workload states.
        """
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
        """
        Returns the workload states as a list.

        Returns:
            list[WorkloadState]: A list of workload states.
        """
        return self._workload_states

    def _from_proto(self, state: _ank_base.WorkloadStatesMap) -> None:
        """
        Populates the collection from a proto message.

        Args:
            state (_ank_base.WorkloadStatesMap): The proto message to interpret.
        """
        for agent_name in state.agentStateMap:
            for workload_name in state.agentStateMap[agent_name].\
                    wlNameStateMap:
                for workload_id in state.agentStateMap[agent_name].\
                        wlNameStateMap[workload_name].idStateMap:
                    self.add_workload_state(WorkloadState(
                        agent_name,
                        workload_name,
                        workload_id,
                        state.agentStateMap[agent_name].wlNameStateMap[workload_name].\
                            idStateMap[workload_id]
                    ))
