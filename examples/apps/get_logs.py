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

from ankaios_sdk import Ankaios, AnkaiosLogLevel, AnkaiosException, Workload, LogResponse, LogsType
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
            "image: ghcr.io/eclipse-ankaios/tests/alpine:latest\ncommandOptions: [ \"--entrypoint\", \"/bin/sh\" ]\ncommandArgs: [ \"-c\", \"echo -e \'1\\n2\\n3\\n4\\n5\';\" ]"
        )
        .build()
    )

    try:
        # Run the workload
        update_response = ankaios.apply_workload(workload)

        # Get the WorkloadInstanceName to check later if the workload is running
        workload_instance_name = update_response.added_workloads[0]

        # Request the logs from the new workload
        log_campaign = ankaios.request_logs(
            workload_names=[workload_instance_name],
        )

        # Check if the workload was accepted for log retrieval
        if workload_instance_name not in log_campaign.accepted_workload_names:
            print("Workload {} not accepted for log retrieval."
                  .format(workload_instance_name))
            sys.exit(1)

        while True:
            # Get the logs from the queue
            log: LogResponse = log_campaign.queue.get()

            # Interpret the received message
            if log.type == LogsType.LOGS_ENTRY:
                # Log entry received
                print(f"Received message: {log.message}")
            elif log.type == LogsType.LOGS_STOP_RESPONSE:
                # Stop response received, break the loop
                print("Received stop response, stopping log retrieval.")
                break

    # Catch the AnkaiosException in case something went wrong
    except AnkaiosException as e:
        print("Ankaios Exception occurred: ", e)

    # Stop receiving logs
    ankaios.stop_receiving_logs(log_campaign)
