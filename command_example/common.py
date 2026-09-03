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
Shared helpers for the Command Interface example scripts.
"""

from ankaios_sdk import Ankaios

DEFAULT_SERVER_URL = "http://127.0.0.1:25551"
DEFAULT_AGENT_NAME = "agent_A"


def print_workload_states(ankaios: Ankaios) -> None:
    """
    Prints the state of every workload in the cluster.

    :param ankaios: The Ankaios object to query.
    :type ankaios: Ankaios
    """
    complete_state = ankaios.get_state(field_masks=["workloadStates"])
    for workload_state in complete_state.get_workload_states().get_as_list():
        instance_name = workload_state.workload_instance_name
        print(
            f"Workload {instance_name.workload_name} on agent "
            f"{instance_name.agent_name} has the state "
            f"{workload_state.execution_state.state}"
        )
