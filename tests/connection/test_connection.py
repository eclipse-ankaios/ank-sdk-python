# Copyright (c) 2026 Elektrobit Automotive GmbH
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
This module contains unit tests for the Connection abstract base
class in the ankaios_sdk.
"""

import pytest
from ankaios_sdk import Connection, ConnectionType
from tests.request.test_request import generate_test_request


class _DummyConnection(Connection):
    """Minimal concrete Connection used to verify the abstract
    contract."""

    def __init__(self) -> None:
        super().__init__(
            lambda response: None,
            lambda request_id, log: None,
            lambda request_id, event: None,
        )
        self.written_requests = []
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def write_request(self, request) -> None:
        self.written_requests.append(request)


def test_connection_type_str():
    """
    Test the string representation of the ConnectionType enum.
    """
    assert str(ConnectionType.CONTROL_INTERFACE) == "CONTROL_INTERFACE"
    assert str(ConnectionType.COMMAND_INTERFACE) == "COMMAND_INTERFACE"


def test_connection_cannot_be_instantiated_directly():
    """
    Test that Connection cannot be instantiated directly, since it
    is an abstract base class.
    """
    with pytest.raises(TypeError):
        # pylint: disable=abstract-class-instantiated,no-value-for-parameter
        Connection()


def test_connection_concrete_subclass_implements_contract():
    """
    Test that a concrete Connection subclass can be instantiated and
    fulfills the connect/disconnect/write_request/connected contract.
    """
    conn = _DummyConnection()
    assert conn.connected is False

    conn.connect()
    assert conn.connected is True

    request = generate_test_request()
    conn.write_request(request)
    assert conn.written_requests == [request]

    conn.disconnect()
    assert conn.connected is False
