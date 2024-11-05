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
This module contains unit tests for the WorkloadExecutionState
class in the ankaios_sdk.
"""

import pytest
from ankaios_sdk import WorkloadExecutionState, WorkloadStateEnum, \
    WorkloadSubStateEnum
from ankaios_sdk._protos import _ank_base


def test_interpret_state():
    """
    Test the interpretation of a valid execution state in the
    WorkloadExecutionState class.
    """
    workload_state = WorkloadExecutionState(
        _ank_base.ExecutionState(
            additionalInfo="Dummy information",
            pending=_ank_base.PENDING_WAITING_TO_START
        )
    )

    assert workload_state.state == WorkloadStateEnum.PENDING
    assert workload_state.substate == \
        WorkloadSubStateEnum.PENDING_WAITING_TO_START
    assert workload_state.additional_info == "Dummy information"


def test_interpret_state_error():
    """
    Test the handling of an invalid execution state in the
    WorkloadExecutionState class, ensuring it raises a ValueError.
    """
    with pytest.raises(ValueError, match="Invalid state for workload."):
        WorkloadExecutionState(
            _ank_base.ExecutionState(
                additionalInfo="No state present"
            )
        )
