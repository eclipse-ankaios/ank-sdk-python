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
This module contains unit tests for the ControlInterfaceConnection class
in the ankaios_sdk.
"""

import threading
import time
from unittest.mock import patch, mock_open, MagicMock
import pytest
from ankaios_sdk import (
    ControlInterfaceConnection,
    Response,
    ResponseException,
    ResponseType,
    ControlInterfaceState,
    ConnectionException,
    ConnectionClosedException,
)
from ankaios_sdk.utils import ANKAIOS_VERSION
from ankaios_sdk._protos import _control_api
from tests.request.test_request import generate_test_request
from tests.response.test_response import (
    MESSAGE_BUFFER_UPDATE_SUCCESS,
    MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH,
    MESSAGE_BUFFER_CONTROL_INTERFACE_ACCEPTED,
    MESSAGE_BUFFER_CONNECTION_CLOSED,
    MESSAGE_BUFFER_CONNECTION_CLOSED_LENGTH,
    MESSAGE_BUFFER_LOGS_ENTRIES_RESPONSE,
    MESSAGE_BUFFER_EVENT_ENTRY_RESPONSE,
)


def test_state():
    """
    Test the state enum and the changing of the state.
    """
    ci = ControlInterfaceConnection(
        add_response_callback=lambda _: None,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    ci._logger = MagicMock()
    assert ci._state == ControlInterfaceState.TERMINATED
    assert str(ci._state) == "TERMINATED"

    ci.change_state(ControlInterfaceState.TERMINATED)
    ci._logger.debug.assert_called_with(
        "State is already %s.", ControlInterfaceState.TERMINATED
    )

    ci.change_state(ControlInterfaceState.CONNECTION_CLOSED)
    ci.change_state(ControlInterfaceState.INITIALIZED)
    ci._logger.debug.assert_called_with(
        "State CONNECTION_CLOSED is unrecoverable."
    )


def test_connection():
    """
    Test the connect / disconnect functionality.
    """
    ci = ControlInterfaceConnection(
        add_response_callback=lambda _: None,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    ci._state = ControlInterfaceState.CONNECTED
    assert ci.connected

    # Already connected
    with pytest.raises(ConnectionException, match="Already connected."):
        ci.connect()

    # Test input pipe does not exist
    ci._state = ControlInterfaceState.TERMINATED
    assert not ci.connected
    with patch("os.path.exists") as mock_exists, pytest.raises(
        ConnectionException, match="Control interface input fifo"
    ):
        mock_exists.side_effect = (
            lambda path: path != "/run/ankaios/control_interface/input"
        )
        ci.connect()

    # Test output pipe does not exist
    with patch("os.path.exists") as mock_exists, pytest.raises(
        ConnectionException, match="Control interface output fifo"
    ):
        mock_exists.side_effect = (
            lambda path: path != "/run/ankaios/control_interface/output"
        )
        ci.connect()

    # Test output pipe error
    with patch("os.path.exists") as mock_exists, patch(
        "builtins.open"
    ) as mock_open_file, pytest.raises(
        ConnectionException, match="Error while opening output fifo"
    ):
        mock_exists.return_value = True
        mock_open_file.side_effect = OSError
        ci.connect()

    # Test success
    with patch("os.path.exists") as mock_exists, patch(
        "threading.Thread"
    ) as mock_thread, patch("builtins.open") as mock_open_file, patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ) as mock_initial_hello:
        mock_exists.return_value = True
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        output_file_mock = MagicMock()
        mock_open_file.return_value = output_file_mock

        # Build ankaios and connect
        ci.connect()
        mock_thread.assert_called_once_with(
            target=ci._read_from_control_interface, daemon=True
        )
        mock_thread_instance.start.assert_called_once()
        mock_open_file.assert_called_once_with(
            "/run/ankaios/control_interface/output", "ab"
        )
        assert ci._read_thread is not None
        assert ci._output_file == output_file_mock
        mock_initial_hello.assert_called_once()
        assert ci._state == ControlInterfaceState.INITIALIZED
        assert not ci._disconnect_event.is_set()

        # Disconnect
        ci.disconnect()

        assert ci._disconnect_event.is_set()
        assert ci._state == ControlInterfaceState.TERMINATED
        mock_thread_instance.join.assert_called_once()
        assert ci._read_thread is None
        output_file_mock.close.assert_called_once()
        assert ci._output_file is None
        assert ci._input_file is None

    # Test disconnect while not connected
    ci._logger = MagicMock()
    assert ci._state == ControlInterfaceState.TERMINATED
    ci.disconnect()
    ci._logger.debug.assert_called_with("Already disconnected.")


def test_decode_response():
    """
    Test the _decode_response static method of the ControlInterfaceConnection
    class, which owns the control interface's own envelope
    (FromAnkaios) unwrapping, for all 3 possible variants plus the
    parsing-error case.
    """
    response = ControlInterfaceConnection._decode_response(
        MESSAGE_BUFFER_UPDATE_SUCCESS
    )
    assert response.content_type == ResponseType.UPDATE_STATE_SUCCESS

    response = ControlInterfaceConnection._decode_response(
        MESSAGE_BUFFER_CONTROL_INTERFACE_ACCEPTED
    )
    assert response.content_type == ResponseType.CONTROL_INTERFACE_ACCEPTED

    response = ControlInterfaceConnection._decode_response(
        MESSAGE_BUFFER_CONNECTION_CLOSED
    )
    assert response.content_type == ResponseType.CONNECTION_CLOSED
    assert response.content == "Connection closed reason"

    with pytest.raises(ResponseException, match="Parsing error"):
        ControlInterfaceConnection._decode_response(b"invalid_buffer{")


def test_read_thread_general():
    """
    Test the _read_from_control_interface method of the
    ControlInterfaceConnection class. Test success and error with
    the input file.
    """
    update_success_content = (
        MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH + MESSAGE_BUFFER_UPDATE_SUCCESS
    )

    # Test error while opening input pipe
    with patch("builtins.open", side_effect=OSError), patch(
        "ankaios_sdk.ControlInterfaceConnection.disconnect"
    ) as mock_disconnect:
        ci = ControlInterfaceConnection(
            add_response_callback=lambda _: None,
            add_log_callback=lambda _: None,
            add_event_callback=lambda _: None,
        )
        with pytest.raises(
            ConnectionException, match="Error while opening input fifo"
        ):
            ci._read_from_control_interface()
        mock_disconnect.assert_called_once()

    # Test success
    with patch("builtins.open", mock_open()) as mock_file, patch(
        "ankaios_sdk.ControlInterfaceConnection._handle_response"
    ) as mock_handle_response, patch("os.set_blocking") as _, patch(
        "select.select"
    ) as mock_select:
        mock_select.return_value = ([True], [], [])
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.read.side_effect = [
            bytes([b]) for b in update_success_content
        ]

        ci = ControlInterfaceConnection(
            add_response_callback=lambda _: None,
            add_log_callback=lambda _: None,
            add_event_callback=lambda _: None,
        )

        # Start thread (similar to _connect)
        ci._read_thread = threading.Thread(
            target=ci._read_from_control_interface, daemon=True
        )
        ci._state = ControlInterfaceState.CONNECTED
        ci._read_thread.start()
        time.sleep(0.01)

        # Stop thread (similar to disconnect)
        ci._state = ControlInterfaceState.TERMINATED
        ci._disconnect_event.set()
        ci._read_thread.join()

        mock_file.assert_called_once_with(
            "/run/ankaios/control_interface/input", "rb"
        )
        mock_handle_response.assert_called_once()


def test_read_thread_agent_disconnected():
    """
    Test the _read_from_control_interface method of the Ankaios class.
    Test agent disconnected case
    """
    with patch("builtins.open", mock_open()) as mock_file, patch(
        "os.set_blocking"
    ) as _, patch("select.select") as mock_select, patch(
        "ankaios_sdk.ControlInterfaceConnection._agent_gone_routine"
    ) as mock_agent_gone:

        # Data is available, but read returns empty
        mock_select.return_value = ([True], [], [])
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.read.return_value = b""

        ci = ControlInterfaceConnection(
            add_response_callback=lambda _: None,
            add_log_callback=lambda _: None,
            add_event_callback=lambda _: None,
        )

        # Start thread (similar to _connect)
        ci._read_thread = threading.Thread(
            target=ci._read_from_control_interface, daemon=True
        )
        ci._state = ControlInterfaceState.CONNECTED
        ci._read_thread.start()
        time.sleep(0.01)

        assert ci._state == ControlInterfaceState.AGENT_DISCONNECTED

        # Stop thread (similar to disconnect)
        ci._state = ControlInterfaceState.TERMINATED
        ci._disconnect_event.set()
        ci._read_thread.join()

        mock_file.assert_called_once_with(
            "/run/ankaios/control_interface/input", "rb"
        )
        mock_agent_gone.assert_called()


def test_read_thread_connection_closed():
    """
    Test the _read_from_control_interface method of the Ankaios class.
    Test connection closed case.
    """
    connection_closed_content = (
        MESSAGE_BUFFER_CONNECTION_CLOSED_LENGTH
        + MESSAGE_BUFFER_CONNECTION_CLOSED
    )

    with patch("builtins.open", mock_open()) as mock_file, patch(
        "ankaios_sdk.ControlInterfaceConnection._handle_response",
        side_effect=ConnectionClosedException,
    ), patch("os.set_blocking") as _, patch("select.select") as mock_select:
        mock_select.return_value = ([True], [], [])
        mock_file_handle = mock_file.return_value.__enter__.return_value
        mock_file_handle.read.side_effect = [
            bytes([b]) for b in connection_closed_content
        ]

        ci = ControlInterfaceConnection(
            add_response_callback=lambda _: None,
            add_log_callback=lambda _: None,
            add_event_callback=lambda _: None,
        )

        # Start thread (similar to _connect)
        ci._read_thread = threading.Thread(
            target=ci._read_from_control_interface, daemon=True
        )
        ci._state = ControlInterfaceState.CONNECTED
        ci._read_thread.start()
        time.sleep(0.01)

        # Thread should stop automatically
        ci._read_thread.join()

        mock_file.assert_called_once_with(
            "/run/ankaios/control_interface/input", "rb"
        )
        assert ci._input_file is None


def test_handle_response():
    """
    Test the _handle_response method of the Ankaios class.
    Test the general functionality.
    """
    response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
    response_callback = MagicMock()
    ci = ControlInterfaceConnection(
        add_response_callback=response_callback,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    ci._logger = MagicMock()

    # Test handle when not connected
    ci._state = ControlInterfaceState.TERMINATED

    ci._handle_response(response)

    ci._logger.warning.assert_called_with(
        "Received response %s, but not in a valid state. Ignoring..",
        response.content_type,
    )

    # Test handle when just initialized
    ci._state = ControlInterfaceState.INITIALIZED

    ci._handle_response(response)

    ci._logger.error.assert_called_with(
        "Received response %s, but expected "
        "CONTROL_INTERFACE_ACCEPTED. Ignoring..",
        response.content_type,
    )

    # Test handle when connected
    ci._state = ControlInterfaceState.CONNECTED
    response_callback.assert_not_called()

    ci._handle_response(response)

    response_callback.assert_called_once_with(response)


def test_handle_response_control_interface_accepted():
    """
    Test the _handle_response method of the Ankaios class.
    Test control interface accepted cases.
    """
    ci_accepted_response = Response(MESSAGE_BUFFER_CONTROL_INTERFACE_ACCEPTED)

    # Got control interface accepted response as initial response
    response_callback = MagicMock()
    ci = ControlInterfaceConnection(
        add_response_callback=response_callback,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    ci._state = ControlInterfaceState.INITIALIZED

    ci._handle_response(ci_accepted_response)

    assert ci._state == ControlInterfaceState.CONNECTED

    # Got control interface accepted response while already connected
    response_callback = MagicMock()
    ci = ControlInterfaceConnection(
        add_response_callback=response_callback,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    ci._logger = MagicMock()
    ci._state = ControlInterfaceState.CONNECTED

    ci._handle_response(ci_accepted_response)

    ci._logger.warning.assert_called_with(
        "Received unexpected control interface accepted response."
    )


def test_handle_response_connection_closed():
    """
    Test the _handle_response method of the Ankaios class.
    Test connection closed cases.
    """
    conn_closed_response = Response(MESSAGE_BUFFER_CONNECTION_CLOSED)

    # Got connection closed response as initial response
    response_callback = MagicMock()
    with pytest.raises(
        ConnectionClosedException, match="Connection closed reason"
    ):
        ci = ControlInterfaceConnection(
            add_response_callback=response_callback,
            add_log_callback=lambda _: None,
            add_event_callback=lambda _: None,
        )
        ci._state = ControlInterfaceState.INITIALIZED

        ci._handle_response(conn_closed_response)

    # Got connection closed response while already connected
    response_callback = MagicMock()
    with pytest.raises(
        ConnectionClosedException, match="Connection closed reason"
    ):
        ci = ControlInterfaceConnection(
            add_response_callback=response_callback,
            add_log_callback=lambda _: None,
            add_event_callback=lambda _: None,
        )
        ci._state = ControlInterfaceState.CONNECTED

        ci._handle_response(conn_closed_response)


def test_handle_response_logs():
    """
    Test the _handle_response method of the Ankaios class.
    Test the logs callback.
    """
    logs_response = Response(MESSAGE_BUFFER_LOGS_ENTRIES_RESPONSE)
    response_callback = MagicMock()
    logs_callback = MagicMock()

    ci = ControlInterfaceConnection(
        add_response_callback=response_callback,
        add_log_callback=logs_callback,
        add_event_callback=lambda _: None,
    )
    ci._state = ControlInterfaceState.CONNECTED

    ci._handle_response(logs_response)

    response_callback.assert_not_called()
    logs_callback.assert_called_once()


def test_handle_response_events():
    """
    Test the _handle_response method of the Ankaios class.
    Test the events callback.
    """
    events_response = Response(MESSAGE_BUFFER_EVENT_ENTRY_RESPONSE)
    response_callback = MagicMock()
    events_callback = MagicMock()

    ci = ControlInterfaceConnection(
        add_response_callback=response_callback,
        add_log_callback=lambda _: None,
        add_event_callback=events_callback,
    )
    ci._state = ControlInterfaceState.CONNECTED

    ci._handle_response(events_response)

    response_callback.assert_not_called()
    events_callback.assert_called_once()


def test_agent_gone_routine():
    """
    Test the _agent_gone_routine method of the
    ControlInterfaceConnection class.
    """
    ci = ControlInterfaceConnection(
        add_response_callback=lambda _: None,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    ci._state = ControlInterfaceState.CONNECTED
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ) as mock_initial_hello:
        ci._agent_gone_routine()
        mock_initial_hello.assert_not_called()

    ci._state = ControlInterfaceState.AGENT_DISCONNECTED
    original_sleep = time.sleep
    with patch(
        "time.sleep",
        new=lambda x: original_sleep(x) if x != 1 else original_sleep(0.01),
    ) as _, patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ) as mock_initial_hello:

        mock_initial_hello.side_effect = BrokenPipeError

        agent_gone_thread = threading.Thread(
            target=ci._agent_gone_routine, daemon=True
        )
        agent_gone_thread.start()
        time.sleep(0.01)
        mock_initial_hello.side_effect = None
        time.sleep(0.01)
        agent_gone_thread.join()

        mock_initial_hello.assert_called()
        assert ci._state == ControlInterfaceState.INITIALIZED


def test_write_to_pipe():
    """
    Test the _write_to_pipe method of the ControlInterfaceConnection class.
    """
    ci = ControlInterfaceConnection(
        add_response_callback=lambda _: None,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )

    ci._output_file = None
    with pytest.raises(
        ConnectionException, match="Could not write to pipe"
    ):
        ci._write_to_pipe(_control_api.FromAnkaios())

    output_file = MagicMock()
    ci._output_file = output_file

    ci._write_to_pipe(_control_api.FromAnkaios())

    output_file.write.assert_called()
    output_file.flush.assert_called_once()


def test_write_request():
    """
    Test the write_request method of the ControlInterfaceConnection class.
    """
    ci = ControlInterfaceConnection(
        add_response_callback=lambda _: None,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )

    ci._state = ControlInterfaceState.TERMINATED
    with pytest.raises(
        ConnectionException, match="Could not write to pipe"
    ):
        ci.write_request(generate_test_request())

    ci._state = ControlInterfaceState.CONNECTED
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._write_to_pipe"
    ) as mock_write:
        ci.write_request(generate_test_request())
        mock_write.assert_called_once()

    ci._state = ControlInterfaceState.CONNECTION_CLOSED
    with pytest.raises(
        ConnectionClosedException,
        match="Could not write to pipe, connection closed.",
    ):
        ci.write_request(generate_test_request())


def test_send_initial_hello():
    """
    Test the _send_initial_hello method of the Ankaios class.
    """
    ci = ControlInterfaceConnection(
        add_response_callback=lambda _: None,
        add_log_callback=lambda _: None,
        add_event_callback=lambda _: None,
    )
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._write_to_pipe"
    ) as mock_write:
        initial_hello = _control_api.ToAnkaios(
            hello=_control_api.Hello(protocolVersion=str(ANKAIOS_VERSION))
        )
        ci._send_initial_hello()
        mock_write.assert_called_once_with(initial_hello)
