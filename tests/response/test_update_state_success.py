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
This module contains unit tests for the UpdateStateSuccess
class in the ankaios_sdk.
"""

from ankaios_sdk import UpdateStateSuccess, WorkloadInstanceName


def test_functionality():
    """
    Test the methods of an UpdateStateSuccess instance.
    """
    update_state_success = UpdateStateSuccess()

    assert update_state_success is not None
    assert len(update_state_success.added_workloads) == 0
    assert len(update_state_success.deleted_workloads) == 0

    update_state_success.added_workloads.append(
        WorkloadInstanceName("agent_A", "new_nginx", "12345")
    )
    update_state_success.deleted_workloads.append(
        WorkloadInstanceName("agent_A", "old_nginx", "54321")
    )

    assert len(update_state_success.added_workloads) == 1
    assert len(update_state_success.deleted_workloads) == 1
    assert (
        str(update_state_success)
        == "Added workloads: ['new_nginx.12345.agent_A'], "
        "Deleted workloads: ['old_nginx.54321.agent_A']"
    )
    assert update_state_success.to_dict() == {
        "added_workloads": [
            {
                "agent_name": "agent_A",
                "workload_name": "new_nginx",
                "workload_id": "12345",
            }
        ],
        "deleted_workloads": [
            {
                "agent_name": "agent_A",
                "workload_name": "old_nginx",
                "workload_id": "54321",
            }
        ],
    }
