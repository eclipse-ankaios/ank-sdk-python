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
This module contains unit tests for the ResponseEvent class in the ankaios_sdk.
"""

import pytest
from ankaios_sdk import ResponseEvent, Response
from tests.response.test_response import MESSAGE_BUFFER_ERROR


def test_event():
    """
    Test the set and wait for event.
    """
    response_event = ResponseEvent()
    assert not response_event.is_set()

    response = Response(MESSAGE_BUFFER_ERROR)
    response_event.set_response(response)
    assert response_event.is_set()

    assert response_event.wait_for_response(0.01) == response

    response_event.clear()
    assert not response_event.is_set()

    with pytest.raises(TimeoutError):
        response_event.wait_for_response(0.01)
