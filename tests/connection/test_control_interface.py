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

import os
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


def _generate_test_ci(
    add_response_callback=lambda _: None,
    add_log_callback=lambda _: None,
    add_event_callback=lambda _: None,
) -> ControlInterfaceConnection:
    """
    Builds a ControlInterfaceConnection whose callbacks do nothing,
    unless given.
    """
    return ControlInterfaceConnection(
        add_response_callback=add_response_callback,
        add_log_callback=add_log_callback,
        add_event_callback=add_event_callback,
    )


def test_state():
    """
    Test the state enum and the changing of the state.
    """
    ci = _generate_test_ci()
    ci._logger = MagicMock()
    assert ci._state == ControlInterfaceState.TERMINATED
    assert str(ci._state) == "TERMINATED"

    ci._set_state(ControlInterfaceState.TERMINATED)
    ci._logger.debug.assert_called_with(
        "State is already %s.", ControlInterfaceState.TERMINATED
    )

    ci._set_state(ControlInterfaceState.CONNECTION_CLOSED)
    ci._set_state(ControlInterfaceState.INITIALIZED)
    ci._logger.debug.assert_called_with(
        "State CONNECTION_CLOSED is unrecoverable."
    )
    assert ci._state == ControlInterfaceState.CONNECTION_CLOSED


def test_connection():
    """
    Test the connect / disconnect functionality.
    """
    ci = _generate_test_ci()
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
        # Kept so a later connect() can check it has stopped.
        assert ci._read_thread is mock_thread_instance
        output_file_mock.close.assert_called_once()
        assert ci._output_file is None

    # Test disconnect while not connected
    ci._logger = MagicMock()
    assert ci._state == ControlInterfaceState.TERMINATED
    ci.disconnect()
    ci._logger.debug.assert_called_with("Already disconnected.")


def test_connect_clears_disconnect_event():
    """
    connect() must clear a disconnect_event left set by a prior disconnect,
    otherwise the freshly started reader thread would stop immediately.
    """
    ci = _generate_test_ci()
    ci._disconnect_event.set()
    with patch("os.path.exists", return_value=True), patch(
        "threading.Thread"
    ) as mock_thread, patch("builtins.open"), patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ):
        mock_thread.return_value = MagicMock()
        ci.connect()

        assert not ci._disconnect_event.is_set()
        assert ci._state == ControlInterfaceState.INITIALIZED


def test_connect_refuses_while_previous_reader_alive():
    """
    connect() must refuse to start a second reader thread while the one
    of a previous connection has not stopped yet, since both would read
    the same fifo.
    """
    ci = _generate_test_ci()
    ci._read_thread = MagicMock()
    ci._read_thread.is_alive.return_value = True
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open"
    ) as mock_open_file, pytest.raises(
        ConnectionException,
        match="Previous connection is still shutting down.",
    ):
        ci.connect()

    mock_open_file.assert_not_called()
    assert ci._state == ControlInterfaceState.TERMINATED


def test_connect_after_previous_reader_stopped():
    """
    connect() succeeds once the reader thread of a previous connection
    has stopped.
    """
    ci = _generate_test_ci()
    ci._read_thread = MagicMock()
    ci._read_thread.is_alive.return_value = False
    with patch("os.path.exists", return_value=True), patch(
        "threading.Thread"
    ) as mock_thread, patch("builtins.open"), patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ):
        mock_thread.return_value = MagicMock()
        ci.connect()

    assert ci._read_thread is mock_thread.return_value
    assert ci._state == ControlInterfaceState.INITIALIZED


def test_connect_while_agent_disconnected_raises():
    """
    While the agent is gone the reader thread is still running, so
    connect() must treat the connection as already connected.
    """
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.AGENT_DISCONNECTED
    with pytest.raises(ConnectionException, match="Already connected."):
        ci.connect()


def test_disconnect_while_agent_disconnected():
    """
    disconnect() must stop the reader thread and release the output
    file while the agent is gone, too.
    """
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.AGENT_DISCONNECTED
    read_thread = MagicMock()
    read_thread.is_alive.return_value = False
    output_file_mock = MagicMock()
    ci._read_thread = read_thread
    ci._output_file = output_file_mock

    ci.disconnect()

    assert ci._disconnect_event.is_set()
    read_thread.join.assert_called_once_with(timeout=2)
    output_file_mock.close.assert_called_once()
    assert ci._output_file is None
    assert ci._state == ControlInterfaceState.TERMINATED


def test_disconnect_keeps_read_thread_that_did_not_stop():
    """
    If the reader thread does not stop in time, disconnect() logs an
    error and keeps it, so a following connect() is refused.
    """
    ci = _generate_test_ci()
    ci._logger = MagicMock()
    ci._state = ControlInterfaceState.CONNECTED
    read_thread = MagicMock()
    read_thread.is_alive.return_value = True
    ci._read_thread = read_thread

    ci.disconnect()

    ci._logger.error.assert_called_once_with("Read thread did not stop.")
    assert ci._read_thread is read_thread
    assert ci._state == ControlInterfaceState.TERMINATED
    with pytest.raises(
        ConnectionException,
        match="Previous connection is still shutting down.",
    ):
        ci.connect()


def test_change_state_from_reader():
    """
    The reader thread may change the state while no disconnect was
    requested.
    """
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.CONNECTED

    ci._change_state_from_reader(ControlInterfaceState.AGENT_DISCONNECTED)

    assert ci._state == ControlInterfaceState.AGENT_DISCONNECTED


def test_change_state_from_reader_ignored_after_disconnect():
    """
    Once a disconnect was requested, the reader thread must not
    overwrite the TERMINATED state set by disconnect().
    """
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.TERMINATED
    ci._disconnect_event.set()

    ci._change_state_from_reader(ControlInterfaceState.AGENT_DISCONNECTED)

    assert ci._state == ControlInterfaceState.TERMINATED


def test_cleanup_is_idempotent():
    """
    _cleanup() may be reached by both the reader thread and a caller;
    a repeat call must not raise or double-close the output file.
    """
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.CONNECTED
    output_file_mock = MagicMock()
    ci._output_file = output_file_mock

    ci._cleanup()
    ci._cleanup()

    output_file_mock.close.assert_called_once()
    assert ci._output_file is None
    assert ci._state == ControlInterfaceState.TERMINATED


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
        "ankaios_sdk.ControlInterfaceConnection._cleanup"
    ) as mock_cleanup:
        ci = _generate_test_ci()
        with pytest.raises(
            ConnectionException, match="Error while opening input fifo"
        ):
            ci._read_from_control_interface()
        # The reader thread tears down directly instead of calling
        # disconnect() (which would join the current thread).
        mock_cleanup.assert_called_once()
        assert ci._disconnect_event.is_set()

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

        ci = _generate_test_ci()

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
            "/run/ankaios/control_interface/input", "rb", buffering=0
        )
        mock_handle_response.assert_called_once()
        mock_file.return_value.close.assert_called_once()


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

        ci = _generate_test_ci()

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
            "/run/ankaios/control_interface/input", "rb", buffering=0
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

        ci = _generate_test_ci()

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
            "/run/ankaios/control_interface/input", "rb", buffering=0
        )
        mock_file.return_value.close.assert_called_once()
        assert ci._state == ControlInterfaceState.TERMINATED


def test_read_thread_handles_messages_arriving_together(tmp_path):
    """
    Two messages arriving in the fifo at once must both be handled
    right away, not leave the second one waiting for more data. Uses
    a real fifo, since this depends on how select() and the input
    file interact.
    """
    os.mkfifo(tmp_path / "input")
    # Opened read-write so neither side blocks waiting for the other.
    writer_fd = os.open(tmp_path / "input", os.O_RDWR)
    message = MESSAGE_BUFFER_UPDATE_SUCCESS_LENGTH + (
        MESSAGE_BUFFER_UPDATE_SUCCESS
    )
    handled = []
    two_handled = threading.Event()

    def _record(response):
        handled.append(response)
        if len(handled) == 2:
            two_handled.set()

    ci = _generate_test_ci()
    try:
        with patch.object(
            ControlInterfaceConnection,
            "ANKAIOS_CONTROL_INTERFACE_BASE_PATH",
            str(tmp_path),
        ), patch.object(ci, "_handle_response", side_effect=_record):
            os.write(writer_fd, message + message)
            read_thread = threading.Thread(
                target=ci._read_from_control_interface, daemon=True
            )
            read_thread.start()

            assert two_handled.wait(timeout=0.5)

            ci._disconnect_event.set()
            read_thread.join(timeout=2)
            assert not read_thread.is_alive()
    finally:
        os.close(writer_fd)

    assert [r.content_type for r in handled] == [
        ResponseType.UPDATE_STATE_SUCCESS,
        ResponseType.UPDATE_STATE_SUCCESS,
    ]


def test_read_thread_skips_incomplete_message():
    """
    A message cut short (the agent closed the fifo or a disconnect was
    requested while reading it) must be logged and not handled.
    """
    ci = _generate_test_ci()
    ci._logger = MagicMock()

    def _short_read(_input_file, _size):
        ci._disconnect_event.set()
        return b"\x01"

    with patch("builtins.open", mock_open()) as mock_file, patch(
        "os.set_blocking"
    ), patch("select.select", return_value=([True], [], [])), patch.object(
        ci, "_read_exactly", side_effect=_short_read
    ), patch.object(
        ci, "_handle_response"
    ) as mock_handle_response:
        mock_file.return_value.read.return_value = bytes([5])
        ci._read_from_control_interface()

    mock_handle_response.assert_not_called()
    ci._logger.error.assert_called_once_with(
        "Incomplete message read from the input fifo."
    )


def test_read_exactly_joins_chunks():
    """
    _read_exactly() keeps reading until it has the requested size,
    asking only for the bytes still missing.
    """
    ci = _generate_test_ci()
    input_file = MagicMock()
    input_file.read.side_effect = [b"ab", b"cd"]

    assert ci._read_exactly(input_file, 4) == b"abcd"
    assert [c.args for c in input_file.read.call_args_list] == [(4,), (2,)]


def test_read_exactly_waits_for_rest():
    """
    _read_exactly() waits with select() when the rest of the message
    has not arrived yet, instead of returning it cut short.
    """
    ci = _generate_test_ci()
    input_file = MagicMock()
    input_file.read.side_effect = [b"a", None, b"bc"]

    with patch("select.select") as mock_select:
        assert ci._read_exactly(input_file, 3) == b"abc"
    mock_select.assert_called_once_with([input_file], [], [], 1)


def test_read_exactly_stops_at_end_of_file():
    """
    _read_exactly() returns what it has when the agent closes the fifo.
    """
    ci = _generate_test_ci()
    input_file = MagicMock()
    input_file.read.side_effect = [b"ab", b""]

    assert ci._read_exactly(input_file, 4) == b"ab"


def test_read_exactly_stops_on_disconnect():
    """
    _read_exactly() stops reading once a disconnect was requested.
    """
    ci = _generate_test_ci()
    ci._disconnect_event.set()
    input_file = MagicMock()

    assert ci._read_exactly(input_file, 4) == b""
    input_file.read.assert_not_called()


def test_handle_response():
    """
    Test the _handle_response method of the Ankaios class.
    Test the general functionality.
    """
    response = Response(MESSAGE_BUFFER_UPDATE_SUCCESS)
    response_callback = MagicMock()
    ci = _generate_test_ci(add_response_callback=response_callback)
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
    ci = _generate_test_ci(add_response_callback=response_callback)
    ci._state = ControlInterfaceState.INITIALIZED

    ci._handle_response(ci_accepted_response)

    assert ci._state == ControlInterfaceState.CONNECTED

    # Got control interface accepted response while already connected
    response_callback = MagicMock()
    ci = _generate_test_ci(add_response_callback=response_callback)
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
    ci = _generate_test_ci(add_response_callback=response_callback)
    ci._state = ControlInterfaceState.INITIALIZED
    with pytest.raises(
        ConnectionClosedException, match="Connection closed reason"
    ):
        ci._handle_response(conn_closed_response)

    # Got connection closed response while already connected
    response_callback = MagicMock()
    ci = _generate_test_ci(add_response_callback=response_callback)
    ci._state = ControlInterfaceState.CONNECTED
    with pytest.raises(
        ConnectionClosedException, match="Connection closed reason"
    ):
        ci._handle_response(conn_closed_response)


def test_handle_response_logs():
    """
    Test the _handle_response method of the Ankaios class.
    Test the logs callback.
    """
    logs_response = Response(MESSAGE_BUFFER_LOGS_ENTRIES_RESPONSE)
    response_callback = MagicMock()
    logs_callback = MagicMock()

    ci = _generate_test_ci(
        add_response_callback=response_callback,
        add_log_callback=logs_callback,
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

    ci = _generate_test_ci(
        add_response_callback=response_callback,
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
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.CONNECTED
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ) as mock_initial_hello:
        ci._agent_gone_routine()
        mock_initial_hello.assert_not_called()

    ci._state = ControlInterfaceState.AGENT_DISCONNECTED
    with patch.object(
        ControlInterfaceConnection, "AGENT_RECONNECT_INTERVAL_SEC", 0.01
    ), patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello"
    ) as mock_initial_hello:

        mock_initial_hello.side_effect = BrokenPipeError

        agent_gone_thread = threading.Thread(
            target=ci._agent_gone_routine, daemon=True
        )
        agent_gone_thread.start()
        time.sleep(0.05)
        mock_initial_hello.side_effect = None
        time.sleep(0.05)
        agent_gone_thread.join(timeout=2)

        assert not agent_gone_thread.is_alive()
        mock_initial_hello.assert_called()
        assert ci._state == ControlInterfaceState.INITIALIZED


def test_agent_gone_routine_stops_on_disconnect():
    """
    _agent_gone_routine must exit promptly when a disconnect is requested,
    even while the agent stays gone.
    """
    ci = _generate_test_ci()
    ci._state = ControlInterfaceState.AGENT_DISCONNECTED
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._send_initial_hello",
        side_effect=BrokenPipeError,
    ):
        agent_gone_thread = threading.Thread(
            target=ci._agent_gone_routine, daemon=True
        )
        agent_gone_thread.start()
        ci._disconnect_event.set()
        agent_gone_thread.join(timeout=2)

        assert not agent_gone_thread.is_alive()
        assert ci._state == ControlInterfaceState.AGENT_DISCONNECTED


def test_write_to_pipe():
    """
    Test the _write_to_pipe method of the ControlInterfaceConnection class.
    """
    ci = _generate_test_ci()
    request = _control_api.FromAnkaios()

    ci._output_file = None
    with pytest.raises(
        ConnectionException, match="Could not write to pipe"
    ):
        ci._write_to_pipe(request)

    output_file = MagicMock()
    ci._output_file = output_file

    ci._write_to_pipe(request)

    output_file.write.assert_called()
    output_file.flush.assert_called_once()


def test_write_to_pipe_closed_output_file():
    """
    A write whose output file was closed by a concurrent disconnect
    must raise a ConnectionException, not a ValueError.
    """
    ci = _generate_test_ci()
    output_file = MagicMock()
    output_file.write.side_effect = ValueError("write to closed file")
    ci._output_file = output_file
    request = _control_api.FromAnkaios()

    with pytest.raises(
        ConnectionException,
        match="Could not write to pipe, output file closed.",
    ):
        ci._write_to_pipe(request)


def test_write_request():
    """
    Test the write_request method of the ControlInterfaceConnection class.
    """
    ci = _generate_test_ci()
    test_request = generate_test_request()

    ci._state = ControlInterfaceState.TERMINATED
    with pytest.raises(
        ConnectionException, match="Could not write to pipe"
    ):
        ci.write_request(test_request)

    ci._state = ControlInterfaceState.CONNECTED
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._write_to_pipe"
    ) as mock_write:
        ci.write_request(test_request)
        mock_write.assert_called_once()

    ci._state = ControlInterfaceState.CONNECTION_CLOSED
    with pytest.raises(
        ConnectionClosedException,
        match="Could not write to pipe, connection closed.",
    ):
        ci.write_request(test_request)


def test_send_initial_hello():
    """
    Test the _send_initial_hello method of the Ankaios class.
    """
    ci = _generate_test_ci()
    with patch(
        "ankaios_sdk.ControlInterfaceConnection._write_to_pipe"
    ) as mock_write:
        initial_hello = _control_api.ToAnkaios(
            hello=_control_api.Hello(protocolVersion=str(ANKAIOS_VERSION))
        )
        ci._send_initial_hello()
        mock_write.assert_called_once_with(initial_hello)
