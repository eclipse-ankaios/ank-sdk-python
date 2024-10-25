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
This module contains unit tests for the WorkloadState
class in the ankaios_sdk.
"""

from ankaios_sdk import WorkloadState, WorkloadStateEnum, WorkloadSubStateEnum
from ankaios_sdk._protos import _ank_base


def generate_test_workload_state():
    """
    Generate a test WorkloadState instance.
    """
    return WorkloadState(
        agent_name="agent_Test",
        workload_name="workload_Test",
        workload_id="1234",
        state=_ank_base.ExecutionState(
            additionalInfo="Dummy information",
            pending=_ank_base.PENDING_WAITING_TO_START
        )
    )


def test_creation():
    """
    Test the creation of a WorkloadState instance.
    """
    workload_state = generate_test_workload_state()
    assert workload_state is not None
    assert workload_state.execution_state is not None
    assert workload_state.execution_state.state == WorkloadStateEnum.PENDING
    assert workload_state.execution_state.substate == \
        WorkloadSubStateEnum.PENDING_WAITING_TO_START
    assert workload_state.execution_state.info == "Dummy information"
    assert workload_state.workload_instance_name is not None
    assert workload_state.workload_instance_name.agent_name == "agent_Test"
    assert workload_state.workload_instance_name.workload_name == \
        "workload_Test"
    assert workload_state.workload_instance_name.workload_id == "1234"
