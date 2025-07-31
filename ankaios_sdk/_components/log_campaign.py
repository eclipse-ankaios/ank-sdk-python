# Copyright (c) 2025 Elektrobit Automotive GmbH
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
This module defines the LogCampaignResponse and LogQueue classes for handling
log campaigns in the Ankaios system.

Classes
-------

- LogCampaignResponse:
    Represents the response for a log campaign, containing the queue of
    received messages and the accepted workload names.
- LogQueue:
    Represents a queue of received messages through the log campaign.

Usage
-----

- Check the valid workload names:
    .. code-block:: python

        log_campaign: LogCampaignResponse
        valid_workload_names: list = log_campaign.accepted_workload_names

- Get logs out of the queue:
    .. code-block:: python

        log = log_campaign.queue.get()
"""

__all__ = ["LogCampaignResponse", "LogQueue"]

from queue import Queue
from typing import Union
from datetime import datetime
from .workload_state import WorkloadInstanceName
from .request import LogsRequest, LogsCancelRequest


# pylint: disable=too-few-public-methods
class LogCampaignResponse:
    """
    Represents the response for a log campaign, containing the queue of
    received messages and the accepted workload names.
    """
    def __init__(self, queue: "LogQueue",
                 accepted_workload_names: list[WorkloadInstanceName]) -> None:
        """
        Initializes the LogCampaignResponse with the given queue and accepted
        workload names.

        Args:
            queue (LogQueue): The queue containing the log messages.
            accepted_workload_names (list[WorkloadInstanceName]): The list of
                workload instance names for which logs have been accepted.
        """
        self.queue = queue
        self.accepted_workload_names = accepted_workload_names


class LogQueue(Queue):
    """
    Represents a queue of received messages through the log campaign.
    Inherits from the standard Queue class.
    All objects in this queue are of type :py:type:`LogResponse`.
    """
    # pylint: disable=too-many-arguments
    def __init__(self, workload_names: list[WorkloadInstanceName], *,
                 follow: bool = False, tail: int = -1,
                 since: Union[str, datetime] = "",
                 until: Union[str, datetime] = "") -> None:
        """
        Initializes the LogQueue with the given parameters.

        Args:
            workload_names (list[WorkloadInstanceName]): The workload
                instance names for which to get logs.
            follow (bool): If true, the logs will be continuously streamed.
            tail (int): The number of lines to display from
                the end of the logs.
            since (str / datetime): The start time for the logs. If string,
                it must be in the RFC3339 format.
            until (str / datetime): The end time for the logs. If string,
                it must be in the RFC3339 format.
        """
        super().__init__()
        self._request = LogsRequest(
            workload_names=workload_names,
            follow=follow, tail=tail,
            since=since, until=until
        )

    def _get_request(self) -> LogsRequest:
        """
        Returns the LogsRequest object.

        Returns:
            LogsRequest: The LogsRequest object.
        """
        return self._request

    def _get_cancel_request(self) -> LogsCancelRequest:
        """
        Returns the LogsCancelRequest object.

        Returns:
            LogsCancelRequest: The LogsCancelRequest object.
        """
        return LogsCancelRequest(request_id=self._request.get_id())
