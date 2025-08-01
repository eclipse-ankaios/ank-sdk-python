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
This module contains unit tests for the UpdateStateRequest class in
the ankaios_sdk.
"""

from ankaios_sdk import UpdateStateRequest, CompleteState


def test_update_state():
    """
    Test the update state request type.
    """
    complete_state = CompleteState()
    request = UpdateStateRequest(complete_state, ["test_mask"])
    assert (
        request._request.updateStateRequest.newState
        == complete_state._to_proto()
    )
    assert request._request.updateStateRequest.updateMask == ["test_mask"]
    assert str(request) == str(request._to_proto())
