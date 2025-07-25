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

from ankaios_sdk import Ankaios, ControlInterfaceException, Workload
from time import sleep
import sys, signal

# Create a new Ankaios object.
# The connection to the control interface is automatically done at this step.
# The Ankaios class supports context manager syntax:
with Ankaios() as ankaios:

    looping = True
    def signal_handler(sig, frame):
        global looping
        looping = False

    # Add a SIGTERM handler to allow a clean shutdown
    signal.signal(signal.SIGTERM, signal_handler)

    while looping:
        try:
            # Request the state of the system, filtered with the workloadStates
            complete_state = ankaios.get_state(timeout=5, field_masks=["workloadStates"])
        except ControlInterfaceException as e:
            print(f"Error while getting the state: {e}")
        else:
            # Get the workload states present in the complete_state
            workload_states_dict = complete_state.get_workload_states().get_as_dict()

            # Print the states of the workloads:
            for agent_name in workload_states_dict:
                for workload_name in workload_states_dict[agent_name]:
                    for workload_id in workload_states_dict[agent_name][workload_name]:
                        print(
                            f"Workload {workload_name} on agent {agent_name} has the state "
                            + str(
                                workload_states_dict[agent_name][workload_name][
                                    workload_id
                                ].state
                            )
                        )
            
        # Sleep for 5 seconds
        sleep(5)
