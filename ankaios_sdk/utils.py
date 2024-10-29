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
"""

import logging
from enum import Enum


SUPPORTED_API_VERSION = "v0.1"
ANKAIOS_VERSION = "0.5.0"
WORKLOADS_PREFIX = "desiredState.workloads"
CONFIGS_PREFIX = "desiredState.configs"


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

    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s %(message)s', datefmt="%FT%TZ"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
