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
This module contains unit tests for the WorkloadStateCollection
class in the ankaios_sdk.
"""

from ankaios_sdk import WorkloadStateCollection, WorkloadState, \
    WorkloadExecutionState, WorkloadInstanceName, WorkloadStateEnum, \
    WorkloadSubStateEnum
from ankaios_sdk._protos import _ank_base


def test_get():
    """
    Test the basic functionality of the WorkloadStateCollection
    class, including adding a workload state and retrieving it
    as a list and dictionary.
    """
    workload_state_collection = WorkloadStateCollection()
    assert workload_state_collection is not None
    assert len(workload_state_collection._workload_states) == 0

    execution_state = _ank_base.ExecutionState(
        additionalInfo="Dummy information",
        pending=_ank_base.PENDING_WAITING_TO_START
    )

    workload_state = WorkloadState(
        agent_name="agent_Test",
        workload_name="workload_Test",
        workload_id="1234",
        state=execution_state
    )

    # Test get_as_list
    workload_state_collection.add_workload_state(workload_state)
    assert len(workload_state_collection._workload_states) == 1
    assert workload_state_collection.get_as_list() == [workload_state]

    # Test get_as_dict
    workload_states_dict = workload_state_collection.get_as_dict()
    assert len(workload_states_dict) == 1
    assert "agent_Test" in workload_states_dict.keys()
    assert len(workload_states_dict["agent_Test"]) == 1
    assert "workload_Test" in workload_states_dict["agent_Test"].keys()
    assert len(workload_states_dict["agent_Test"]["workload_Test"]) == 1
    assert "1234" in workload_states_dict["agent_Test"]["workload_Test"].keys()
    assert isinstance(
        workload_states_dict["agent_Test"]["workload_Test"]["1234"],
        WorkloadExecutionState
    )

    # Test get_for_instance_name
    workload_instance_name = WorkloadInstanceName(
        agent_name="agent_Test",
        workload_name="workload_Test",
        workload_id="1234"
    )
    assert workload_state_collection.get_for_instance_name(
        workload_instance_name
    ) == workload_state
    workload_instance_name.workload_id = "5678"
    assert workload_state_collection.get_for_instance_name(
        workload_instance_name
    ) is None


def test_from_proto():
    """
    Test the _from_proto method of the WorkloadStateCollection class,
    ensuring it correctly populates the collection from a proto message.
    """
    ank_workload_state = _ank_base.WorkloadStatesMap(
        agentStateMap={"agent_Test": _ank_base.ExecutionsStatesOfWorkload(
            wlNameStateMap={"workload_Test": _ank_base.ExecutionsStatesForId(
                idStateMap={"1234": _ank_base.ExecutionState(
                    additionalInfo="Dummy information",
                    pending=_ank_base.PENDING_WAITING_TO_START
                )}
            )}
        )}
    )

    workload_state_collection = WorkloadStateCollection()
    workload_state_collection._from_proto(ank_workload_state)
    assert len(workload_state_collection._workload_states) == 1
    workload_states = workload_state_collection.get_as_list()
    assert len(workload_states) == 1

    assert workload_states[0].workload_instance_name.agent_name == \
        "agent_Test"
    assert workload_states[0].workload_instance_name.workload_name == \
        "workload_Test"
    assert workload_states[0].workload_instance_name.workload_id == \
        "1234"
    assert workload_states[0].execution_state.state == \
        WorkloadStateEnum.PENDING
    assert workload_states[0].execution_state.substate == \
        WorkloadSubStateEnum.PENDING_WAITING_TO_START
    assert workload_states[0].execution_state.info == \
        "Dummy information"
