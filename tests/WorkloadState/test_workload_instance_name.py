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
This module contains unit tests for the WorkloadInstanceName
class in the ankaios_sdk.
"""

from ankaios_sdk import WorkloadInstanceName


def test_creation():
    """
    Test the creation of a WorkloadInstanceName instance,
    ensuring it is correctly initialized with the provided attributes.
    """
    workload_instance_name = WorkloadInstanceName(
        agent_name="agent_Test",
        workload_name="workload_Test",
        workload_id="1234"
    )
    assert workload_instance_name is not None
    assert workload_instance_name.agent_name == "agent_Test"
    assert workload_instance_name.workload_name == "workload_Test"
    assert workload_instance_name.workload_id == "1234"
    assert str(workload_instance_name) == "agent_Test.workload_Test.1234"
