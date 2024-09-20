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
    with pytest.raises(ValueError, match="Workload can not be built without a name."):
        builder.build()
    builder = builder.workload_name("workload_test")

    with pytest.raises(ValueError, match="Workload can not be built without an agent name."):
        builder.build()
    builder = builder.agent_name("agent_Test")

    with pytest.raises(ValueError, match="Workload can not be built without a runtime."):
        builder.build()
    builder = builder.runtime("runtime_test")

    with pytest.raises(ValueError, match="Workload can not be built without a runtime configuration."):
        builder.build()

    workload = builder.runtime_config("config_test") \
        .restart_policy("NEVER") \
        .add_dependency("workload_test_other", "RUNNING") \
        .add_tag("key_test", "abc") \
        .build()

    assert workload is not None
    assert isinstance(workload, Workload)
