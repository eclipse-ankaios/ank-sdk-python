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

__all__ = ["LogCampaignResponse", "LogQueue"]

from queue import Queue
from typing import Union
from datetime import datetime
from .workload_state import WorkloadInstanceName
from .request import LogsRequest, LogsCancelRequest


class LogCampaignResponse:
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
    """
    def __init__(self, workload_names: list[WorkloadInstanceName],
                 follow: bool = False, tail: int = -1,
                 since: Union[str, datetime] = "",
                 until: Union[str, datetime] = "") -> None:
        """
        Initializes the LogQueue with the given parameters.

        Args:
            workload_names (list[WorkloadInstanceName]): The workload
                instance names for which to get logs.
            follow (bool): If true, the logs will be continuously streamed.
            tail (int): The number of lines to display from the end of the logs.
            since (str / datetime): The start time for the logs. If string, it must
                be in the RFC3339 format.
            until (str / datetime): The end time for the logs. If string, it must
                be in the RFC3339 format.
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
        return LogsCancelRequest(id=self._request.get_id())
