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

- :class:`EventQueue`:
    Represents a queue of events received from the Ankaios system.
    Inherits from the standard Queue class.

Usage
-----

- Check current state of the followed fields:
    .. code-block:: python

        event_queue: EventQueue
        current_state = event_queue.complete_state

- Get the events out of the queue:
    .. code-block:: python

        event_queue: EventQueue
        event: EventEntry = event_queue.get()  # blocking call
"""

__all__ = ["EventQueue"]


from queue import Queue
from .request import EventsRequest
from .response import EventEntry
from .complete_state import CompleteState


class EventQueue(Queue):
    """
    Represents a queue of updates through the event campaign.
    Inherits from the standard Queue class.
    All objects in this queue are of type |EventEntry|.
    """

    def __init__(
        self,
        request_id: str,
    ) -> None:
        """
        Initializes the EventQueue with the given parameters.

        :param request_id: The request id of the event campaign.
        :type request_id: str
        """
        super().__init__()
        self.complete_state: CompleteState = None
        self._request_id = request_id

    def add_event(self, event: EventEntry) -> None:
        """
        Adds an event to the queue and updates the known complete state.

        :param event: The event to be added to the queue.
        :type event: EventEntry
        """
        self.complete_state = event.complete_state
        self.put(event)
