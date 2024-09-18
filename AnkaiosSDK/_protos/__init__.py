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

# TODO remove this line after the issue is fixed
# https://github.com/grpc/grpc/issues/37609
# https://github.com/protocolbuffers/protobuf/issues/18096
import warnings
warnings.filterwarnings("ignore", ".*obsolete", UserWarning, "google.protobuf.runtime_version")

try:
    import AnkaiosSDK._protos.ank_base_pb2 as _ank_base
    import AnkaiosSDK._protos.control_api_pb2 as _control_api
except ImportError as r:
    raise r

__all__ = ["_ank_base", "_control_api"]
