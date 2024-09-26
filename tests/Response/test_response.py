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
This module contains unit tests for the Response class in the ankaios_sdk.
"""

import pytest
from google.protobuf.internal.encoder import _VarintBytes
from ankaios_sdk import Response, CompleteState
from ankaios_sdk._protos import _ank_base, _control_api


MESSAGE_BUFFER_ERROR = _control_api.FromAnkaios(
    response=_ank_base.Response(
        requestId="1234",
        error=_ank_base.Error(
            message="Test error message",
        )
    )
).SerializeToString()

MESSAGE_BUFFER_COMPLETE_STATE = _control_api.FromAnkaios(
    response=_ank_base.Response(
        requestId="1234",
        completeState=_ank_base.CompleteState(
            desiredState=_ank_base.State(
                apiVersion="v0.1",
                workloads=_ank_base.WorkloadMap(
                    workloads={},
                )
            )
        )
    )
).SerializeToString()

MESSAGE_UPDATE_SUCCESS = _control_api.FromAnkaios(
    response=_ank_base.Response(
        requestId="1234",
        UpdateStateSuccess=_ank_base.UpdateStateSuccess(
            addedWorkloads=["new_nginx"],
            deletedWorkloads=["old_nginx"],
        )
    )
)
MESSAGE_BUFFER_UPDATE_SUCCESS = MESSAGE_UPDATE_SUCCESS.SerializeToString()
MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH = _VarintBytes(
    MESSAGE_UPDATE_SUCCESS.ByteSize()
)

MESSAGE_BUFFER_INVALID_RESPONSE = _control_api.FromAnkaios(
    response=_ank_base.Response(
        requestId="1234",
    )
).SerializeToString()


def test_initialisation():
    """
    Test the initialisation of a Response object.
    This step tests the parsing of the response buffer into a proto object
    and the conversion to a Response object.
    """
    # Test error message
    response = Response(MESSAGE_BUFFER_ERROR)
    assert response.content_type == "error"
    assert response.content == "Test error message"

    # Test CompleteState message
    response = Response(MESSAGE_BUFFER_COMPLETE_STATE)
    assert response.content_type == "complete_state"
    assert isinstance(response.content, CompleteState)

    # Test UpdateStateSuccess message
    response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
    assert response.content_type == "update_state_success"
    assert response.content == {
        "added_workloads": ["new_nginx"],
        "deleted_workloads": ["old_nginx"],
    }

    # Test invalid buffer
    with pytest.raises(ValueError, match="Invalid response, parsing error"):
        _ = Response(b"invalid_buffer{")

    # Test invalid response type
    with pytest.raises(ValueError, match="Invalid response type"):
        response = Response(MESSAGE_BUFFER_INVALID_RESPONSE)


def test_getters():
    """
    Test the getter methods of the Response class.
    """
    response = Response(MESSAGE_BUFFER_ERROR)
    assert response.get_request_id() == "1234"
    assert response.get_content() == ("error", "Test error message")


def test_check_request_id():
    """
    Test the check_request_id method of the Response class.
    """
    response = Response(MESSAGE_BUFFER_ERROR)
    assert response.check_request_id("1234")
    assert not response.check_request_id("4321")
