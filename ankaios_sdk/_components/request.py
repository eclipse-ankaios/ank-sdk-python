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
This module defines the Request class for creating and handling
requests to the Ankaios system.

Classes
-------

- Request:
    Represents a request to the Ankaios system and provides \
    methods to get and set the state of the system.

Enums
-----

- RequestType:
    Enumeration for the different types of requests. It includes
    UPDATE_STATE and GET_STATE.

Usage
-----

- Create a Request for updating the state:
    .. code-block:: python

        request = Request(RequestType.UPDATE_STATE)
        request.set_complete_state(complete_state)

- Create a Request for getting the state:
    .. code-block:: python

        request = Request(RequestType.GET_STATE)

- Get the request ID:
    .. code-block:: python

        request_id = request.get_id()

- Add a mask to the request:
    .. code-block:: python

        request.add_mask("desiredState.workloads")
"""

__all__ = ["Request", "RequestType"]

import uuid
from enum import Enum
from .._protos import _ank_base
from ..exceptions import RequestException
from ..utils import get_logger
from .complete_state import CompleteState


class Request:
    """
    Represents a request to the Ankaios system.
    """
    def __init__(self, request_type: 'RequestType') -> None:
        """
        Initializes a Request instance with the given request type.

        Args:
            request_type (RequestType): The type of the request.

        Raises:
            RequestException: If the request type is invalid.
        """
        self._request = _ank_base.Request()
        self._request.requestId = str(uuid.uuid4())
        self._request_type = request_type
        self.logger = get_logger()

        if request_type == RequestType.UPDATE_STATE:
            self._request.updateStateRequest.updateMask[:] = []
        elif request_type == RequestType.GET_STATE:
            self._request.completeStateRequest.fieldMask[:] = []
        else:
            self.logger.error("Invalid request type.")
            raise RequestException("Invalid request type. "
                                   "Check the RequestType enum.")
        self.logger.debug("Created request of type %s with id %s",
                          str(request_type), self._request.requestId)

    def __str__(self) -> str:
        """
        Returns the string representation of the request.

        Returns:
            str: The string representation of the request.
        """
        return str(self._to_proto())

    def get_id(self) -> str:
        """
        Gets the request ID.

        Returns:
            str: The request ID.
        """
        return self._request.requestId

    def set_complete_state(self, complete_state: CompleteState) -> None:
        """
        Sets the complete state for the request.

        Args:
            complete_state (CompleteState): The complete state to
                set for the request.

        Raises:
            RequestException: If the request type is not UPDATE_STATE.
        """
        if self._request_type != RequestType.UPDATE_STATE:
            raise RequestException("Complete state can only be set "
                                   + "for an update state request.")

        self._request.updateStateRequest.newState.CopyFrom(
            complete_state._to_proto()
        )

    def add_mask(self, mask: str) -> None:
        """
        Sets the update mask for the request.

        Args:
            mask (str): The mask to set for the request.
        """
        if self._request_type == RequestType.UPDATE_STATE:
            self._request.updateStateRequest.updateMask.append(mask)
        elif self._request_type == RequestType.GET_STATE:
            self._request.completeStateRequest.fieldMask.append(mask)

    def set_masks(self, masks: list) -> None:
        """
        Sets the update masks for the request.

        Args:
            masks (list): The masks to set for the request.
        """
        if self._request_type == RequestType.UPDATE_STATE:
            self._request.updateStateRequest.updateMask[:] = masks
        elif self._request_type == RequestType.GET_STATE:
            self._request.completeStateRequest.fieldMask[:] = masks

    def _to_proto(self) -> _ank_base.Request:
        """
        Converts the Request object to a proto message.

        Returns:
            _ank_base.Request: The protobuf message representing the request.
        """
        return self._request


class RequestType(Enum):
    """ Enumeration for the different types of requests. """
    UPDATE_STATE = 1
    "(int): Request for updating the state."
    GET_STATE = 2
    "(int): Request for getting the state."

    def __str__(self) -> str:
        """
        Return the string representation of the enum value.

        Returns:
            str: The enum value as a string.
        """
        return self.name.lower()
