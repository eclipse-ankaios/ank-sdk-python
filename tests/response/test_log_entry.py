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
This module contains unit tests for the LogEntry class in the ankaios_sdk.

Helper Functions:
    generate_test_log_entry: Helper function to generate a LogEntry proto
        message for testing.
"""

from ankaios_sdk import LogEntry
from ankaios_sdk._protos import _ank_base


def generate_test_log_entry(name="nginx") -> _ank_base.LogEntry:
    """
    Helper function to generate a LogEntry proto.

    Returns:
        _ank_base.LogEntry: A LogEntry proto.
    """
    return _ank_base.LogEntry(
        workloadName=_ank_base.WorkloadInstanceName(
            workloadName=name,
            agentName="agent_A",
            id="1234"
        ),
        message="Test log message"
    )


def test_log_entry():
    """
    Test the LogEntry class.
    """
    log_entry = LogEntry(
        generate_test_log_entry()
    )
    assert log_entry is not None
    assert str(log_entry) == "Workload Instance Name: nginx.1234.agent_A, Message: Test log message"
    assert log_entry.to_dict() == {
        "workload_instance_name": {
            "agent_name": "agent_A",
            "workload_name": "nginx",
            "workload_id": "1234"
        },
        "message": "Test log message"
    }