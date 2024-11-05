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
This module contains unit tests for the utils methods.
"""

import logging
from ankaios_sdk.utils import get_logger


def test_get_logger():
    """
    Test the get_logger method.
    """
    logger = get_logger("test_logger")
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert len(logger.handlers) == 1

    # Creating another with the same name should not add more handlers
    logger = get_logger("test_logger")
    assert len(logger.handlers) == 1
