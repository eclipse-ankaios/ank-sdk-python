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
This module defines various classes and enumerations related to the state
of workloads. It provides functionality to interpret and manage the states
and sub-states of workloads, including converting between different
representations and handling collections of workload states.

Classes
-------

- :class:`WorkloadExecutionState`:
    Represents the execution state and sub-state of a workload.
- :class:`WorkloadInstanceName`:
    Represents the name of a workload instance.
- :class:`WorkloadState`:
    Represents the state of a workload (execution state and name).
- :class:`WorkloadStateCollection`:
    A collection of workload states.

Enums
-----

- :class:`WorkloadStateEnum`:
    Enumeration for different states of a workload.
- :class:`WorkloadSubStateEnum`:
    Enumeration for different sub-states of a workload.

Usage
-----

- Get all workload states:
    .. code-block:: python

        workload_state_collection = WorkloadStateCollection()
        list_of_workload_states = workload_state_collection.get_as_list()
        dict_of_workload_states = workload_state_collection.get_as_dict()

- Unpack a workload state:
    .. code-block:: python

        workload_state = WorkloadState()
        agent_name = workload_state.workload_instance_name.agent_name
        workload_name = workload_state.workload_instance_name.workload_name
        state = workload_state.execution_state.state
        substate = workload_state.execution_state.substate
        info = workload_state.execution_state.additional_info

- Get the workload instance name as a dictionary:
    .. code-block:: python

        workload_instance_name = WorkloadInstanceName()
        instance_name_dict = workload_instance_name.to_dict()
        json_instance_name = json.dumps(instance_name_dict)
"""

__all__ = [
    "WorkloadStateCollection",
    "WorkloadState",
    "WorkloadInstanceName",
    "WorkloadExecutionState",
    "WorkloadStateEnum",
    "WorkloadSubStateEnum",
]

from typing import Optional, Union
from enum import Enum
from .._protos import _ank_base


class WorkloadStateEnum(Enum):
    """Enumeration for different states of a workload."""

    AGENT_DISCONNECTED: int = 0
    "(int): The agent is disconnected."
    PENDING: int = 1
    "(int): The workload is pending."
    RUNNING: int = 2
    "(int): The workload is running."
    STOPPING: int = 3
    "(int): The workload is stopping."
    SUCCEEDED: int = 4
    "(int): The workload has succeeded."
    FAILED: int = 5
    "(int): The workload has failed."
    NOT_SCHEDULED: int = 6
    "(int): The workload is not scheduled."
    REMOVED: int = 7
    "(int): The workload has been removed."

    def __str__(self) -> str:
        """
        Return the name of the enumeration member.

        :returns: The name of the enumeration member.
        :rtype: str
        """
        return self.name

    @staticmethod
    def _get(field: str) -> "WorkloadStateEnum":
        """
        Get the enumeration member corresponding to the given field name.

        :param field: The field name to look up.
        :type field: str

        :returns: The enumeration member corresponding
            to the field name.
        :rtype: WorkloadStateEnum

        :raises KeyError: If the field name does not correspond to
            any enumeration member.
        """
        # camelCase to SNAKE_CASE
        if field == "agentDisconnected":
            return WorkloadStateEnum.AGENT_DISCONNECTED
        if field == "notScheduled":
            return WorkloadStateEnum.NOT_SCHEDULED
        return WorkloadStateEnum[field.upper()]


class WorkloadSubStateEnum(Enum):
    """Enumeration for different sub-states of a workload."""

    AGENT_DISCONNECTED: int = 0
    "(int): The agent is disconnected."
    PENDING_INITIAL: int = 1
    "(int): The workload is in the initial pending state."
    PENDING_WAITING_TO_START: int = 2
    "(int): The workload is waiting to start."
    PENDING_STARTING: int = 3
    "(int): The workload is starting."
    PENDING_STARTING_FAILED: int = 4
    "(int): The workload failed to start."
    RUNNING_OK: int = 5
    "(int): The workload is running successfully."
    STOPPING: int = 6
    "(int): The workload is stopping."
    STOPPING_WAITING_TO_STOP: int = 7
    "(int): The workload is waiting to stop."
    STOPPING_REQUESTED_AT_RUNTIME: int = 8
    "(int): The workload stop was requested at runtime."
    STOPPING_DELETE_FAILED: int = 9
    "(int): The workload stop failed to delete."
    SUCCEEDED_OK: int = 10
    "(int): The workload succeeded successfully."
    FAILED_EXEC_FAILED: int = 11
    "(int): The workload failed due to execution failure."
    FAILED_UNKNOWN: int = 12
    "(int): The workload failed due to an unknown reason."
    FAILED_LOST: int = 13
    "(int): The workload failed because it was lost."
    NOT_SCHEDULED: int = 14
    "(int): The workload is not scheduled."
    REMOVED: int = 15
    "(int): The workload has been removed."

    def __str__(self) -> str:
        """
        Return the name of the enumeration member.

        :returns: The name of the enumeration member.
        :rtype: str
        """
        return self.name

    @staticmethod
    def _get(
        state: WorkloadStateEnum, field: _ank_base
    ) -> "WorkloadSubStateEnum":
        """
        Get the enumeration member corresponding to the given state and field.

        :param state: The state of the workload.
        :type state: WorkloadStateEnum
        :param field: The field to look up.
        :type field: _ank_base

        :returns: The enumeration member corresponding
            to the state and field.
        :rtype: WorkloadSubStateEnum

        :raises ValueError: If the field does not correspond to
            any enumeration member.
        """
        # SNAKE_CASE to CamelCase
        state_name = "".join([elem.title() for elem in state.name.split("_")])
        if field not in getattr(_ank_base, state_name).values():
            raise ValueError(
                "No corresponding WorkloadSubStateEnum "
                + f"value for enum: {field}"
            )
        return WorkloadSubStateEnum[getattr(_ank_base, state_name).Name(field)]

    def _sub_state2ank_base(self) -> _ank_base:
        """
        Convert the WorkloadSubStateEnum member to the corresponding
        _ank_base value.

        :returns: The corresponding _ank_base value.
        :rtype: _ank_base

        :raises ValueError: If there is no corresponding _ank_base
            value for the enumeration member.
        """
        try:
            return getattr(_ank_base, self.name)
        except AttributeError as e:  # pragma: no cover
            raise ValueError(
                "No corresponding ank_base value " + f"for enum: {self.name}"
            ) from e


# pylint: disable=too-few-public-methods
class WorkloadExecutionState:
    """
    Represents the execution state of a workload.

    :var WorkloadStateEnum state:
        The state of the workload.
    :var WorkloadSubStateEnum substate:
        The sub-state of the workload.
    :var str additional_info:
        Additional information about the workload state.
    """

    def __init__(self, state: _ank_base.ExecutionState) -> None:
        """
        Initializes a WorkloadExecutionState instance.

        :param state: The execution state to interpret.
        :type state: _ank_base.ExecutionState
        """
        self.state: WorkloadStateEnum = None
        self.substate: WorkloadSubStateEnum = None
        self.additional_info: str = None

        self._interpret_state(state)

    def __str__(self) -> str:
        """
        Returns the string representation of the workload execution state.

        :returns: The string representation of the workload execution state.
        :rtype: str
        """
        return (
            f"{self.state.name} ({self.substate.name}):"
            + f"{self.additional_info}"
        )

    def _interpret_state(self, exec_state: _ank_base.ExecutionState) -> None:
        """
        Interprets the execution state and sets the state, substate,
        and info attributes.

        :param exec_state: The execution
            state to interpret.
        :type exec_state: _ank_base.ExecutionState

        :raises ValueError: If the execution state is invalid.
        """
        self.additional_info = str(exec_state.additionalInfo)

        field = exec_state.WhichOneof("ExecutionStateEnum")
        if field is None:
            raise ValueError("Invalid state for workload.")

        self.state = WorkloadStateEnum._get(field)
        self.substate = WorkloadSubStateEnum._get(
            self.state, getattr(exec_state, field)
        )

    def to_dict(self) -> dict:
        """
        Returns the execution state as a dictionary.

        :returns: The execution state as a dictionary.
        :rtype: dict
        """
        return {
            "state": str(self.state),
            "substate": str(self.substate),
            "additional_info": self.additional_info,
        }


# pylint: disable=too-few-public-methods
class WorkloadInstanceName:
    """
    Represents the name of a workload instance.

    :var str agent_name:
        The name of the agent.
    :var str workload_name:
        The name of the workload.
    :var str workload_id:
        The ID of the workload.
    """

    def __init__(
        self, agent_name: str, workload_name: str, workload_id: str
    ) -> None:
        """
        Initializes a WorkloadInstanceName instance.

        :param agent_name: The name of the agent.
        :type agent_name: str
        :param workload_name: The name of the workload.
        :type workload_name: str
        :param workload_id: The ID of the workload.
        :type workload_id: str
        """
        self.agent_name = agent_name
        self.workload_name = workload_name
        self.workload_id = workload_id

    def __eq__(self, other: "WorkloadInstanceName") -> bool:
        """
        Checks if two workload instance names are equal.

        :param other: The instance name to compare with.
        :type other: WorkloadInstanceName

        :returns: True if the workload instance names are equal,
            False otherwise.
        :rtype: bool
        """
        if isinstance(other, WorkloadInstanceName):
            return (
                self.agent_name == other.agent_name
                and self.workload_name == other.workload_name
                and self.workload_id == other.workload_id
            )
        return NotImplemented

    def __str__(self) -> str:
        """
        Returns the string representation of the workload instance name.

        :returns: The string representation of the workload instance name.
        :rtype: str
        """
        return f"{self.workload_name}.{self.workload_id}.{self.agent_name}"

    def to_dict(self) -> dict:
        """
        Returns the workload instance name as a dictionary.

        :returns: The workload instance name as a dictionary.
        :rtype: dict
        """
        return {
            "agent_name": self.agent_name,
            "workload_name": self.workload_name,
            "workload_id": self.workload_id,
        }

    def get_filter_mask(self) -> str:
        """
        Returns the filter mask for the workload instance name.

        :returns: The filter mask for the workload instance name.
        :rtype: str
        """
        return (
            f"workloadStates.{self.agent_name}."
            + f"{self.workload_name}.{self.workload_id}"
        )

    def _to_proto(self) -> _ank_base.WorkloadInstanceName:
        """
        Converts the workload instance name to a proto message.

        :returns: The protobuf message
            representing the workload instance name.
        :rtype: _ank_base.WorkloadInstanceName
        """
        return _ank_base.WorkloadInstanceName(
            agentName=self.agent_name,
            workloadName=self.workload_name,
            id=self.workload_id,
        )


# pylint: disable=too-few-public-methods
class WorkloadState:
    """
    Represents the state of a workload.

    :var WorkloadExecutionState execution_state:
        The execution state of the workload.
    :var WorkloadInstanceName workload_instance_name:
        The name of the workload instance.
    """

    def __init__(
        self,
        agent_name: str,
        workload_name: str,
        workload_id: str,
        state: Union[WorkloadExecutionState, _ank_base.ExecutionState],
    ) -> None:
        """
        Initializes a WorkloadState instance.

        :param agent_name: The name of the agent.
        :type agent_name: str
        :param workload_name: The name of the workload.
        :type workload_name: str
        :param workload_id: The ID of the workload.
        :type workload_id: str
        :param state: The execution state.
        :type state: WorkloadExecutionState
        """
        if isinstance(state, _ank_base.ExecutionState):
            self.execution_state = WorkloadExecutionState(state)
        else:
            self.execution_state = state
        self.workload_instance_name = WorkloadInstanceName(
            agent_name, workload_name, workload_id
        )

    def __str__(self) -> str:
        """
        Returns the string representation of the workload state.

        :returns: The string representation of the workload state.
        :rtype: str
        """
        return f"{self.workload_instance_name}: {self.execution_state}"


class WorkloadStateCollection:
    """
    A class that represents a collection of workload states and provides
    methods to manipulate them.
    """

    ExecutionsStatesForId = dict[str, WorkloadExecutionState]
    ExecutionsStatesOfWorkload = dict[str, ExecutionsStatesForId]
    WorkloadStatesMap = dict[str, ExecutionsStatesOfWorkload]

    def __init__(self) -> None:
        """
        Initializes a WorkloadStateCollection instance.
        """
        self._workload_states: dict = {}

    def add_workload_state(self, state: WorkloadState) -> None:
        """
        Adds a workload state to the collection.

        :param state: The workload state to add.
        :type state: WorkloadState
        """
        agent_name = state.workload_instance_name.agent_name
        workload_name = state.workload_instance_name.workload_name
        workload_id = state.workload_instance_name.workload_id
        if agent_name not in self._workload_states:
            self._workload_states[agent_name] = (
                self.ExecutionsStatesOfWorkload()
            )
        if workload_name not in self._workload_states[agent_name]:
            self._workload_states[agent_name][
                workload_name
            ] = self.ExecutionsStatesForId()
        self._workload_states[agent_name][workload_name][
            workload_id
        ] = state.execution_state

    def get_as_dict(self) -> WorkloadStatesMap:
        """
        Returns the workload states as a dict.

        :returns: A dict of workload states.
        :rtype: WorkloadStatesMap
        """
        return self._workload_states

    def get_as_list(self) -> list[WorkloadState]:
        """
        Returns the workload states as a list.

        :returns: A list of workload states.
        :rtype: list[WorkloadState]
        """
        workload_states = []
        for agent_name, workloads in sorted(self._workload_states.items()):
            for workload_name, workload_ids in sorted(workloads.items()):
                for workload_id, exec_state in sorted(workload_ids.items()):
                    workload_states.append(
                        WorkloadState(
                            agent_name, workload_name, workload_id, exec_state
                        )
                    )
        return workload_states

    def get_for_instance_name(
        self, instance_name: WorkloadInstanceName
    ) -> Optional[WorkloadState]:
        """
        Returns the workload state for the given workload instance name.

        :param instance_name: The workload instance name
            to look up.
        :type instance_name: WorkloadInstanceName

        :returns: The workload state for the given instance name,
            or None if no workload state was found.
        :rtype: Optional[WorkloadState]
        """
        try:
            return WorkloadState(
                instance_name.agent_name,
                instance_name.workload_name,
                instance_name.workload_id,
                self._workload_states[instance_name.agent_name][
                    instance_name.workload_name
                ][instance_name.workload_id],
            )
        except KeyError:
            return None

    def _from_proto(self, state: _ank_base.WorkloadStatesMap) -> None:
        """
        Populates the collection from a proto message.

        :param state: The proto message
            to interpret.
        :type state: _ank_base.WorkloadStatesMap
        """
        for agent_name in state.agentStateMap:
            for workload_name in state.agentStateMap[
                agent_name
            ].wlNameStateMap:
                for workload_id in (
                    state.agentStateMap[agent_name]
                    .wlNameStateMap[workload_name]
                    .idStateMap
                ):
                    self.add_workload_state(
                        WorkloadState(
                            agent_name,
                            workload_name,
                            workload_id,
                            state.agentStateMap[agent_name]
                            .wlNameStateMap[workload_name]
                            .idStateMap[workload_id],
                        )
                    )
