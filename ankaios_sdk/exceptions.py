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

Exceptions
----------
- WorkloadFieldException: Raised when the workload field is invalid.
- WorkloadBuilderException: Raised when the workload builder is invalid.
- InvalidManifestException: Raised when the manifest file is invalid.
- ConnectionClosedException: Raised when the connection is closed.
- RequestException: Raised when the request is invalid.
- ResponseException: Raised when the response is invalid.
- ControlInterfaceException: Raised when an operation on the connection fails.
- AnkaiosException: Raised when an update operation fails.
"""

import inspect

__all__ = ['WorkloadFieldException', 'WorkloadBuilderException',
           'InvalidManifestException', 'ConnectionClosedException',
           'RequestException', 'ResponseException',
           'ControlInterfaceException', 'AnkaiosException']


class AnkaiosBaseException(Exception):
    """Base class for exceptions in this module."""


class WorkloadFieldException(AnkaiosBaseException):
    """Raised when the workload field is invalid"""
    def __init__(self, field: str, value: str, accepted_values: list) -> None:
        message = f"Invalid value for {field}: \"{value}\"."
        message += "Accepted values are: " + ", ".join(accepted_values)
        super().__init__(message)


class WorkloadBuilderException(AnkaiosBaseException):
    """Raised when the workload builder is invalid."""


class InvalidManifestException(AnkaiosBaseException):
    """Raised when the manifest file is invalid."""


class ConnectionClosedException(AnkaiosBaseException):
    """Raised when the connection is closed."""


class RequestException(AnkaiosBaseException):
    """Raised when the request is invalid."""


class ResponseException(AnkaiosBaseException):
    """Raised when the response is invalid."""


class ControlInterfaceException(AnkaiosBaseException):
    """Raised when an operation on the Control Interface fails"""


class AnkaiosException(AnkaiosBaseException):
    """Raised when an update operation fails."""
    def __init__(self, message):
        function_name = inspect.stack()[1].function
        super().__init__(f"{function_name}: {message}")
