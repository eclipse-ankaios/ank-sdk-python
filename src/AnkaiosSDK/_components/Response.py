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

from typing import Union
from threading import Event
from .._protos import _ank_base, _control_api
from .CompleteState import CompleteState
from .Workload import Workload


__all__ = ["Response", "ResponseEvent"]


class Response:
    def __init__(self, message_buffer: bytes) -> None:
        """Initialize the Response object with the received message buffer."""
        self.buffer = message_buffer
        self._response = None
        self.content_type = None
        self.content = None

        self._parse_response()
        self._from_proto()

    def _parse_response(self) -> None:
        from_ankaios = _control_api.FromAnkaios()
        try:
            # Deserialize the received proto msg
            from_ankaios.ParseFromString(self.buffer)
        except Exception as e:
            raise ValueError(f"Invalid response, parsing error: '{e}'")
        self._response = from_ankaios.response

    def _from_proto(self) -> None:
        """
        Convert the proto message to a Response object.
        This can be either an error, a complete state, or an update state success.
        """
        if self._response.HasField("error"):
            self.content_type = "error"
            self.content = self._response.error.message
        elif self._response.HasField("completeState"):
            self.content_type = "complete_state"
            self.content = CompleteState()
            self.content._from_proto(self._response.completeState)
        elif self._response.HasField("UpdateStateSuccess"):
            self.content_type = "update_state_success"
            self.content = {
                "added_workloads": self._response.UpdateStateSuccess.addedWorkloads,
                "deleted_workloads": self._response.UpdateStateSuccess.deletedWorkloads,
            }
        else:
            raise ValueError("Invalid response type.")

    def get_request_id(self) -> str:
        """Get the request_id of the response."""
        return self._response.requestId

    def check_request_id(self, request_id: str) -> bool:
        """Check if the request_id of the response matches the given request_id."""
        return self._response.requestId == request_id

    def get_content(self) -> tuple[str, Union[str, CompleteState, dict]]:
        """Get the content of the response."""
        return (self.content_type, self.content)


class ResponseEvent(Event):
    def __init__(self, response: Response = None) -> None:
        super().__init__()
        self._response = response

    def set_response(self, response: Response) -> None:
        """Set the response."""
        self._response = response
        self.set()

    def get_response(self) -> Response:
        """Get the response."""
        return self._response

    def wait_for_response(self, timeout: int) -> Response:
        """Wait for the response."""
        if not self.wait(timeout):
            raise TimeoutError("Timeout while waiting for the response.")
        return self.get_response()


if __name__ == "__main__":
    complete_state = CompleteState()

    # Create workload
    workload = Workload(
        agent_name="agent_A"
    )

    # Add workload to complete state
    complete_state.set_workload("dynamic_nginx", workload)
    complete_state.set_workload("dynamic_nginx2", workload)


    from_ankaios = _control_api.FromAnkaios(
        response=_ank_base.Response(
            requestId="1234",
            completeState=complete_state._to_proto()
        )
    )

    response = Response(from_ankaios.SerializeToString())
    print(response.get_request_id())
    (content_type, content) = response.get_content()
    print(content_type)
    print(content)

    if response.check_request_id("1234"):
        print("Request ID matches")