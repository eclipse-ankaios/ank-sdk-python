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
This module contains unit tests for the Request class in the ankaios_sdk.
"""

import pytest
from ankaios_sdk import Request, GetStateRequest, \
    UpdateStateRequest, CompleteState
from tests.workload.test_workload import generate_test_workload


def generate_test_request(request_type: str = "update_state") -> Request:
    """
    Helper function to generate a Request instance with some default values.

    Returns:
        Request: A Request instance.
    """
    with pytest.raises(
            TypeError, match="Request cannot be instantiated directly."
            ):
        _ = Request()
    if request_type == "update_state":
        complete_state = CompleteState(workloads=[generate_test_workload()])
        request = UpdateStateRequest(complete_state)
        return request
    return GetStateRequest()


def test_proto():
    """
    Test the conversion to proto message.
    """
    request = UpdateStateRequest(CompleteState())
    assert request._to_proto().requestId == request.get_id()

    request = GetStateRequest()
    assert request._to_proto().requestId == request.get_id()
