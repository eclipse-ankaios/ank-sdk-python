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
Connects to an Ankaios server directly over gRPC (from outside a
workload), applies a workload, updates it, then deletes it, printing
the workload states after every change.

Usage:
    python3 basic_test.py [server_url] [agent_name]
"""

import sys
import time

from common import (
    DEFAULT_AGENT_NAME,
    DEFAULT_SERVER_URL,
    print_workload_states,
)
from ankaios_sdk import (
    Ankaios,
    AnkaiosException,
    ConnectionType,
    Workload,
    WorkloadStateEnum,
)


def main() -> None:
    """Applies, updates and deletes a workload over gRPC."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL
    agent_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_AGENT_NAME

    with Ankaios(
        connection_type=ConnectionType.COMMAND_INTERFACE, server_url=server_url
    ) as ankaios:
        workload = (
            Workload.builder()
            .workload_name("dynamic_nginx")
            .agent_name(agent_name)
            .runtime("podman")
            .restart_policy("NEVER")
            .runtime_config(
                "image: docker.io/library/nginx\n"
                'commandOptions: ["-p", "8080:80"]'
            )
            .build()
        )

        try:
            # Run the workload
            update_response = ankaios.apply_workload(workload)
            workload_instance_name = update_response.added_workloads[0]

            try:
                ankaios.wait_for_workload_to_reach_state(
                    workload_instance_name, WorkloadStateEnum.RUNNING
                )
                print("Workload reached the RUNNING state.")
            except TimeoutError:
                print("Workload didn't reach the required state in time.")
            print_workload_states(ankaios)

            time.sleep(2)

            # Update the workload
            workloads = ankaios.get_workload(
                workload_instance_name.workload_name
            )
            workload = workloads[0]
            workload.update_restart_policy("ALWAYS")
            ankaios.apply_workload(workload)

            try:
                ankaios.wait_for_workload_to_reach_state(
                    workload_instance_name, WorkloadStateEnum.RUNNING
                )
                print("Workload reached the RUNNING state after update.")
            except TimeoutError:
                print("Workload didn't reach the required state in time.")
            print_workload_states(ankaios)

            time.sleep(2)

            # Delete the workload
            ankaios.delete_workload(workload_instance_name.workload_name)
            time.sleep(5)
            print_workload_states(ankaios)

        except AnkaiosException as e:
            print("Ankaios Exception occurred: ", e)


if __name__ == "__main__":
    main()
