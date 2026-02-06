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

- :class:`LogCampaignResponse`:
    Represents the response for a log campaign, containing the queue of
    received messages and the accepted workload names.
- :class:`LogQueue`:
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
from .workload_state import WorkloadInstanceName


# pylint: disable=too-few-public-methods
class LogCampaignResponse:
    """
    Represents the response for a log campaign, containing the queue of
    received messages and the accepted workload names.
    """

    def __init__(
        self,
        queue: "LogQueue",
        accepted_workload_names: list[WorkloadInstanceName],
    ) -> None:
        """
        Initializes the LogCampaignResponse with the given queue and accepted
        workload names.

        :param queue: The queue containing the log messages.
        :type queue: LogQueue
        :param accepted_workload_names: The list of
            workload instance names for which logs have been accepted.
        :type accepted_workload_names: list[WorkloadInstanceName]
        """
        self.queue = queue
        self.accepted_workload_names = accepted_workload_names


class LogQueue(Queue):
    """
    Represents a queue of received messages through the log campaign.
    Inherits from the standard Queue class.
    All objects in this queue are of type |LogResponse|.
    """

    def __init__(
        self,
        request_id: str,
    ) -> None:
        """
        Initializes the LogQueue with the given parameters.

        :param request_id: The request id of the logs campaign.
        :type request_id: str
        """
        super().__init__()
        self._request_id = request_id
