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

from ankaios_sdk import (
    Ankaios,
    AnkaiosLogLevel,
    AnkaiosException,
    Workload,
    EventEntry,
)
import sys, signal

# Create a new Ankaios object.
# The connection to the control interface is automatically done at this step.
# The Ankaios class supports context manager syntax:
with Ankaios(log_level=AnkaiosLogLevel.DEBUG) as ankaios:

    def signal_handler(sig, frame):
        global ankaios
        del ankaios
        sys.exit(0)

    # Add a SIGTERM handler to allow a clean shutdown
    signal.signal(signal.SIGTERM, signal_handler)

    # Create a new workload
    workload = (
        Workload.builder()
        .workload_name("count_to_five")
        .agent_name("agent_Py_SDK")
        .runtime("podman")
        .restart_policy("NEVER")
        .runtime_config(
            'image: ghcr.io/eclipse-ankaios/tests/alpine:latest\ncommandOptions: [ "--entrypoint", "/bin/sh" ]\ncommandArgs: [ "-c", "echo -e \'1\\n2\\n3\\n4\\n5\';" ]'
        )
        .build()
    )

    try:
        # Run the workload
        update_response = ankaios.apply_workload(workload)

        # Get the WorkloadInstanceName to check later if the workload is running
        workload_instance_name = update_response.added_workloads[0]

        # Register to events to the workload
        try:
            event_queue = ankaios.register_event(
                field_masks=["desiredState.workloads.count_to_five"],
            )
        except AnkaiosException as e:
            print("Ankaios Exception occurred during event registration: ", e)
            sys.exit(1)

        while True:
            # Get the events out of the queue
            event: EventEntry = event_queue.get()

            # Interpret the event
            print("Received event:")
            if event.added_fields:
                print(f" - Added fields: {event.added_fields}")
            if event.updated_fields:
                print(f" - Updated fields: {event.updated_fields}")
            if event.removed_fields:
                print(f" - Removed fields: {event.removed_fields}")
            print(f"Current complete state: {event.complete_state}\n")

        # Unregister the events
        ankaios.unregister_event(event_queue)

    # Catch the AnkaiosException in case something went wrong
    except AnkaiosException as e:
        print("Ankaios Exception occurred: ", e)
