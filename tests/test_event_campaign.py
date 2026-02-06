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
This module contains unit tests for the EventQueue class in the ankaios_sdk.

Helper Functions:
    generate_test_event_entry: Helper function to generate an EventEntry
        instance for testing.
"""

from ankaios_sdk import (
    EventQueue,
    EventEntry,
    EventsRequest,
    CompleteState,
)
from tests.test_complete_state import COMPLETE_STATE_PROTO


def generate_test_event_entry(complete_state=None):
    """
    Generate a test EventEntry object.
    """
    if complete_state is None:
        complete_state = CompleteState(_proto=COMPLETE_STATE_PROTO)
    return EventEntry(
        complete_state=complete_state,
        added_fields=["field1"],
        updated_fields=["field2"],
        removed_fields=["field3"],
    )


def test_events_queue():
    """
    Test the queue functionality.
    """
    events_queue = EventQueue(EventsRequest(masks=["field1"]))

    event_entry = generate_test_event_entry()
    events_queue.put(event_entry)
    assert events_queue.empty() is False
    entry = events_queue.get()
    assert isinstance(entry, EventEntry)
    assert entry == event_entry

    assert (
        str(entry) == "Event:\n  Added fields: ['field1']\n  "
        "Updated fields: ['field2']\n  Deleted fields: ['field3']\n"
    )
