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

from ankaios_sdk import WorkloadStateEnum


def test_get():
    """
    Test the get method of the WorkloadStateEnum class,
    ensuring it correctly retrieves the enumeration member
    and its string representation.
    """
    workload_state = WorkloadStateEnum._get("agentDisconnected")
    assert workload_state == WorkloadStateEnum.AGENT_DISCONNECTED
    workload_state = WorkloadStateEnum._get("pending")
    assert workload_state == WorkloadStateEnum.PENDING
    workload_state = WorkloadStateEnum._get("notScheduled")
    assert workload_state == WorkloadStateEnum.NOT_SCHEDULED
    assert str(workload_state) == "NOT_SCHEDULED"
