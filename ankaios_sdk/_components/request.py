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
    Represents the base request to the Ankaios system. It is an abstract
    class that should be subclassed for specific request types.
- GetStateRequest:
    Represents a request to get the state of the Ankaios system.
- UpdateStateRequest:
    Represents a request to update the state of the Ankaios system.
- LogsRequest:
    Represents a request to get logs from the Ankaios system.
- LogsCancelRequest:
    Represents a request to stop the real-time log stream from the
    Ankaios system.

Usage
-----

- Create a Request for updating the state:
    .. code-block:: python

        complete_state = CompleteState()
        request = UpdateStateRequest(
            complete_state, masks=["desiredState.workloads"]
        )

- Create a Request for getting the state:
    .. code-block:: python

        request = GetStateRequest(masks=["desiredState.workloads"])

- Create a Request for getting logs for a workload:
    .. code-block:: python

        workload_name: WorkloadInstanceName = ...
        request = LogsRequest(workload_names=[workload_name])

- Create a Request for getting a continuous stream of logs:
    .. code-block:: python

        workload_name: WorkloadInstanceName = ...
        request = LogsRequest(workload_names=[workload_name], follow=True)

- Create a Request for stopping the log stream:
    .. code-block:: python

        request = LogsCancelRequest()

- Get the request ID:
    .. code-block:: python

        request_id = request.get_id()
"""

__all__ = ["Request", "GetStateRequest", "UpdateStateRequest",
           "LogsRequest", "LogsCancelRequest"]

import uuid
from typing import Union
from datetime import datetime
from .._protos import _ank_base
from ..utils import get_logger
from .complete_state import CompleteState
from .workload_state import WorkloadInstanceName


class Request:
    """
    Represents a request to the Ankaios system.
    """
    def __init__(self) -> None:
        """
        Initializes a Request instance.

        Raises:
            TypeError: If the Request class is instantiated directly.
        """
        if self.__class__ is Request:
            raise TypeError("Request cannot be instantiated directly.")
        self._request = _ank_base.Request()
        self._request.requestId = str(uuid.uuid4())
        self.logger = get_logger()

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

    def _to_proto(self) -> _ank_base.Request:
        """
        Converts the Request object to a proto message.

        Returns:
            _ank_base.Request: The protobuf message representing the request.
        """
        return self._request


# pylint: disable=too-few-public-methods, dangerous-default-value
class GetStateRequest(Request):
    """
    Represents a request for getting the state of the Ankaios system.
    This request includes an optional list of masks to specify which
    fields should be included in the response.
    """
    def __init__(self, masks: list = []) -> None:
        """
        Initializes a GetStateRequest instance.

        Args:
            masks (list): The masks to set for the request.
        """
        super().__init__()
        self._request.completeStateRequest.fieldMask[:] = masks

        self.logger.debug("Created request of type GetState with id %s",
                          self._request.requestId)


# pylint: disable=too-few-public-methods, dangerous-default-value
class UpdateStateRequest(Request):
    """
    Represents a request for updating the state of the Ankaios system.
    This request includes the new state and an optional list of masks
    to specify which fields should be updated.
    """
    def __init__(
            self, complete_state: CompleteState, masks: list = []
            ) -> None:
        """
        Initializes an UpdateStateRequest instance.

        Args:
            complete_state (CompleteState): The new state to set.
            masks (list): The masks to set for the request.
        """
        super().__init__()
        self._request.updateStateRequest.updateMask[:] = masks
        self._request.updateStateRequest.newState.CopyFrom(
            complete_state._to_proto()
        )

        self.logger.debug("Created request of type UpdateState with id %s",
                          self._request.requestId)


# pylint: disable=too-few-public-methods, dangerous-default-value
class LogsRequest(Request):
    """
    Represents a request for getting logs from the Ankaios system.
    """
    def __init__(
            self, workload_names: list[WorkloadInstanceName], follow: bool = False,
            tail: int = -1, since: Union[str, datetime] = "",
            until: Union[str, datetime] = ""
            ) -> None:
        """
        Initializes an LogsRequest instance.

        Args:
            workload_names (list[WorkloadInstanceName]): The workload instance
                names for which to get logs.
            follow (bool): If true, the logs will be continuously streamed.
            tail (int): The number of lines to display from the end of the logs.
            since (str / datetime): The start time for the logs. If string, it must
                be in the RFC3339 format.
            until (str / datetime): The end time for the logs. If string, it must
                be in the RFC3339 format.

        Raises:
            ValueError: If no workload names are provided.
        """
        if len(workload_names) == 0:
            raise ValueError("At least one workload name must be provided.")

        super().__init__()
        self._request.logsRequest = _ank_base.LogsRequest(
            workloadNames=[name._to_proto() for name in workload_names],
            follow=follow,
            tail=tail
        )
        if since:
            if isinstance(since, str):
                self._request.logsRequest.since = since
            else:
                self._request.logsRequest.since = since.isoformat()
        if until:
            if isinstance(until, str):
                self._request.logsRequest.until = until
            else:
                self._request.logsRequest.until = until.isoformat()

        self.logger.debug("Created request of type LogsRequest with id %s",
                          self._request.requestId)


# pylint: disable=too-few-public-methods, dangerous-default-value
class LogsCancelRequest(Request):
    """
    Represents a request for stopping the real-time log stream
    from the Ankaios system.
    """
    def __init__(self) -> None:
        """
        Initializes an LogsCancelRequest instance.
        """
        super().__init__()
        self._request.logsCancelRequest = _ank_base.LogsCancelRequest()

        self.logger.debug("Created request of type LogsCancelRequest with id %s",
                          self._request.requestId)
