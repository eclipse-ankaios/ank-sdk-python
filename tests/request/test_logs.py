# Copyright (c) 2025 Elektrobit Automotive GmbH
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
This module contains unit tests for the LogsRequest and LogsCancelRequest
classes in the ankaios_sdk.
"""

from datetime import datetime
import pytest
from ankaios_sdk import LogsRequest, LogsCancelRequest, WorkloadInstanceName


def test_logs_request():
    """
    Test the logs request type.
    """
    # Test raises error if empty
    with pytest.raises(
            ValueError, match="At least one workload name must be provided."
            ):
        _ = LogsRequest(workload_names=[])

    # Test success with datetime
    workload_name = WorkloadInstanceName(
        workload_name="nginx",
        agent_name="agent_A",
        workload_id="1234"
    )
    request = LogsRequest(
        workload_names=[workload_name],
        follow=True,
        tail=10,
        since=datetime(2023, 1, 1, 12, 0, 0),
        until=datetime(2023, 1, 1, 12, 5, 0),
    )
    assert request is not None
    assert request._request.HasField("logsRequest")
    assert request._request.logsRequest.\
        workloadNames[0].workloadName == "nginx"
    assert request._request.logsRequest.workloadNames[0].agentName == "agent_A"
    assert request._request.logsRequest.workloadNames[0].id == "1234"
    assert request._request.logsRequest.follow is True
    assert request._request.logsRequest.tail == 10
    assert request._request.logsRequest.since == "2023-01-01T12:00:00"
    assert request._request.logsRequest.until == "2023-01-01T12:05:00"

    # Test success with string
    request = LogsRequest(
        workload_names=[workload_name],
        follow=True,
        tail=10,
        since="2023-01-01T12:00:00",
        until="2023-01-01T12:05:00",
    )
    assert request is not None


def test_cancel_request():
    """
    Test the logs cancel request type.
    """
    request = LogsCancelRequest(
        request_id="1234"
    )
    assert request is not None
    assert request._request.HasField("logsCancelRequest")
