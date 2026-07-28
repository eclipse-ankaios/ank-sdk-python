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
This module contains unit tests for the GrpcConnection class in the
ankaios_sdk.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import grpc
import pytest

from ankaios_sdk import ConnectionException
from ankaios_sdk._components.connection.grpc_interface import (
    GrpcConnection,
    GrpcConnectionState,
)
from ankaios_sdk._protos import grpc_api_pb2 as _grpc_api
from ankaios_sdk._protos import _ank_base
from ankaios_sdk.utils import ANKAIOS_VERSION
from tests.request.test_request import generate_test_request
from tests.response.test_log_response import (
    generate_test_log_entry,
    generate_test_logs_stop_reponse,
)


SERVER_URL = "http://127.0.0.1:25551"
SERVER_TARGET = "127.0.0.1:25551"


class _FakeCall:
    """
    A fake bidi call standing in for the object returned by
    stub.ConnectCommand(...): an iterable of FromServer messages,
    optionally followed by an error, with a working cancel().
    """

    def __init__(self, messages=None, error=None):
        self._messages = list(messages) if messages else []
        self._error = error
        self.cancelled = threading.Event()

    def __iter__(self):
        for message in self._messages:
            if self.cancelled.is_set():
                return
            yield message
        if self._error is not None:
            raise self._error
        while not self.cancelled.is_set():
            time.sleep(0.01)

    def cancel(self):
        """Cancels the fake call, unblocking __iter__."""
        self.cancelled.set()


def _mock_stub(call_factory):
    """
    Builds a MagicMock standing in for CommandConnectionStub, whose
    ConnectCommand(request_iterator) drains the request_iterator in a
    background thread (collecting the sent ToServer messages) and
    returns a call built via call_factory().

    :returns: A tuple of (stub_instance, sent_messages list).
    """
    sent_messages = []

    def _connect_command(request_iterator):
        def _drain():
            for message in request_iterator:
                sent_messages.append(message)

        threading.Thread(target=_drain, daemon=True).start()
        return call_factory()

    stub_instance = MagicMock()
    stub_instance.ConnectCommand.side_effect = _connect_command
    return stub_instance, sent_messages


def _generate_test_connection(**kwargs) -> GrpcConnection:
    return GrpcConnection(
        SERVER_URL,
        add_response_callback=MagicMock(),
        add_log_callback=MagicMock(),
        add_event_callback=MagicMock(),
        **kwargs,
    )


def test_grpc_connection_state_str():
    """
    Test the string representation of the GrpcConnectionState enum.
    """
    assert str(GrpcConnectionState.CONNECTED) == "CONNECTED"
    assert str(GrpcConnectionState.TERMINATED) == "TERMINATED"


def test_init_validation():
    """
    Test the __init__ validation of the TLS certificate arguments.
    """
    # No certs: insecure connection, no error
    conn = _generate_test_connection()
    assert conn._ca_pem is None
    assert conn._crt_pem is None
    assert conn._key_pem is None

    # All three certs: secured connection, no error
    conn = _generate_test_connection(
        ca_pem="ca-secret", crt_pem="crt-secret", key_pem="key-secret"
    )
    assert conn._ca_pem == "ca-secret"
    assert conn._crt_pem == "crt-secret"
    assert conn._key_pem == "key-secret"

    # Partial certs: error
    with pytest.raises(ValueError, match="must all be provided together"):
        _generate_test_connection(crt_pem="crt-secret")


def test_connected_property_default():
    """
    Test that a freshly created connection is not connected.
    """
    conn = _generate_test_connection()
    assert conn.connected is False


def test_connect_already_connected_raises():
    """
    Test that connect() raises if already connected.
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.CONNECTED
    with pytest.raises(ConnectionException, match="Already connected."):
        conn.connect()


def test_connect_fails_on_unreachable_server():
    """
    Test that connect() fails (and leaves the state untouched) when
    the server is unreachable. Port 0 is never a valid connection
    target, so this fails fast without needing a real server.
    """
    conn = _generate_test_connection()
    conn._server_url = "127.0.0.1:0"

    with patch.object(
        GrpcConnection, "CHANNEL_READY_TIMEOUT", 1.0
    ), pytest.raises(
        ConnectionException, match="Could not connect to the Ankaios server"
    ):
        conn.connect()
    assert conn._state == GrpcConnectionState.TERMINATED
    assert conn.connected is False


def test_disconnect_without_connect():
    """
    Test that disconnect() without a prior connect() is a no-op.
    """
    conn = _generate_test_connection()
    conn._logger = MagicMock()
    conn.disconnect()
    conn._logger.debug.assert_called_with("Already disconnected.")


def test_write_request_not_connected_raises():
    """
    Test that write_request() raises if not connected.
    """
    conn = _generate_test_connection()
    with pytest.raises(
        ConnectionException, match="Could not write to the gRPC connection"
    ):
        conn.write_request(generate_test_request())


def test_connect_write_and_disconnect_success():
    """
    Test the full connect -> write_request -> disconnect flow using a
    mocked gRPC channel/stub boundary.
    """
    fake_call = _FakeCall()
    stub_instance, sent_messages = _mock_stub(lambda: fake_call)

    with patch(
        "ankaios_sdk._components.connection.grpc_interface."
        "_grpc_api_grpc.CommandConnectionStub"
    ) as mock_stub_cls, patch("grpc.insecure_channel") as mock_channel, patch(
        "grpc.channel_ready_future"
    ) as mock_ready:
        mock_stub_cls.return_value = stub_instance
        mock_channel.return_value = MagicMock()
        mock_ready.return_value = MagicMock(
            result=MagicMock(return_value=None)
        )

        conn = _generate_test_connection()
        conn.connect()
        assert conn.connected is True
        assert conn._reader_thread.is_alive()

        time.sleep(0.05)
        assert len(sent_messages) == 1
        assert sent_messages[0].WhichOneof("ToServerEnum") == "commanderHello"
        assert (
            sent_messages[0].commanderHello.protocolVersion
            == ANKAIOS_VERSION
        )

        request = generate_test_request()
        conn.write_request(request)
        time.sleep(0.05)
        assert len(sent_messages) == 2
        assert sent_messages[1].WhichOneof("ToServerEnum") == "request"
        assert sent_messages[1].request == request._to_proto()

        conn.disconnect()
        assert conn.connected is False
        assert fake_call.cancelled.is_set()
        assert conn._reader_thread is None

        # Disconnecting again is a no-op.
        conn.disconnect()


def test_open_stream_channel_not_ready_raises():
    """
    Test that _open_stream() raises ConnectionException if the
    channel does not become ready in time.
    """
    with patch("grpc.insecure_channel") as mock_channel, patch(
        "grpc.channel_ready_future"
    ) as mock_ready:
        mock_channel.return_value = MagicMock()
        mock_ready.return_value = MagicMock(
            result=MagicMock(side_effect=grpc.FutureTimeoutError())
        )
        conn = _generate_test_connection()
        with pytest.raises(
            ConnectionException, match="Could not connect"
        ):
            conn._open_stream()


def test_build_channel_insecure():
    """
    Test that _build_channel() builds a plaintext channel when no
    certificates are provided, using the bare host:port target (the
    http:// scheme is stripped, since grpc-python's channel target
    doesn't understand URL schemes).
    """
    with patch("grpc.insecure_channel") as mock_channel:
        conn = _generate_test_connection()
        conn._build_channel()
        mock_channel.assert_called_once_with(SERVER_TARGET)


def test_build_channel_secure():
    """
    Test that _build_channel() builds a mTLS-secured channel when
    certificates are provided, using the bare host:port target.
    """
    with patch("grpc.secure_channel") as mock_secure_channel, patch(
        "grpc.ssl_channel_credentials"
    ) as mock_credentials:
        mock_credentials.return_value = "credentials"
        conn = _generate_test_connection(
            ca_pem="ca-secret", crt_pem="crt-secret", key_pem="key-secret"
        )
        conn._build_channel()

        mock_credentials.assert_called_once_with(
            root_certificates=b"ca-secret",
            private_key=b"key-secret",
            certificate_chain=b"crt-secret",
        )
        mock_secure_channel.assert_called_once_with(
            SERVER_TARGET,
            "credentials",
            options=(("grpc.ssl_target_name_override", "ank-server"),),
        )


def test_grpc_target_strips_url_scheme():
    """
    Test that _grpc_target() strips a http(s):// scheme prefix from
    server_url, since grpc's channel target must be a bare host:port.
    A server_url given without a scheme is passed through unchanged.
    """
    conn = _generate_test_connection()

    conn._server_url = "http://127.0.0.1:25551"
    assert conn._grpc_target() == "127.0.0.1:25551"

    conn._server_url = "https://127.0.0.1:25551"
    assert conn._grpc_target() == "127.0.0.1:25551"

    conn._server_url = "127.0.0.1:25551"
    assert conn._grpc_target() == "127.0.0.1:25551"


def test_request_iterator():
    """
    Test that _request_iterator() yields exactly the queued messages,
    in order.
    """
    conn = _generate_test_connection()
    conn._write_queue.put("message_1")
    conn._write_queue.put("message_2")

    iterator = conn._request_iterator()
    assert next(iterator) == "message_1"
    assert next(iterator) == "message_2"


def test_handle_from_server_generic_response():
    """
    Test that a generic response is forwarded via add_response_callback.
    """
    conn = _generate_test_connection()
    ank_base_response = _ank_base.Response(
        requestId="1122",
        error=_ank_base.Error(message="Test error message"),
    )
    conn._handle_from_server(
        _grpc_api.FromServer(response=ank_base_response)
    )
    conn._add_response_callback.assert_called_once()
    response = conn._add_response_callback.call_args[0][0]
    assert response.get_request_id() == "1122"
    conn._add_log_callback.assert_not_called()
    conn._add_event_callback.assert_not_called()


def test_handle_from_server_log_entries():
    """
    Test that a log entries response is forwarded via
    add_log_callback.
    """
    conn = _generate_test_connection()
    ank_base_response = _ank_base.Response(
        requestId="1122",
        logEntriesResponse=_ank_base.LogEntriesResponse(
            logEntries=[generate_test_log_entry()]
        ),
    )
    conn._handle_from_server(
        _grpc_api.FromServer(response=ank_base_response)
    )
    conn._add_log_callback.assert_called_once()
    request_id, content = conn._add_log_callback.call_args[0]
    assert request_id == "1122"
    assert len(content) == 1
    conn._add_response_callback.assert_not_called()


def test_handle_from_server_logs_stop_response():
    """
    Test that a logs stop response is forwarded via add_log_callback.
    """
    conn = _generate_test_connection()
    ank_base_response = _ank_base.Response(
        requestId="1122",
        logsStopResponse=generate_test_logs_stop_reponse(),
    )
    conn._handle_from_server(
        _grpc_api.FromServer(response=ank_base_response)
    )
    conn._add_log_callback.assert_called_once()
    conn._add_response_callback.assert_not_called()


def test_handle_from_server_event_response():
    """
    Test that an event response is forwarded via add_event_callback.
    """
    conn = _generate_test_connection()
    ank_base_response = _ank_base.Response(
        requestId="1122",
        completeStateResponse=_ank_base.CompleteStateResponse(
            completeState=_ank_base.CompleteState(
                desiredState=_ank_base.State(apiVersion="v1"),
            ),
            alteredFields=_ank_base.AlteredFields(
                addedFields=["desiredState.workloads.test"],
            ),
        ),
    )
    conn._handle_from_server(
        _grpc_api.FromServer(response=ank_base_response)
    )
    conn._add_event_callback.assert_called_once()
    request_id, content = conn._add_event_callback.call_args[0]
    assert request_id == "1122"
    assert content.added_fields == ["desiredState.workloads.test"]
    conn._add_response_callback.assert_not_called()


def test_handle_from_server_ignores_non_response_messages():
    """
    Test that non-response messages (serverHello, or anything else
    targeted at agents rather than commanders) are ignored, without
    raising or forwarding anything.
    """
    conn = _generate_test_connection()

    conn._handle_from_server(
        _grpc_api.FromServer(serverHello=_grpc_api.ServerHello())
    )
    conn._handle_from_server(
        _grpc_api.FromServer(updateWorkload=_grpc_api.UpdateWorkload())
    )
    conn._handle_from_server(_grpc_api.FromServer())

    conn._add_response_callback.assert_not_called()
    conn._add_log_callback.assert_not_called()
    conn._add_event_callback.assert_not_called()


def test_read_from_grpc_stops_on_terminated_state():
    """
    Test that the reader loop returns without attempting a reconnect
    if the connection was terminated (disconnect() was called), and
    logs the resulting RpcError at debug level, since it's the
    expected result of disconnect()'s own call.cancel().
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.TERMINATED
    conn._logger = MagicMock()
    fake_call = _FakeCall(error=grpc.RpcError("boom"))

    with patch.object(conn, "_reconnect") as mock_reconnect:
        conn._read_from_grpc(fake_call)
        mock_reconnect.assert_not_called()

    conn._logger.debug.assert_called_once()
    conn._logger.warning.assert_not_called()


def test_read_from_grpc_reconnects_on_lost_connection():
    """
    Test that the reader loop attempts a reconnect (via the real
    _reconnect logic) when the stream errors while the connection is
    still expected to be up, logging the RpcError as a warning (since
    this is an unexpected drop, not one caused by disconnect()), and
    resumes reading from the newly reconnected call.
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.CONNECTED
    conn._logger = MagicMock()
    first_call = _FakeCall(error=grpc.RpcError("boom"))
    second_call = _FakeCall()

    with patch.object(
        GrpcConnection, "RECONNECT_INTERVAL", 0.01
    ), patch.object(conn, "_open_stream", return_value=second_call):
        reader_thread = threading.Thread(
            target=conn._read_from_grpc, args=(first_call,), daemon=True
        )
        reader_thread.start()
        reader_thread.join(timeout=1)

    assert conn._state == GrpcConnectionState.CONNECTED
    conn._logger.warning.assert_any_call(
        "Error while reading from the gRPC connection: '%s'",
        first_call._error,
    )
    conn._logger.debug.assert_not_called()

    second_call.cancel()
    reader_thread.join(timeout=1)


def test_reconnect_gives_up_when_terminated():
    """
    Test that _reconnect() gives up (returns None) as soon as it
    notices the connection was terminated, without attempting to
    reopen the stream.
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.TERMINATED

    with patch.object(
        GrpcConnection, "RECONNECT_INTERVAL", 0.01
    ), patch.object(conn, "_open_stream") as mock_open_stream:
        result = conn._reconnect()
        assert result is None
        mock_open_stream.assert_not_called()


def test_reconnect_retries_until_success():
    """
    Test that _reconnect() retries opening the stream until it
    succeeds, and updates the state back to CONNECTED.
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.RECONNECTING
    fake_call = _FakeCall()

    attempts = [ConnectionException("still down"), fake_call]

    def _fake_open_stream():
        attempt = attempts.pop(0)
        if isinstance(attempt, Exception):
            raise attempt
        return attempt

    with patch.object(
        GrpcConnection, "RECONNECT_INTERVAL", 0.01
    ), patch.object(conn, "_open_stream", side_effect=_fake_open_stream):
        result = conn._reconnect()

    assert result is fake_call
    assert conn._state == GrpcConnectionState.CONNECTED


def test_read_from_grpc_dispatches_messages():
    """
    Test that messages read from the bidi call are dispatched via
    _handle_from_server while the reader loop is running.
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.CONNECTED
    fake_call = _FakeCall(
        messages=[_grpc_api.FromServer(serverHello=_grpc_api.ServerHello())]
    )
    reader_thread = threading.Thread(
        target=conn._read_from_grpc, args=(fake_call,), daemon=True
    )
    reader_thread.start()
    time.sleep(0.05)

    conn._state = GrpcConnectionState.TERMINATED
    fake_call.cancel()
    reader_thread.join(timeout=1)
    assert not reader_thread.is_alive()


def test_read_from_grpc_stops_when_reconnect_gives_up():
    """
    Test that the reader loop returns once _reconnect() gives up
    (returns None), without looping forever.
    """
    conn = _generate_test_connection()
    conn._state = GrpcConnectionState.CONNECTED
    fake_call = _FakeCall(error=grpc.RpcError("boom"))

    with patch.object(conn, "_reconnect", return_value=None):
        conn._read_from_grpc(fake_call)


def test_disconnect_logs_error_when_reader_thread_does_not_stop():
    """
    Test that disconnect() logs an error if the reader thread does
    not stop within the join timeout.
    """
    fake_call = _FakeCall()
    stub_instance, _ = _mock_stub(lambda: fake_call)

    with patch(
        "ankaios_sdk._components.connection.grpc_interface."
        "_grpc_api_grpc.CommandConnectionStub"
    ) as mock_stub_cls, patch("grpc.insecure_channel") as mock_channel, patch(
        "grpc.channel_ready_future"
    ) as mock_ready, patch("threading.Thread") as mock_thread:
        mock_stub_cls.return_value = stub_instance
        mock_channel.return_value = MagicMock()
        mock_ready.return_value = MagicMock(
            result=MagicMock(return_value=None)
        )
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        conn = _generate_test_connection()
        conn._logger = MagicMock()
        conn.connect()
        conn.disconnect()

        mock_thread_instance.join.assert_called_once_with(timeout=2)
        conn._logger.error.assert_called_once_with(
            "Reader thread did not stop."
        )
