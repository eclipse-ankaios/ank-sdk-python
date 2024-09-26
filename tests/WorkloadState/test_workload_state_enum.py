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
    field = "agentDisconnected"
    workload_state = WorkloadStateEnum._get(field)
    assert workload_state == WorkloadStateEnum.AgentDisconnected
    assert str(workload_state) == "AgentDisconnected"
