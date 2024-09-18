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
        .agent_name("agent_Test") \
        .runtime("runtime_test") \
        .restart_policy("NEVER") \
        .runtime_config("config_test") \
        .add_dependency("workload_test", "RUNNING") \
        .add_tag("key1", "value1") \
        .add_tag("key2", "value2") \
        .build()

def test_builder(workload):
    builder = workload.builder()
    assert builder is not None
    assert isinstance(builder, WorkloadBuilder)

def test_update_fields(workload):
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
    assert proto.dependencies.dependencies == {"workload_test": _ank_base.ADD_COND_RUNNING}
    assert proto.tags == _ank_base.Tags(tags=[
        _ank_base.Tag(key="key1", value="value1"), 
        _ank_base.Tag(key="key2", value="value2")
    ])

    new_workload = Workload()
    new_workload._from_proto(proto)
    assert new_workload is not None
    assert str(workload) == str(new_workload)

@pytest.fixture
def builder():
    return WorkloadBuilder()

def test_workload_fields(builder):
    assert builder.agent_name("agent_Test") == builder
    assert builder.wl_agent_name == "agent_Test"
    
    assert builder.runtime("runtime_test") == builder
    assert builder.wl_runtime == "runtime_test"

    assert builder.runtime_config("config_test") == builder
    assert builder.wl_runtime_config == "config_test"

    with patch("builtins.open", mock_open(read_data="config_test_from_file")):
        assert builder.runtime_config_from_file("config_test_from_file") == builder
        assert builder.wl_runtime_config == "config_test_from_file"

    assert builder.restart_policy("NEVER") == builder
    assert builder.wl_restart_policy == "NEVER"

def test_add_dependency(builder):
    assert len(builder.dependencies) == 0

    assert builder.add_dependency("workload_test", "RUNNING") == builder
    assert builder.dependencies == {"workload_test": "RUNNING"}

    assert builder.add_dependency("workload_test_other", "RUNNING") == builder
    assert builder.dependencies == {"workload_test": "RUNNING", "workload_test_other": "RUNNING"}

def test_add_tag(builder):
    assert len(builder.tags) == 0

    assert builder.add_tag("key_test", "abc") == builder
    assert builder.tags == [("key_test", "abc")]

    assert builder.add_tag("key_test", "bcd") == builder
    assert builder.tags == [("key_test", "abc"), ("key_test", "bcd")]

def test_build(builder):
    with pytest.raises(ValueError, match="Workload can not be built without an agent name."):
        builder.build()
    builder.agent_name("agent_Test")

    with pytest.raises(ValueError, match="Workload can not be built without a runtime."):
        builder.build()
    builder.runtime("runtime_test")

    with pytest.raises(ValueError, match="Workload can not be built without a runtime configuration."):
        builder.build()
    builder.runtime_config("config_test")

    builder.restart_policy("NEVER")
    builder.add_dependency("workload_test", "RUNNING")
    builder.add_tag("key_test", "abc")
    
    workload = builder.build()

    assert workload is not None
    assert isinstance(workload, Workload)