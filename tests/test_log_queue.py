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
This module contains unit tests for the LogQueue class in the ankaios_sdk.
"""

from ankaios_sdk import (
    LogQueue,
    WorkloadInstanceName,
    LogEntry,
    LogsRequest,
    LogsCancelRequest,
)
from tests.response.test_log_response import generate_test_log_entry


def test_log_queue_requests():
    """
    Test the log queue requests generation.
    """
    workload_name = WorkloadInstanceName(
        workload_name="nginx", agent_name="agent_A", workload_id="1234"
    )

    log_queue = LogQueue(LogsRequest(workload_names=[workload_name]))
    assert log_queue is not None

    request = log_queue._get_request()
    request_id = request.get_id()
    assert isinstance(request, LogsRequest)

    cancel_request = log_queue._get_cancel_request()
    assert isinstance(cancel_request, LogsCancelRequest)
    assert cancel_request.get_id() == request_id


def test_log_queue():
    """
    Test the queue functionality.
    """
    workload_name = WorkloadInstanceName(
        workload_name="nginx", agent_name="agent_A", workload_id="1234"
    )
    log_queue = LogQueue([workload_name])

    log_entry = LogEntry.from_entries(generate_test_log_entry())
    log_queue.put(log_entry)
    assert log_queue.empty() is False
    entry = log_queue.get()
    assert entry == log_entry
