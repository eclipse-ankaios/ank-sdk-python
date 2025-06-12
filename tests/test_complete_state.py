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

import json
from ankaios_sdk import CompleteState, WorkloadStateCollection, Manifest
from ankaios_sdk._components.complete_state import SUPPORTED_API_VERSION
from ankaios_sdk._protos import _ank_base
from tests.workload.test_workload import generate_test_workload, WORKLOAD_PROTO
from tests.workload_state.test_workload_state_collection import \
    WORKLOAD_STATES_PROTO
from tests.test_manifest import MANIFEST_DICT


CONFIGS_PROTO = _ank_base.ConfigMap(
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


FILES_PROTO = _ank_base.Files(
    files=[
        _ank_base.File(
            mountPoint="./mount_point",
            data="data_1"
        ),
        _ank_base.File(
            mountPoint="./mount_point_2",
            binaryData="binary_data_1"
        )
    ]
)


AGENTS_PROTO = _ank_base.AgentMap(
    agents={
        "agent_A": _ank_base.AgentAttributes(
                cpu_usage=_ank_base.CpuUsage(cpu_usage=50),
                free_memory=_ank_base.FreeMemory(free_memory=1024)
        )
    }
)


COMPLETE_PROTO = proto_msg = _ank_base.CompleteState(
    desiredState=_ank_base.State(
        apiVersion="v0.1",
        workloads=WORKLOAD_PROTO,
        configs=CONFIGS_PROTO
    ),
    workloadStates=WORKLOAD_STATES_PROTO,
    agents=AGENTS_PROTO
)


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
    complete_state = CompleteState(workloads=[wl_nginx])
    assert len(complete_state.get_workloads()) == 1
    assert complete_state._complete_state.desiredState.workloads\
        .workloads["nginx_test"] == wl_nginx._to_proto()

    assert complete_state.get_workload("invalid") is None
    assert complete_state.get_workload("nginx_test") is not None


def test_workload_states():
    """
    Test the functionality of CompleteState class regarding
    setting and getting workload states.
    """
    complete_state = CompleteState(
        _proto=_ank_base.CompleteState(
            workloadStates=WORKLOAD_STATES_PROTO
        )
    )

    workload_states = complete_state.get_workload_states()
    assert isinstance(workload_states, WorkloadStateCollection)
    assert len(workload_states.get_as_list()) == 3


def test_get_agents():
    """
    Test the get_agents method of the CompleteState class.
    """
    complete_state = CompleteState(
        _proto=_ank_base.CompleteState(
            agents=AGENTS_PROTO
        )
    )
    agents = complete_state.get_agents()
    assert len(agents) == 1
    assert "agent_A" in agents
    assert agents["agent_A"]["cpu_usage"] == 50
    assert agents["agent_A"]["free_memory"] == 1024


def test_get_configs():
    """
    Test the get_configs method of the CompleteState class.
    """
    complete_state = CompleteState(
        _proto=_ank_base.CompleteState(
            desiredState=_ank_base.State(
                configs=CONFIGS_PROTO
            )
        )
    )
    configs = complete_state.get_configs()
    assert configs == {
        "config_1": "val_1",
        "config_2": ["val_2", "val_3"],
        "config_3": {
            "key_1": "val_4",
            "key_2": "val_5"
        }
    }
    complete_state.set_configs(configs)
    assert complete_state.get_configs() == configs


def test_from_manifest():
    """
    Test the from_manifest method of the CompleteState class.
    """
    manifest = Manifest.from_dict(MANIFEST_DICT)
    complete_state = CompleteState(manifest=manifest)
    assert complete_state.get_api_version() == "v0.1"
    workloads = complete_state.get_workloads()
    assert len(workloads) == 1
    assert workloads[0].name == "nginx_test"
    assert complete_state.get_configs() == {
        "test_ports": {
            "port": "8081"
        }
    }


def test_to_dict():
    """
    Test converting the CompleteState to a dictionary.
    """
    complete_state = CompleteState(
        _proto=COMPLETE_PROTO
    )

    complete_state_dict = complete_state.to_dict()
    assert complete_state_dict == {
        'desired_state': {
            'api_version': 'v0.1',
            'workloads': {
                'dynamic_nginx': {
                    'agent': 'agent_A',
                    'runtime': 'podman',
                    'runtimeConfig': 'image: control_interface_prod:0.1\\n',
                    'dependencies': {
                        'nginx': 'ADD_COND_RUNNING'
                    },
                    'restartPolicy': 'ALWAYS',
                    'tags': [
                        {
                            'key': 'owner',
                            'value': 'Ankaios team'
                        }
                    ],
                    'controlInterfaceAccess': {
                        'allowRules': [
                            {
                                'type': 'StateRule',
                                'operation': 'Write',
                                'filterMask': [
                                    'desiredState.workloads.dynamic_nginx'
                                ]
                            }
                        ],
                        'denyRules': [
                            {
                                'type': 'StateRule',
                                'operation': 'Read',
                                'filterMask': [
                                    'desiredState.workloads.dynamic_nginx'
                                ]
                            }]
                    },
                    'files': [
                        {
                            'mountPoint': './mount_point',
                            'data': 'data_1',
                        },
                        {
                            'mountPoint': './mount_point_2',
                            'binaryData': 'binary_data_1',
                        }
                    ],
                    'configs': {
                        'array': 'config_2',
                        'dict': 'config_3',
                        'str': 'config_1'
                    }
                }
            },
            'configs': {
                'config_1': 'val_1',
                'config_2': [
                    'val_2', 'val_3'
                ],
                'config_3': {
                    'key_1': 'val_4',
                    'key_2': 'val_5'
                }
            }
        },
        'workload_states': {
            'agent_B': {
                'nginx': {
                    '5678': {
                        'state': 'PENDING',
                        'substate': 'PENDING_WAITING_TO_START',
                        'additional_info': 'Random info'
                    }
                },
                'dyn_nginx': {
                    '9012': {
                        'state': 'STOPPING',
                        'substate': 'STOPPING_WAITING_TO_STOP',
                        'additional_info': 'Random info'
                    }
                }
            },
            'agent_A': {
                'nginx': {
                    '1234': {
                        'state': 'SUCCEEDED',
                        'substate': 'SUCCEEDED_OK',
                        'additional_info': 'Random info'
                    }
                }
            }
        },
        'agents': {
            'agent_A': {
                'cpu_usage': 50,
                'free_memory': 1024
            }
        }
    }

    # Test that it can be converted to json
    json.dumps(complete_state_dict)


def test_proto():
    """
    Test converting the CompleteState instance to and from a protobuf message.
    """
    complete_state = CompleteState(
        _proto=COMPLETE_PROTO
    )
    new_proto = complete_state._to_proto()

    assert new_proto == COMPLETE_PROTO
