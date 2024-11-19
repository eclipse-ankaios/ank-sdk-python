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
This module contains unit tests for the ControlInterface class
in the ankaios_sdk.
"""

import threading
import time
from unittest.mock import patch, mock_open, MagicMock
import pytest
from ankaios_sdk import ControlInterface, ControlInterfaceState, \
    ControlInterfaceException
from ankaios_sdk.utils import ANKAIOS_VERSION
from ankaios_sdk._protos import _control_api
from tests.test_request import generate_test_request
from tests.response.test_response import MESSAGE_BUFFER_UPDATE_SUCCESS, \
    MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH


def test_state():
    """
    Test the state enum and the changing of the state.
    """
    state_changed = MagicMock()
    ci = ControlInterface(
        add_response_callback=lambda _: None,
        state_changed_callback=state_changed
    )
    ci.logger = MagicMock()
    assert ci.state == ControlInterfaceState.DISCONNECTED
    assert str(ci.state) == "DISCONNECTED"

    ci.change_state(ControlInterfaceState.CONNECTED)
    assert ci.state == ControlInterfaceState.CONNECTED
    state_changed.assert_called_once_with(ControlInterfaceState.CONNECTED)

    ci.change_state(ControlInterfaceState.CONNECTED)
    ci.logger.debug.assert_called_with(
        "State is already %s.", ControlInterfaceState.CONNECTED)


def test_connection():
    """
    Test the connect / disconnect functionality.
    """
    ci = ControlInterface(
        add_response_callback=lambda _: None,
        state_changed_callback=lambda _: None
    )
    ci.state = ControlInterfaceState.CONNECTED

    # Already connected
    with pytest.raises(ControlInterfaceException,
                       match="Already connected."):
        ci.connect()

    # Test input pipe does not exist
    ci.state = ControlInterfaceState.DISCONNECTED
    with patch("os.path.exists") as mock_exists, \
        pytest.raises(ControlInterfaceException,
                      match="Control interface input fifo"):
        mock_exists.side_effect = lambda path: \
            path != "/run/ankaios/control_interface/input"
        ci.connect()

    # Test output pipe does not exist
    with patch("os.path.exists") as mock_exists, \
        pytest.raises(ControlInterfaceException,
                      match="Control interface output fifo"):
        mock_exists.side_effect = lambda path: \
            path != "/run/ankaios/control_interface/output"
        ci.connect()

    # Test output pipe error
    with patch("os.path.exists") as mock_exists, \
        patch("builtins.open") as mock_open_file, \
        pytest.raises(ControlInterfaceException,
                      match="Error while opening output fifo"):
        mock_exists.return_value = True
        mock_open_file.side_effect = OSError
        ci.connect()

    # Test success
    with patch("os.path.exists") as mock_exists, \
            patch("threading.Thread") as mock_thread, \
            patch("builtins.open") as mock_open_file, \
            patch("ankaios_sdk.ControlInterface._send_initial_hello") \
            as mock_initial_hello:
        mock_exists.return_value = True
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        output_file_mock = MagicMock()
        mock_open_file.return_value = output_file_mock

        # Build ankaios and connect
        ci.connect()
        mock_thread.assert_called_once_with(
            target=ci._read_from_control_interface,
            daemon=True
        )
        mock_thread_instance.start.assert_called_once()
        mock_open_file.assert_called_once_with(
            "/run/ankaios/control_interface/output", "ab"
        )
        assert ci._read_thread is not None
        assert ci._output_file == output_file_mock
        mock_initial_hello.assert_called_once()
        assert ci.state == ControlInterfaceState.CONNECTED
        assert not ci._disconnect_event.is_set()

        # Disconnect
        ci.disconnect()

        assert ci._disconnect_event.is_set()
        assert ci.state == ControlInterfaceState.DISCONNECTED
        mock_thread_instance.join.assert_called_once()
        assert ci._read_thread is None
        output_file_mock.close.assert_called_once()
        assert ci._output_file is None

    # Test disconnect while not connected
    ci.logger = MagicMock()
    assert ci.state == ControlInterfaceState.DISCONNECTED
    ci.disconnect()
    ci.logger.debug.assert_called_with("Already disconnected.")


def test_read_from_control_interface():
    """
    Test the _read_from_control_interface method of the Ankaios class.
    """
    input_file_content = MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH + \
        MESSAGE_BUFFER_UPDATE_SUCCESS
    response_callback = MagicMock()

    # Test error while opening input pipe
    with patch("builtins.open", side_effect=OSError), \
         patch("ankaios_sdk.ControlInterface.disconnect") as mock_disconnect:
        ci = ControlInterface(
            add_response_callback=response_callback,
            state_changed_callback=lambda _: None
        )
        with pytest.raises(ControlInterfaceException,
                           match="Error while opening input fifo"):
            ci._read_from_control_interface()
        mock_disconnect.assert_called_once()

    # Test success
    with patch("builtins.open", mock_open()) as mock_file, \
            patch("os.set_blocking") as _, \
            patch("select.select") as mock_select:
        mock_select.return_value = ([True], [], [])
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.read.side_effect = \
            [bytes([b]) for b in input_file_content]

        ci = ControlInterface(
            add_response_callback=response_callback,
            state_changed_callback=lambda _: None
        )

        # Start thread (similar to _connect)
        ci._read_thread = threading.Thread(
            target=ci._read_from_control_interface,
            daemon=True
        )
        ci.state = ControlInterfaceState.CONNECTED
        ci._read_thread.start()
        time.sleep(0.01)

        # Stop thread (similar to disconnect)
        ci.state = ControlInterfaceState.DISCONNECTED
        ci._disconnect_event.set()
        ci._read_thread.join()

        mock_file.assert_called_once_with(
            "/run/ankaios/control_interface/input", "rb")
        response_callback.assert_called_once()


def test_write_to_pipe():
    """
    Test the _write_to_pipe method of the ControlInterface class.
    """
    ci = ControlInterface(
        add_response_callback=lambda _: None,
        state_changed_callback=lambda _: None
        )

    ci._output_file = None
    with pytest.raises(ControlInterfaceException,
                       match="Could not write to pipe"):
        ci._write_to_pipe(_control_api.FromAnkaios())

    output_file = MagicMock()
    ci._output_file = output_file

    ci._write_to_pipe(_control_api.FromAnkaios())

    output_file.write.assert_called()
    output_file.flush.assert_called_once()


def test_write_request():
    """
    Test the write_request method of the ControlInterface class.
    """
    ci = ControlInterface(
        add_response_callback=lambda _: None,
        state_changed_callback=lambda _: None
        )

    ci.state = ControlInterfaceState.DISCONNECTED
    with pytest.raises(ControlInterfaceException,
                       match="Could not write to pipe"):
        ci.write_request(generate_test_request())

    ci.state = ControlInterfaceState.CONNECTED
    with patch("ankaios_sdk.ControlInterface._write_to_pipe") as mock_write:
        ci.write_request(generate_test_request())
        mock_write.assert_called_once()


def test_send_initial_hello():
    """
    Test the _send_initial_hello method of the Ankaios class.
    """
    ci = ControlInterface(
        add_response_callback=lambda _: None,
        state_changed_callback=lambda _: None
        )
    with patch("ankaios_sdk.ControlInterface._write_to_pipe") as mock_write:
        initial_hello = _control_api.ToAnkaios(
            hello=_control_api.Hello(
                protocolVersion=str(ANKAIOS_VERSION)
            )
        )
        ci._send_initial_hello()
        mock_write.assert_called_once_with(initial_hello)
