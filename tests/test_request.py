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
This module contains unit tests for the Request class in the AnkaiosSDK.
"""

import pytest
from AnkaiosSDK import Request, CompleteState
from tests.Workload.test_workload import generate_test_workload


def generate_test_request(request_type: str = "update_state") -> Request:
    """
    Helper function to generate a Request instance with some default values.

    Returns:
        Request: A Request instance.
    """
    if request_type == "update_state":
        request = Request("update_state")
        complete_state = CompleteState()
        complete_state.set_workload(generate_test_workload())
        request.set_complete_state(complete_state)
        return request
    return Request("get_state")


def test_general_functionality():
    """
    Test general functionality of the Request class.
    """
    with pytest.raises(ValueError, match="Invalid request type."):
        Request("invalid")

    request = Request("update_state")
    assert request.get_id() is not None
    assert str(request) == f"requestId: \"{request.get_id()}\"\n"


def test_update_state():
    """
    Test the update state request type.
    """
    request = Request("update_state")
    complete_state = CompleteState()
    request.set_complete_state(complete_state)
    assert request._request.updateStateRequest.newState == complete_state._to_proto()

    request.add_mask("test_mask")
    assert request._request.updateStateRequest.updateMask == ["test_mask"]

    with pytest.raises(ValueError,
                       match="Complete state can only be set for an update state request."):
        Request("get_state").set_complete_state(CompleteState())

def test_get_state():
    """
    Test the get state request type.
    """
    request = Request("get_state")
    request.add_mask("test_mask")
    assert request._request.completeStateRequest.fieldMask == ["test_mask"]


def test_proto():
    """
    Test the conversion to proto message.
    """
    request = Request("update_state")
    assert request._to_proto().requestId == request.get_id()

    request = Request("get_state")
    assert request._to_proto().requestId == request.get_id()
