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
This script defines the CommandInterfaceConnection class, implementing the
Connection abstraction over a direct gRPC connection to the Ankaios
server, used to connect to Ankaios from outside a workload.

Classes
-------

- :class:`CommandInterfaceConnection`:
    Handles the interaction with Ankaios over gRPC.

Enums
-----

- :class:`CommandInterfaceState`:
    Represents the state of the gRPC connection.

Usage
-----

- Create a CommandInterfaceConnection instance, connect and disconnect.
    .. code-block:: python

        conn = CommandInterfaceConnection(
            "http://127.0.0.1:25551", <callbacks from Ankaios>
        )
        conn.connect()
        ...
        conn.disconnect()
"""


__all__ = ["CommandInterfaceConnection", "CommandInterfaceState"]


import queue
import threading
import time
from enum import Enum
from typing import Callable, Optional

import grpc

from ..._protos import grpc_api_pb2 as _grpc_api
from ..._protos import grpc_api_pb2_grpc as _grpc_api_grpc
from ...exceptions import ConnectionException
from ...utils import ANKAIOS_VERSION
from ..request import Request
from ..response import Response
from .connection import Connection


class CommandInterfaceState(Enum):
    """The state of the gRPC connection."""

    INITIALIZED = 1
    "(int): The connection was initialized but not yet accepted."
    CONNECTED = 2
    "(int): The connection is established."
    TERMINATED = 3
    "(int): The connection is terminated."
    RECONNECTING = 4
    "(int): A lost connection is being retried."

    def __str__(self) -> str:
        """
        Returns the string representation of the state.

        :returns: The state as a string.
        :rtype: str
        """
        return self.name


# pylint: disable=too-many-instance-attributes
class CommandInterfaceConnection(Connection):
    """
    This class handles the interaction with an Ankaios server over the
    command interface: a direct gRPC connection to the server,
    playing the commander role via the CommandConnection service.

    The initial :func:`connect` attempt is never retried. Once a
    connection has been established, losing it is treated as
    transient: it is retried every ``RECONNECT_INTERVAL`` seconds
    until it succeeds or :func:`disconnect` is called.
    """

    RECONNECT_INTERVAL = 0.5
    "(float): Seconds to wait between reconnect attempts."
    CHANNEL_READY_TIMEOUT = 5.0
    "(float): Seconds to wait for a single (re)connect attempt."
    SERVER_TLS_NAME = "ank-server"
    "(str): The domain name Ankaios server certificates are issued for."

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(
        self,
        server_url: str,
        add_response_callback: Callable,
        add_log_callback: Callable,
        add_event_callback: Callable,
        *,
        ca_pem: Optional[str] = None,
        crt_pem: Optional[str] = None,
        key_pem: Optional[str] = None,
    ) -> None:
        """
        Initialize the CommandInterfaceConnection object. This is used to
        interact with an Ankaios server directly over the command interface.

        If none of ca_pem, crt_pem and key_pem are provided, the
        connection is a plaintext (insecure) one. If all three are
        provided, the connection is mTLS-secured. Providing only
        some of them is invalid.

        :param server_url: The URL of the Ankaios server, e.g.
            "http://127.0.0.1:25551" (insecure) or
            "https://127.0.0.1:25551" (mTLS-secured).
        :type server_url: str
        :param add_response_callback: The callback function to add
            a response to the Ankaios class.
        :type add_response_callback: Callable
        :param add_log_callback: The callback function to add
            a log to the Ankaios class.
        :type add_log_callback: Callable
        :param add_event_callback: The callback function to add
            an event to the Ankaios class.
        :type add_event_callback: Callable
        :param ca_pem: The PEM-encoded CA certificate content.
        :type ca_pem: Optional[str]
        :param crt_pem: The PEM-encoded client certificate content.
        :type crt_pem: Optional[str]
        :param key_pem: The PEM-encoded client private key content.
        :type key_pem: Optional[str]

        :raises ValueError: If only some of ca_pem, crt_pem and
            key_pem are provided.
        """
        provided = (
            ca_pem is not None,
            crt_pem is not None,
            key_pem is not None,
        )
        if any(provided) and not all(provided):
            raise ValueError(
                "ca_pem, crt_pem and key_pem must all be provided "
                "together for a secured connection, or all omitted "
                "for an insecure connection."
            )
        super().__init__(
            add_response_callback, add_log_callback, add_event_callback
        )
        self._server_url = server_url
        self._ca_pem = ca_pem
        self._crt_pem = crt_pem
        self._key_pem = key_pem

        # The state of the connection must not be changed directly.
        self._state_value = CommandInterfaceState.TERMINATED
        self._state_lock = threading.Lock()
        self._channel: Optional[grpc.Channel] = None
        self._call = None
        self._write_queue: "queue.Queue" = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None

    @property
    def _state(self) -> CommandInterfaceState:
        """
        Get the current state of the connection.

        :returns: The current state.
        :rtype: CommandInterfaceState
        """
        with self._state_lock:
            return self._state_value

    @_state.setter
    def _state(self, value: CommandInterfaceState) -> None:
        """
        Set the current state of the connection.

        :param value: The new state to set.
        :type value: CommandInterfaceState
        """
        with self._state_lock:
            self._state_value = value

    @property
    def connected(self) -> bool:
        """
        Check if the gRPC connection is established.

        :returns: True if connected, False otherwise.
        :rtype: bool
        """
        return self._state == CommandInterfaceState.CONNECTED

    def connect(self) -> None:
        """
        Establish the gRPC connection to the Ankaios server.

        This attempt is never retried by this method; once
        established, a later lost connection is retried
        transparently every ``RECONNECT_INTERVAL`` seconds.

        :raises ConnectionException: If already connected, or if
            the connection could not be established.
        """
        if self._state in (
            CommandInterfaceState.INITIALIZED,
            CommandInterfaceState.CONNECTED,
            CommandInterfaceState.RECONNECTING,
        ):
            raise ConnectionException("Already connected.")

        # Only change the state once past the point where connecting
        # can still fail, so a failed attempt leaves the connection
        # exactly as it was and free to retry via a plain connect().
        call = self._open_stream()
        self._state = CommandInterfaceState.INITIALIZED

        self._reader_thread = threading.Thread(
            target=self._read_from_grpc, args=(call,), daemon=True
        )
        self._reader_thread.start()
        self._state = CommandInterfaceState.CONNECTED
        self._logger.debug("Connected to the Ankaios server over gRPC.")

    def disconnect(self) -> None:
        """
        Disconnect from the gRPC connection.
        """
        if self._state == CommandInterfaceState.TERMINATED:
            self._logger.debug("Already disconnected.")
            return

        self._logger.debug("Disconnecting..")
        self._state = CommandInterfaceState.TERMINATED
        if self._call is not None:
            self._call.cancel()
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2)
            if self._reader_thread.is_alive():
                self._logger.error("Reader thread did not stop.")
            self._reader_thread = None
        if self._channel is not None:
            self._channel.close()
            self._channel = None
        self._call = None

    def write_request(self, request: Request) -> None:
        """
        Sends the request through the gRPC connection.

        :param request: The request object to be written.
        :type request: Request

        :raises ConnectionException: If not connected.
        """
        if self._state != CommandInterfaceState.CONNECTED:
            self._logger.error(
                "Could not write to the gRPC connection, not connected."
            )
            raise ConnectionException(
                "Could not write to the gRPC connection, not connected."
            )
        self._write_queue.put(_grpc_api.ToServer(request=request._to_proto()))

    # grpc's channel target is a bare host:port (or a resolver-prefixed
    # target such as "dns:///host:port") -- it does not understand a
    # http(s):// URL scheme. server_url is documented (and accepted)
    # as a full URL, so the scheme is stripped here rather than
    # pushing this onto every caller.
    _URL_SCHEME_PREFIXES = ("http://", "https://")

    def _grpc_target(self) -> str:
        """
        Returns server_url as a bare host:port gRPC channel target.

        :returns: The channel target.
        :rtype: str
        """
        for prefix in self._URL_SCHEME_PREFIXES:
            if self._server_url.startswith(prefix):
                return self._server_url[len(prefix):]
        return self._server_url

    def _build_channel(self) -> grpc.Channel:
        """
        Builds the (optionally mTLS-secured) gRPC channel used to
        reach the Ankaios server.

        :returns: The gRPC channel.
        :rtype: grpc.Channel
        """
        target = self._grpc_target()
        if self._ca_pem is None:
            return grpc.insecure_channel(target)

        credentials = grpc.ssl_channel_credentials(
            root_certificates=self._ca_pem.encode(),
            private_key=self._key_pem.encode(),
            certificate_chain=self._crt_pem.encode(),
        )
        # Ankaios server certificates are always issued for this
        # domain name, regardless of the actual connection address.
        options = (("grpc.ssl_target_name_override", self.SERVER_TLS_NAME),)
        return grpc.secure_channel(target, credentials, options=options)

    def _open_stream(self):
        """
        Builds the gRPC channel, sends the initial CommanderHello and
        opens the ConnectCommand bidi stream. Used both for the
        initial connect and for every reconnect attempt.

        :returns: The opened bidi call, iterable for FromServer
            messages.
        :rtype: grpc.Call

        :raises ConnectionException: If the channel does not become
            ready in time, or the stream could not be opened.
        """
        try:
            channel = self._build_channel()
            grpc.channel_ready_future(channel).result(
                timeout=self.CHANNEL_READY_TIMEOUT
            )
        except (grpc.FutureTimeoutError, grpc.RpcError) as e:
            raise ConnectionException(
                f"Could not connect to the Ankaios server: '{e}'"
            ) from e

        stub = _grpc_api_grpc.CommandConnectionStub(channel)
        self._write_queue = queue.Queue()
        self._write_queue.put(
            _grpc_api.ToServer(
                commanderHello=_grpc_api.CommanderHello(
                    protocolVersion=str(ANKAIOS_VERSION)
                )
            )
        )

        call = stub.ConnectCommand(self._request_iterator())
        self._channel = channel
        self._call = call
        return call

    def _request_iterator(self):
        """
        Generator yielding ToServer messages queued via
        :func:`write_request` (and the initial hello), until
        :func:`disconnect` cancels the call.
        """
        write_queue = self._write_queue
        while True:
            yield write_queue.get()

    def _read_from_grpc(self, call) -> None:
        """
        Reads continuously from the gRPC bidi stream. This is meant
        to be run in a separate thread. If the connection is lost
        after having been established, it is retried every
        ``RECONNECT_INTERVAL`` seconds until it succeeds or
        :func:`disconnect` is called.

        :param call: The bidi call to read FromServer messages from.
        """
        while True:
            try:
                for from_server in call:
                    self._handle_from_server(from_server)
            except grpc.RpcError as e:
                if self._state == CommandInterfaceState.TERMINATED:
                    # disconnect() already cancelled the call itself;
                    # this is the expected, self-inflicted result.
                    self._logger.debug(
                        "gRPC connection cancelled by disconnect(): '%s'", e
                    )
                    return
                self._logger.warning(
                    "Error while reading from the gRPC connection: '%s'",
                    e,
                )
            else:
                # The stream ended without an error; still need to know
                # whether that was disconnect()'s doing before retrying.
                if self._state == CommandInterfaceState.TERMINATED:
                    return

            self._state = CommandInterfaceState.RECONNECTING
            self._logger.warning(
                "Lost connection to the Ankaios server, attempting to "
                "reconnect every %ss..",
                self.RECONNECT_INTERVAL,
            )
            call = self._reconnect()
            if call is None:
                return

    def _reconnect(self):
        """
        Retries opening the gRPC stream every ``RECONNECT_INTERVAL``
        seconds until it succeeds or :func:`disconnect` is called.

        :returns: The newly opened call, or None if disconnect() was
            called while reconnecting.
        :rtype: Optional[grpc.Call]
        """
        while True:
            time.sleep(self.RECONNECT_INTERVAL)
            if self._state == CommandInterfaceState.TERMINATED:
                return None
            try:
                call = self._open_stream()
            except ConnectionException as e:
                self._logger.debug("Reconnect attempt failed: '%s'", e)
                continue
            self._state = CommandInterfaceState.CONNECTED
            self._logger.info("Reconnected to the Ankaios server.")
            return call

    def _handle_from_server(self, from_server) -> None:
        """
        Handles a decoded FromServer message and dispatches to the
        appropriate callback.

        :param from_server: The decoded FromServer message.
        """
        response_type = from_server.WhichOneof("FromServerEnum")
        if response_type == "response":
            response = Response._from_ank_base_response(from_server.response)
            self._dispatch_response(response)
        elif response_type == "serverHello":
            self._logger.debug("Received server hello.")
        else:
            self._logger.warning(
                "Received unexpected message from the Ankaios server: '%s'",
                response_type,
            )
