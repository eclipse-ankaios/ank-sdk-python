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
This module initializes the connection package by importing the
Connection abstraction and its interface implementations.

Imports
-------

- Connection component:
    the abstract base class for a connection to Ankaios.
- ControlInterfaceConnection component:
    the control interface (named pipes) implementation of Connection.
- CommandInterfaceConnection component:
    the command interface (gRPC server interface) implementation of
    Connection. Only available if the 'grpc' extra is installed.
"""

from .connection import *
from .control_interface import *

try:
    from .command_interface import *
except ImportError:
    # The 'grpc' extra is not installed; CommandInterfaceConnection
    # stays unavailable, but the rest of the SDK must still work.
    pass

__all__ = [name for name in globals() if not name.startswith("_")]
