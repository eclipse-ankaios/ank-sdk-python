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
This script defines the exceptions used in the ankaios_sdk module.

All the exceptions are derived from the AnkaiosException class.

Exceptions
----------
- AnkaiosException: Base exception.
- WorkloadFieldException: Raised when the workload field is invalid.
- WorkloadBuilderException: Raised when the workload builder is invalid.
- InvalidManifestException: Raised when the manifest file is invalid.
- ConnectionClosedException: Raised when the connection is closed.
- ResponseException: Raised when the response is invalid.
- ControlInterfaceException: Raised when an operation fails.
- AnkaiosProtocolException: Raised when something unexpected is received.
- AnkaiosResponseError: Raised when the response from Ankaios is an error.
"""

import inspect

__all__ = [
    "AnkaiosException",
    "WorkloadFieldException",
    "WorkloadBuilderException",
    "InvalidManifestException",
    "ConnectionClosedException",
    "ResponseException",
    "ControlInterfaceException",
    "AnkaiosProtocolException",
    "AnkaiosResponseError",
]


class AnkaiosException(Exception):
    """Base class for exceptions in this module."""


class WorkloadFieldException(AnkaiosException):
    """Raised when the workload field is invalid"""

    def __init__(self, field: str, value: str, accepted_values: list) -> None:
        message = f'Invalid value for {field}: "{value}".'
        message += "Accepted values are: " + ", ".join(accepted_values)
        super().__init__(message)


class WorkloadBuilderException(AnkaiosException):
    """Raised when the workload builder is invalid."""


class InvalidManifestException(AnkaiosException):
    """Raised when the manifest file is invalid."""


class ConnectionClosedException(AnkaiosException):
    """Raised when the connection is closed."""


class ResponseException(AnkaiosException):
    """Raised when the response is invalid."""


class ControlInterfaceException(AnkaiosException):
    """Raised when an operation on the Control Interface fails"""


class AnkaiosProtocolException(AnkaiosException):
    """Raised when something unexpected is received"""

    def __init__(self, message):
        function_name = inspect.stack()[1].function
        super().__init__(f"{function_name}: {message}")


class AnkaiosResponseError(AnkaiosException):
    """Raised when the response from Ankaios is an error"""
