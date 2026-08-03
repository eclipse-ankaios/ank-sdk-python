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
This script defines the Connection abstract base class, which specifies
the common interface implemented by every way this SDK can talk to
Ankaios (the control interface, used from inside a workload, or a
direct gRPC connection to the Ankaios server, used from outside a
workload).

Classes
-------

- :class:`Connection`:
    Abstract base class for a connection to Ankaios.

Enums
-----

- :class:`ConnectionType`:
    Represents which connection the Ankaios class should use.
"""


__all__ = ["Connection", "ConnectionType"]


from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable

from ...utils import get_logger
from ..request import Request


class ConnectionType(Enum):
    """Represents which connection the Ankaios class should use."""

    CONTROL_INTERFACE = 1
    "(int): Connect via the control interface (named pipes)."
    COMMAND_INTERFACE = 2
    "(int): Connect via the command interface (direct gRPC)."

    def __str__(self) -> str:
        """
        Returns the string representation of the connection type.

        :returns: The connection type as a string.
        :rtype: str
        """
        return self.name


class Connection(ABC):
    """
    Abstract base class that defines the common interface for every
    connection to Ankaios, so that the :class:`Ankaios` class can work
    identically regardless of which connection implementation is used.
    """

    def __init__(
        self,
        add_response_callback: Callable,
        add_log_callback: Callable,
        add_event_callback: Callable,
    ) -> None:
        """
        Stores the callbacks shared by every connection implementation
        for forwarding responses, logs and events to the Ankaios class.

        :param add_response_callback: The callback function to add
            a response to the Ankaios class.
        :type add_response_callback: Callable
        :param add_log_callback: The callback function to add
            a log to the Ankaios class.
        :type add_log_callback: Callable
        :param add_event_callback: The callback function to add
            an event to the Ankaios class.
        :type add_event_callback: Callable
        """
        self._add_response_callback = add_response_callback
        self._add_log_callback = add_log_callback
        self._add_event_callback = add_event_callback
        self._logger = get_logger()

    @property
    @abstractmethod
    def connected(self) -> bool:
        """
        Check if the connection is established.

        :returns: True if connected, False otherwise.
        :rtype: bool
        """

    @abstractmethod
    def connect(self) -> None:
        """
        Establish the connection.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """
        Tear down the connection.
        """

    @abstractmethod
    def write_request(self, request: Request) -> None:
        """
        Send a request through the connection.

        :param request: The request object to be sent.
        :type request: Request
        """
