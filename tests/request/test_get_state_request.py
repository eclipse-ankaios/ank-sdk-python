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
This module contains unit tests for the GetStateRequest class in
the ankaios_sdk.
"""

from ankaios_sdk import GetStateRequest

def test_get_state():
    """
    Test the get state request type.
    """
    request = GetStateRequest(["test_mask"])
    assert request._request.completeStateRequest.fieldMask == ["test_mask"]
