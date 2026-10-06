# Copyright (c) 2026 Elektrobit Automotive GmbH
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
Connects to an Ankaios server directly over the Command Interface,
registers for events on a workload, applies it, streams its
logs until they stop while printing any events received along the
way, then unregisters/deletes everything.

Usage:
    python3 logs_events_test.py [server_url] [agent_name]
"""

import sys
import threading
from queue import Empty, Queue

from common import DEFAULT_AGENT_NAME, DEFAULT_SERVER_URL
from ankaios_sdk import (
    Ankaios,
    AnkaiosException,
    ConnectionType,
    EventEntry,
    LogEntry,
    LogsStopResponse,
    Workload,
)


def _print_events(event_queue: Queue, stop_event: threading.Event) -> None:
    """Prints events from the queue until stop_event is set."""
    while not stop_event.is_set():
        try:
            event: EventEntry = event_queue.get(timeout=0.2)
        except Empty:
            continue
        print(
            f"[event] added={event.added_fields} "
            f"updated={event.updated_fields} "
            f"removed={event.removed_fields}"
        )


def main() -> None:
    """Streams logs and events for a short-lived workload over the Command Interface."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL
    agent_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_AGENT_NAME

    with Ankaios(
        connection_type=ConnectionType.COMMAND_INTERFACE, server_url=server_url
    ) as ankaios:
        # Workload that prints a handful of lines then exits.
        workload = (
            Workload.builder()
            .workload_name("count_to_five")
            .agent_name(agent_name)
            .runtime("podman")
            .restart_policy("NEVER")
            .runtime_config(
                "image: ghcr.io/eclipse-ankaios/tests/alpine:latest\n"
                'commandOptions: [ "--entrypoint", "/bin/sh" ]\n'
                "commandArgs: [ \"-c\", \"echo -e '1\\n2\\n3\\n4\\n5';\" ]"
            )
            .build()
        )

        try:
            # Subscribe to changes on this workload's desired state
            # before applying it.
            event_queue = ankaios.register_event(
                field_masks=["desiredState.workloads.count_to_five"],
            )

            update_response = ankaios.apply_workload(workload)
            workload_instance_name = update_response.added_workloads[0]

            log_campaign = ankaios.request_logs(
                workload_names=[workload_instance_name],
            )
            if (
                workload_instance_name
                not in log_campaign.accepted_workload_names
            ):
                print(
                    f"Workload '{workload_instance_name}' not accepted "
                    "for log retrieval"
                )

            # Print events in the background while logs are streamed
            # on the main thread below.
            stop_event = threading.Event()
            events_thread = threading.Thread(
                target=_print_events,
                args=(event_queue, stop_event),
                daemon=True,
            )
            events_thread.start()

            # Stream logs until they stop.
            while True:
                log = log_campaign.queue.get()
                match log:
                    case LogEntry():
                        print(f"[log] {log.message}")
                    case LogsStopResponse():
                        print(
                            "No more logs available for "
                            f"'{workload_instance_name}'."
                        )
                        break

            stop_event.set()
            events_thread.join()

            ankaios.stop_receiving_logs(log_campaign)
            ankaios.unregister_event(event_queue)
            ankaios.delete_workload(workload_instance_name.workload_name)

        except AnkaiosException as e:
            print("Ankaios Exception occurred: ", e)


if __name__ == "__main__":
    main()
