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
This module contains the ankaios_sdk protobuf components.
It contains the proto files and the generated protobuf classes.

Imports
-------

- ank_base_pb2:
    Used for general grpc messages.
- control_api_pb2:
    Used for exchanging messages with the control interface.
"""

try:
    import ankaios_sdk._protos.ank_base_pb2 as _ank_base
    import ankaios_sdk._protos.control_api_pb2 as _control_api
except ImportError as r:
    raise r

__all__ = ["_ank_base", "_control_api"]
