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

import uuid
from .._protos import _ank_base
from .CompleteState import CompleteState


__all__ = ["Request"]


class Request:
    def __init__(self, request_type: str) -> None:
        self._request = _ank_base.Request()
        self._request.requestId = str(uuid.uuid4())
        self._request_type = request_type

        if request_type not in ["update_state", "get_state"]:
            raise ValueError("Invalid request type. Supported values: 'update_state', 'get_state'.")

    def __str__(self) -> str:
        return str(self._to_proto())

    def _get_id(self) -> str:
        """Get the request ID."""
        return self._request.requestId

    def set_complete_state(self, complete_state: CompleteState) -> None:
        """Set the complete state for the request."""
        if self._request_type != "update_state":
            raise ValueError("Complete state can only be set for an update state request.")

        self._request.updateStateRequest.newState.CopyFrom(complete_state._to_proto())

    def add_mask(self, mask: str) -> None:
        """Set the update mask for the request."""
        if self._request_type == "update_state":
            self._request.updateStateRequest.updateMask.append(mask)
        elif self._request_type == "get_state":
            self._request.completeStateRequest.fieldMask.append(mask)
        else:
            raise ValueError("Invalid request type.")

    def _to_proto(self) -> _ank_base.Request:
        """Convert the Request object to a proto message."""
        return self._request


if __name__ == "__main__":
    request_update = Request(request_type="update_state")

    # Create the CompleteState object
    complete_state = CompleteState()
    request_update.set_complete_state(complete_state)
    print(request_update)

    request_get = Request(request_type="get_state")
    print(request_get)
