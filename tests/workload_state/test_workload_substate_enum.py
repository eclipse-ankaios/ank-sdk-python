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
This module contains unit tests for the WorkloadSubStateEnum
class in the ankaios_sdk.
"""

import pytest
from ankaios_sdk import WorkloadSubStateEnum, WorkloadStateEnum
from ankaios_sdk._protos import _ank_base


def test_get():
    """
    Test the get method of the WorkloadSubStateEnum class,
    ensuring it correctly retrieves the enumeration member
    based on the state and field.
    """
    data = [
        (WorkloadStateEnum.AGENT_DISCONNECTED, _ank_base.AGENT_DISCONNECTED,
         WorkloadSubStateEnum.AGENT_DISCONNECTED),
        (WorkloadStateEnum.PENDING, _ank_base.PENDING_INITIAL,
         WorkloadSubStateEnum.PENDING_INITIAL),
        (WorkloadStateEnum.PENDING, _ank_base.PENDING_WAITING_TO_START,
         WorkloadSubStateEnum.PENDING_WAITING_TO_START),
        (WorkloadStateEnum.PENDING, _ank_base.PENDING_STARTING,
         WorkloadSubStateEnum.PENDING_STARTING),
        (WorkloadStateEnum.PENDING, _ank_base.PENDING_STARTING_FAILED,
         WorkloadSubStateEnum.PENDING_STARTING_FAILED),
        (WorkloadStateEnum.RUNNING, _ank_base.RUNNING_OK,
         WorkloadSubStateEnum.RUNNING_OK),
        (WorkloadStateEnum.STOPPING, _ank_base.STOPPING,
         WorkloadSubStateEnum.STOPPING),
        (WorkloadStateEnum.STOPPING, _ank_base.STOPPING_WAITING_TO_STOP,
         WorkloadSubStateEnum.STOPPING_WAITING_TO_STOP),
        (WorkloadStateEnum.STOPPING, _ank_base.STOPPING_REQUESTED_AT_RUNTIME,
         WorkloadSubStateEnum.STOPPING_REQUESTED_AT_RUNTIME),
        (WorkloadStateEnum.STOPPING, _ank_base.STOPPING_DELETE_FAILED,
         WorkloadSubStateEnum.STOPPING_DELETE_FAILED),
        (WorkloadStateEnum.SUCCEEDED, _ank_base.SUCCEEDED_OK,
         WorkloadSubStateEnum.SUCCEEDED_OK),
        (WorkloadStateEnum.FAILED, _ank_base.FAILED_EXEC_FAILED,
         WorkloadSubStateEnum.FAILED_EXEC_FAILED),
        (WorkloadStateEnum.FAILED, _ank_base.FAILED_UNKNOWN,
         WorkloadSubStateEnum.FAILED_UNKNOWN),
        (WorkloadStateEnum.FAILED, _ank_base.FAILED_LOST,
         WorkloadSubStateEnum.FAILED_LOST),
        (WorkloadStateEnum.NOT_SCHEDULED, _ank_base.NOT_SCHEDULED,
         WorkloadSubStateEnum.NOT_SCHEDULED),
        (WorkloadStateEnum.REMOVED, _ank_base.REMOVED,
         WorkloadSubStateEnum.REMOVED)
    ]
    for state, field, expected in data:
        assert WorkloadSubStateEnum._get(state, field) == expected


def test_get_error():
    """
    Test the get method of the WorkloadSubStateEnum class,
    ensuring it raises a ValueError for an invalid state and field combination.
    """
    with pytest.raises(ValueError):
        WorkloadSubStateEnum._get(WorkloadStateEnum.AGENT_DISCONNECTED,
                                  _ank_base.PENDING_WAITING_TO_START)


def test_sub_state2ank_base():
    """
    Test the conversion from WorkloadSubStateEnum to _ank_base.
    """
    substate = WorkloadSubStateEnum.FAILED_UNKNOWN
    assert substate._sub_state2ank_base() == _ank_base.FAILED_UNKNOWN
    assert str(substate) == "FAILED_UNKNOWN"
