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

import pytest
from AnkaiosSDK import WorkloadStateEnum, WorkloadSubStateEnum
from AnkaiosSDK._protos import _ank_base


@pytest.mark.parametrize("state, field, expected", [
    (WorkloadStateEnum.AgentDisconnected, _ank_base.AGENT_DISCONNECTED, WorkloadSubStateEnum.AGENT_DISCONNECTED),
    (WorkloadStateEnum.Pending, _ank_base.PENDING_INITIAL, WorkloadSubStateEnum.PENDING_INITIAL),
    (WorkloadStateEnum.Pending, _ank_base.PENDING_WAITING_TO_START, WorkloadSubStateEnum.PENDING_WAITING_TO_START),
    (WorkloadStateEnum.Pending, _ank_base.PENDING_STARTING, WorkloadSubStateEnum.PENDING_STARTING),
    (WorkloadStateEnum.Pending, _ank_base.PENDING_STARTING_FAILED, WorkloadSubStateEnum.PENDING_STARTING_FAILED),
    (WorkloadStateEnum.Running, _ank_base.RUNNING_OK, WorkloadSubStateEnum.RUNNING_OK),
    (WorkloadStateEnum.Stopping, _ank_base.STOPPING, WorkloadSubStateEnum.STOPPING),
    (WorkloadStateEnum.Stopping, _ank_base.STOPPING_WAITING_TO_STOP, WorkloadSubStateEnum.STOPPING_WAITING_TO_STOP),
    (WorkloadStateEnum.Stopping, _ank_base.STOPPING_REQUESTED_AT_RUNTIME, WorkloadSubStateEnum.STOPPING_REQUESTED_AT_RUNTIME),
    (WorkloadStateEnum.Stopping, _ank_base.STOPPING_DELETE_FAILED, WorkloadSubStateEnum.STOPPING_DELETE_FAILED),
    (WorkloadStateEnum.Succeeded, _ank_base.SUCCEEDED_OK, WorkloadSubStateEnum.SUCCEEDED_OK),
    (WorkloadStateEnum.Failed, _ank_base.FAILED_EXEC_FAILED, WorkloadSubStateEnum.FAILED_EXEC_FAILED),
    (WorkloadStateEnum.Failed, _ank_base.FAILED_UNKNOWN, WorkloadSubStateEnum.FAILED_UNKNOWN),
    (WorkloadStateEnum.Failed, _ank_base.FAILED_LOST, WorkloadSubStateEnum.FAILED_LOST),
    (WorkloadStateEnum.NotScheduled, _ank_base.NOT_SCHEDULED, WorkloadSubStateEnum.NOT_SCHEDULED),
    (WorkloadStateEnum.Removed, _ank_base.REMOVED, WorkloadSubStateEnum.REMOVED)
])
def test_get(state: WorkloadStateEnum, field: _ank_base, expected: WorkloadSubStateEnum):
    assert WorkloadSubStateEnum._get(state, field) == expected


def test_get_error():
    with pytest.raises(ValueError):
        WorkloadSubStateEnum._get(WorkloadStateEnum.AgentDisconnected, _ank_base.PENDING_WAITING_TO_START)


def test_sub_state2ank_base():
    substate = WorkloadSubStateEnum.FAILED_UNKNOWN
    assert substate._sub_state2ank_base() == _ank_base.FAILED_UNKNOWN
    assert str(substate) == "FAILED_UNKNOWN"
