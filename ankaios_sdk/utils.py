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
This script provides general functionality and constants for the ankaios_sdk.

Enums
-----

- AnkaiosLogLevel:
    Represents the log levels for the Ankaios class.

Functions
---------

- get_logger:
    Creates and returns the logger.
"""

import logging
from enum import Enum
import threading


SUPPORTED_API_VERSION = "v0.1"
"(str): The supported API version of the Ankaios SDK."

ANKAIOS_VERSION = "0.5.0"
"(str): The version of the compatible Ankaios."

WORKLOADS_PREFIX = "desiredState.workloads"
"(str): The prefix for the workloads in the desired state."

CONFIGS_PREFIX = "desiredState.configs"
"(str): The prefix for the configs in the desired state."

DEFAULT_CONTROL_INTERFACE_PATH = "/run/ankaios/control_interface"
"(str): The base path for the Ankaios control interface."


# Used to sync across different threads when adding handlers
_logger_lock = threading.Lock()


class AnkaiosLogLevel(Enum):
    """ Ankaios log levels. """
    ERROR = logging.ERROR
    "(int): Error log level."
    WARN = logging.WARN
    "(int): Warning log level."
    INFO = logging.INFO
    "(int): Info log level."
    DEBUG = logging.DEBUG
    "(int): Debug log level."


def get_logger(name="Ankaios logger"):
    """
    Returns a configured logger with a custom format.

    Args:
        name (str): The name of the logger.
    """
    logger = logging.getLogger(name)

    with _logger_lock:
        if not any(isinstance(handler, logging.StreamHandler)
                   for handler in logger.handlers):
            formatter = logging.Formatter(
                '%(asctime)s %(message)s', datefmt="[%F %T]"
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    return logger
