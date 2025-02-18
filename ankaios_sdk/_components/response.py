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
This script defines the Response and UpdateStateSuccess classes,
used for receiving messages from the control interface.

Classes
--------

- Response:
    Represents a response from the control interface.
- UpdateStateSuccess:
    Represents a response for a successful update state request.

Enums
-----

- ResponseType:
    Enumeration for the different types of response. It includes
    ERROR, COMPLETE_STATE, and UPDATE_STATE_SUCCESS and CONNECTION_CLOSED.

Usage
------

- Get response content:
    .. code-block:: python

        response = Response()
        (content_type, content) = response.get_content()

- Check if the request_id matches:
    .. code-block:: python

        response = Response()
        if response.check_request_id("1234"):
            print("Request ID matches")

- Convert the update state success to a dictionary:
    .. code-block:: python

        update_state_success = UpdateStateSuccess()
        update_state_success.to_dict()
"""

__all__ = ["Response", "ResponseType", "UpdateStateSuccess"]

from typing import Union
from enum import Enum
from .._protos import _control_api
from ..exceptions import ResponseException
from ..utils import get_logger
from .complete_state import CompleteState
from .workload_state import WorkloadInstanceName


logger = get_logger()


class Response:
    """
    Represents a response received from the Ankaios system.

    Attributes:
        buffer (bytes): The received message buffer.
        content_type (str): The type of the response content
            (e.g., "error", "complete_state", "update_state_success").
        content: The content of the response, which can be a string,
            CompleteState, or UpdateStateSuccess.
    """
    def __init__(self, message_buffer: bytes) -> None:
        """
        Initializes the Response object with the received message buffer.

        Args:
            message_buffer (bytes): The received message buffer.
        """
        self.buffer = message_buffer
        self._response = None
        self.content_type = None
        self.content = None

        self._parse_response()

    def _parse_response(self) -> None:
        """
        Parses the received message buffer into a protobuf response message.

        Raises:
            ResponseException: If there is an error parsing the message buffer.
        """
        from_ankaios = _control_api.FromAnkaios()
        try:
            # Deserialize the received proto msg
            from_ankaios.ParseFromString(self.buffer)
        except Exception as e:
            logger.error(
                "Error parsing the received message: %s", e
            )
            raise ResponseException(f"Parsing error: '{e}'") from e
        if from_ankaios.HasField("response"):
            self._response = from_ankaios.response
            self._from_proto()
        elif from_ankaios.HasField("connectionClosed"):
            self.content_type = ResponseType.CONNECTION_CLOSED
            self.content = from_ankaios.connectionClosed.reason
        else:
            raise ResponseException(  # pragma: no cover
                "Invalid response type.")

    def _from_proto(self) -> None:
        """
        Converts the parsed protobuf message to a Response object.
        This can be either an error, a complete state,
        or an update state success.

        Raises:
            ResponseException: If the response type is invalid.
        """
        if self._response.HasField("error"):
            self.content_type = ResponseType.ERROR
            self.content = self._response.error.message
        elif self._response.HasField("completeState"):
            self.content_type = ResponseType.COMPLETE_STATE
            self.content = CompleteState()
            self.content._from_proto(self._response.completeState)
        elif self._response.HasField("UpdateStateSuccess"):
            update_state_msg = self._response.UpdateStateSuccess
            self.content_type = ResponseType.UPDATE_STATE_SUCCESS
            self.content = UpdateStateSuccess()
            for workload in update_state_msg.addedWorkloads:
                workload_name, workload_id, agent_name = \
                    workload.split(".")
                self.content.added_workloads.append(
                    WorkloadInstanceName(
                        agent_name, workload_name, workload_id
                    )
                )
            for workload in update_state_msg.deletedWorkloads:
                workload_name, workload_id, agent_name = \
                    workload.split(".")
                self.content.deleted_workloads.append(
                    WorkloadInstanceName(
                        agent_name, workload_name, workload_id
                    )
                )
        else:
            raise ResponseException("Invalid response type.")

    def get_request_id(self) -> str:
        """
        Gets the request id of the response.

        Returns:
            str: The request id of the response.
        """
        if self.content_type == ResponseType.CONNECTION_CLOSED:
            return None
        return self._response.requestId

    def get_content(self) -> \
            tuple[
                'ResponseType',
                Union[str, 'CompleteState', 'UpdateStateSuccess']
                ]:
        """
        Gets the content of the response. It can be either a string (if error),
        a CompleteState instance, or a UpdateStateSuccess instance.

        Returns:
            tuple[ResponseType, any]: the content type and the content.
        """
        return (self.content_type, self.content)


class ResponseType(Enum):
    """ Enumeration for the different types of response. """
    ERROR = 1
    "(int): Got an error from Ankaios."
    COMPLETE_STATE = 2
    "(int): Got the complete state."
    UPDATE_STATE_SUCCESS = 3
    "(int): Got a successful update state response."
    CONNECTION_CLOSED = 4
    "(int): Connection closed by the server."

    def __str__(self) -> str:
        """
        Converts the ResponseType to a string.

        Returns:
            str: The string representation of the ResponseType.
        """
        return self.name.lower()


class UpdateStateSuccess:
    """
    Represents an object that holds the added and deleted workloads.
    This is automatically returned whenever a state update is successful.
    """
    def __init__(self) -> None:
        """
        Initializes the UpdateStateSuccess.
        """
        self.added_workloads = []
        self.deleted_workloads = []

    def to_dict(self) -> dict:
        """
        Converts the UpdateStateSuccess to a dictionary.

        Returns:
            dict: The dictionary representation.
        """
        return {
            "added_workloads": [instance_name.to_dict()
                                for instance_name in self.added_workloads],
            "deleted_workloads": [instance_name.to_dict()
                                  for instance_name in self.deleted_workloads]
        }

    def __str__(self) -> str:
        """
        Converts the UpdateStateSuccess to a string.

        Returns:
            str: The string representation.
        """
        added_workloads = [
            str(instance_name) for instance_name in self.added_workloads]
        deleted_workloads = [
            str(instance_name) for instance_name in self.deleted_workloads]
        return f"Added workloads: {added_workloads}, " \
               f"Deleted workloads: {deleted_workloads}"
