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

import os
import configparser


SUPPORTED_API_VERSION = "v0.1"
WORKLOADS_PREFIX = "desiredState.workloads"
CONFIGS_PREFIX = "desiredState.configs"

_config = configparser.ConfigParser()
_config.read(os.path.join(os.path.dirname(__file__), '..', 'setup.cfg'))
ANKAIOS_VERSION = _config['metadata']['ankaios_version']
