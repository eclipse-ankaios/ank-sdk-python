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
This module defines the EventQueue class for handling events.

Classes
-------

- EventQueue:
    Represents a queue of events received from the Ankaios system.
    Inherits from the standard Queue class.

Usage
-----

- Get the events out of the queue:
    .. code-block:: python

        event_queue: EventQueue
        event: EventEntry = event_queue.get()  # blocking call
"""

__all__ = ["EventQueue"]


from queue import Queue
from .request import EventsRequest


class EventQueue(Queue):
    """
    Represents a queue of updates through the event campaign.
    Inherits from the standard Queue class.
    All objects in this queue are of type :py:type:`EventEntry`.
    """

    def __init__(
        self,
        request_id: EventsRequest,
    ) -> None:
        """
        Initializes the EventQueue with the given parameters.

        Args:
            request_id (str): The request id of the event campaign.
        """
        super().__init__()
        self._request_id = request_id
