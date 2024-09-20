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

import pytest
from unittest.mock import patch, mock_open
from AnkaiosSDK import Workload, WorkloadBuilder
from AnkaiosSDK._protos import _ank_base


@pytest.fixture
def workload():
    return Workload.builder() \
        .workload_name("workload_test") \
        .agent_name("agent_Test") \
        .runtime("runtime_test") \
        .restart_policy("NEVER") \
        .runtime_config("config_test") \
        .add_dependency("workload_test_other", "RUNNING") \
        .add_tag("key1", "value1") \
        .add_tag("key2", "value2") \
        .build()


def test_builder(workload):
    builder = workload.builder()
    assert builder is not None
    assert isinstance(builder, WorkloadBuilder)


def test_update_fields(workload):
    assert workload._get_masks() == ["desiredState.workloads.workload_test"]

    workload.update_workload_name("new_workload_test")
    assert workload.name == "new_workload_test"

    workload.update_agent_name("new_agent_Test")
    assert workload._workload.agent == "new_agent_Test"

    workload.update_runtime("new_runtime_test")
    assert workload._workload.runtime == "new_runtime_test"

    workload.update_runtime_config("new_config_test")
    assert workload._workload.runtimeConfig == "new_config_test"

    with patch("builtins.open", mock_open(read_data="new_config_test_from_file")):
        workload.update_runtime_config_from_file("new_config_test_from_file")
        assert workload._workload.runtimeConfig == "new_config_test_from_file"
    
    with pytest.raises(ValueError):
        workload.update_restart_policy("INVALID_POLICY")
    workload.update_restart_policy("ON_FAILURE")
    assert workload._workload.restartPolicy == _ank_base.ON_FAILURE


def test_dependencies(workload):
    assert len(workload.get_dependencies()) == 1

    with pytest.raises(ValueError):
        workload.add_dependency("other_workload_test", "DANCING")

    workload.add_dependency("other_workload_test", "SUCCEEDED")
    assert len(workload.get_dependencies()) == 2

    workload.add_dependency("another_workload_test", "FAILED")
    
    deps = workload.get_dependencies()
    assert len(deps) == 3
    deps.pop("other_workload_test")

    workload.update_dependencies(deps)
    assert len(workload.get_dependencies()) == 2


def test_tags(workload):
    assert len(workload.get_tags()) == 2

    # Allow duplicate tags
    workload.add_tag("key1", "new_value1")
    assert len(workload.get_tags()) == 3

    tags = workload.get_tags()
    tags = tags[1:]
    workload.update_tags(tags)

    assert len(workload.get_tags()) == 2


def test_proto(workload):
    proto = workload._to_proto()
    assert proto is not None
    assert proto.agent == "agent_Test"
    assert proto.runtime == "runtime_test"
    assert proto.restartPolicy == _ank_base.NEVER
    assert proto.runtimeConfig == "config_test"
    assert proto.dependencies.dependencies == {"workload_test_other": _ank_base.ADD_COND_RUNNING}
    assert proto.tags == _ank_base.Tags(tags=[
        _ank_base.Tag(key="key1", value="value1"), 
        _ank_base.Tag(key="key2", value="value2")
    ])

    new_workload = Workload("workload_test")
    new_workload._from_proto(proto)
    assert new_workload is not None
    assert str(workload) == str(new_workload)


def test_from_dict(workload):
    workload_dict = {
        "name": "workload_test",
        "agent": "agent_Test",
        "runtime": "runtime_test",
        "restartPolicy": "NEVER",
        "runtimeConfig": "config_test",
        "dependencies": {"workload_test_other": "RUNNING"},
        "tags": {"key1": "value1", "key2": "value2"}
    }

    new_workload = Workload._from_dict("workload_test", workload_dict)
    assert new_workload is not None
    assert str(workload) == str(new_workload)


@pytest.mark.parametrize("function_name, data, mask", [
    ("update_workload_name", {"name": "workload_test"}, "desiredState.workloads.workload_test"),
    ("update_agent_name", {"agent_name": "agent_Test"}, "desiredState.workloads.workload_test.agent"),
    ("update_runtime", {"runtime": "runtime_test"}, "desiredState.workloads.workload_test.runtime"),
    ("update_restart_policy", {"policy": "NEVER"}, "desiredState.workloads.workload_test.restartPolicy"),
    ("update_runtime_config", {"config": "config_test"}, "desiredState.workloads.workload_test.runtimeConfig"),
    ("add_dependency", {"workload_name": "workload_test_other", "condition": "RUNNING"}, "desiredState.workloads.workload_test.dependencies"),
    ("add_tag", {"key": "key1", "value": "value1"}, "desiredState.workloads.workload_test.tags"),
])
def test_mask_generation(function_name, data, mask):
    workload = Workload("workload_test")

    # Call function and assert the mask has been added
    getattr(workload, function_name)(**data)
    assert workload._get_masks() == [mask]

    # Updating the mask again should not add a new mask
    getattr(workload, function_name)(**data)
    assert len(workload._get_masks()) == 1
