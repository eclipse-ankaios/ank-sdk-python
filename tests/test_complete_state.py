# Copyright (c) 2024 Elektrobit Automotive GmbH
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
This module contains unit tests for the Manifest class in the ankaios_sdk.
"""

from ankaios_sdk import CompleteState, WorkloadStateCollection, Manifest
from ankaios_sdk._components.complete_state import SUPPORTED_API_VERSION
from ankaios_sdk._protos import _ank_base
from tests.workload.test_workload import generate_test_workload
from tests.test_manifest import MANIFEST_DICT


def generate_test_config():
    """
    Generate a test configuration.
    """
    return {
        "config_1": "val_1",
        "config_2": ["val_2", "val_3"],
        "config_3": {
            "key_1": "val_4",
            "key_2": "val_5"
        }
    }


def test_general_functionality():
    """
    Test general functionality of the CompleteState class.
    """
    complete_state = CompleteState()
    assert complete_state.get_api_version() == SUPPORTED_API_VERSION
    complete_state._set_api_version("v0.2")
    assert complete_state.get_api_version() == "v0.2"
    assert str(complete_state) == "desiredState {\n  apiVersion: \"v0.2\"\n}\n"


def test_workload_functionality():
    """
    Test the functionality of CompleteState class
    regarding setting and getting workloads.
    """
    complete_state = CompleteState()
    assert len(complete_state.get_workloads()) == 0

    wl_nginx = generate_test_workload("nginx_test")
    complete_state.add_workload(wl_nginx)
    assert len(complete_state.get_workloads()) == 1
    assert complete_state.get_workload("nginx_test") == wl_nginx
    assert complete_state._complete_state.desiredState.workloads\
        .workloads["nginx_test"] == wl_nginx._to_proto()

    assert complete_state.get_workload("invalid") is None


def test_workload_states():
    """
    Test the functionality of CompleteState class regarding
    setting and getting workload states.
    """
    complete_state = CompleteState()
    complete_state._from_proto(_ank_base.CompleteState(
        workloadStates=_ank_base.WorkloadStatesMap(agentStateMap={
            "agent_A": _ank_base.ExecutionsStatesOfWorkload(wlNameStateMap={
                "nginx": _ank_base.ExecutionsStatesForId(idStateMap={
                    "1234": _ank_base.ExecutionState(
                        additionalInfo="Random info",
                        succeeded=_ank_base.SUCCEEDED_OK,
                        )
                    })
                }),
            "agent_B": _ank_base.ExecutionsStatesOfWorkload(wlNameStateMap={
                "nginx": _ank_base.ExecutionsStatesForId(idStateMap={
                    "5678": _ank_base.ExecutionState(
                        additionalInfo="Random info",
                        pending=_ank_base.PENDING_WAITING_TO_START,
                        )
                    }),
                "dyn_nginx": _ank_base.ExecutionsStatesForId(idStateMap={
                    "9012": _ank_base.ExecutionState(
                        additionalInfo="Random info",
                        stopping=_ank_base.STOPPING_WAITING_TO_STOP,
                        )
                    })
                })
            })
        )
    )

    workload_states = complete_state.get_workload_states()
    assert isinstance(workload_states, WorkloadStateCollection)
    assert len(workload_states.get_as_list()) == 3


def test_get_agents():
    """
    Test the get_agents method of the CompleteState class.
    """
    complete_state = CompleteState()
    complete_state._from_proto(_ank_base.CompleteState(
        agents=_ank_base.AgentMap(agents={
            "agent_A": _ank_base.AgentAttributes(
                cpu_usage=_ank_base.CpuUsage(cpu_usage=50),
                free_memory=_ank_base.FreeMemory(free_memory=1024)
            )
        })
    ))
    agents = complete_state.get_agents()
    assert len(agents) == 1
    assert "agent_A" in agents
    assert agents["agent_A"]["cpu_usage"] == 50
    assert agents["agent_A"]["free_memory"] == 1024


def test_get_configs():
    """
    Test the get_configs method of the CompleteState class.
    """
    complete_state = CompleteState()
    complete_state._from_proto(_ank_base.CompleteState(
        desiredState=_ank_base.State(
            configs=_ank_base.ConfigMap(
                configs={
                    "config_1": _ank_base.ConfigItem(
                        String="val_1"
                    ),
                    "config_2": _ank_base.ConfigItem(
                        array=_ank_base.ConfigArray(
                            values=[
                                _ank_base.ConfigItem(String="val_2"),
                                _ank_base.ConfigItem(String="val_3")
                            ]
                        )
                    ),
                    "config_3": _ank_base.ConfigItem(
                        object=_ank_base.ConfigObject(
                            fields={
                                "key_1": _ank_base.ConfigItem(String="val_4"),
                                "key_2": _ank_base.ConfigItem(String="val_5")
                            }
                        )
                    )
                }
            )
        )
    ))
    assert complete_state.get_configs() == generate_test_config()


def test_from_manifest():
    """
    Test the from_manifest method of the CompleteState class.
    """
    manifest = Manifest(MANIFEST_DICT)
    complete_state = CompleteState.from_manifest(manifest)
    assert complete_state.get_api_version() == "v0.1"
    workloads = complete_state.get_workloads()
    assert len(workloads) == 1
    assert workloads[0].name == "nginx_test"
    assert complete_state.get_configs() == {
        "test_ports": {
            "port": "8081"
        }
    }


def test_proto():
    """
    Test converting the CompleteState instance to and from a protobuf message.
    """
    complete_state = CompleteState()
    wl_nginx = generate_test_workload("nginx_test")
    config = generate_test_config()

    complete_state.add_workload(wl_nginx)
    complete_state.set_configs(config)

    new_complete_state = CompleteState()
    new_complete_state._from_proto(complete_state._to_proto())

    assert str(complete_state) == str(new_complete_state)
