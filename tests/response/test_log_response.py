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
This module contains unit tests for the LogResponse class in the ankaios_sdk.

Helper Functions:
    generate_test_log_entry: Helper function to generate a LogEntry proto
        message for testing.
    generate_test_logs_stop_reponse: Helper function to generate a
        LogsStopResponse proto message for testing.
"""

from ankaios_sdk import LogResponse, LogsType
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


def generate_test_logs_stop_reponse(name="nginx") -> _ank_base.LogsStopResponse:
    """
    Helper function to generate a LogsStopResponse proto.

    Returns:
        _ank_base.LogsStopResponse: A LogStoLogsStopResponsepResponse proto.
    """
    return _ank_base.LogsStopResponse(
        workloadName=_ank_base.WorkloadInstanceName(
            workloadName=name,
            agentName="agent_A",
            id="1234"
        )
    )


def test_log_entries():
    """
    Test the Log entries Response class.
    """
    log_entry = LogResponse.from_entries(
        generate_test_log_entry()
    )
    assert log_entry is not None
    assert str(log_entry) == "Log from nginx.1234.agent_A: Test log message"
    assert log_entry.to_dict() == {
        "workload_instance_name": {
            "agent_name": "agent_A",
            "workload_name": "nginx",
            "workload_id": "1234"
        },
        "type": LogsType.LOGS_ENTRY,
        "message": "Test log message"
    }

def test_log_stop_response():
    """
    Test the Log stop response.
    """
    log_stop_response = LogResponse.from_stop_response(
        generate_test_logs_stop_reponse()
    )
    assert log_stop_response is not None
    assert str(log_stop_response) == "Stopped receiving logs from nginx.1234.agent_A."
    assert log_stop_response.to_dict() == {
        "workload_instance_name": {
            "agent_name": "agent_A",
            "workload_name": "nginx",
            "workload_id": "1234"
        },
        "type": LogsType.LOGS_STOP_RESPONSE,
        "message": ""
    }