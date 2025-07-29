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
This module contains unit tests for the WorkloadBuilder
class in the ankaios_sdk.

Fixtures:
    builder: Returns a WorkloadBuilder instance.
"""

from unittest.mock import patch, mock_open
import pytest
from ankaios_sdk import (Workload, WorkloadBuilder,
                         WorkloadBuilderException, File)
from ankaios_sdk._components.file import Data, BinaryData
from ankaios_sdk._protos import _ank_base


@pytest.fixture
def builder():
    """
    Fixture that returns a WorkloadBuilder instance.

    Returns:
        WorkloadBuilder: A WorkloadBuilder instance.
    """
    return WorkloadBuilder()


def test_workload_fields(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test setting various fields of the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    assert builder.agent_name("agent_Test") == builder
    assert builder.wl_agent_name == "agent_Test"

    assert builder.runtime("runtime_test") == builder
    assert builder.wl_runtime == "runtime_test"

    assert builder.runtime_config("config_test") == builder
    assert builder.wl_runtime_config == "config_test"

    with patch("builtins.open", mock_open(read_data="config_test_from_file")):
        assert builder.runtime_config_from_file(
            "config_test_from_file"
            ) == builder
        assert builder.wl_runtime_config == "config_test_from_file"

    assert builder.restart_policy("NEVER") == builder
    assert builder.wl_restart_policy == "NEVER"


def test_add_dependency(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test adding dependencies to the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    assert len(builder.dependencies) == 0

    assert builder.add_dependency(
        "workload_test", "ADD_COND_RUNNING"
        ) == builder
    assert builder.dependencies == {"workload_test": "ADD_COND_RUNNING"}

    assert builder.add_dependency(
        "workload_test_other", "ADD_COND_RUNNING"
        ) == builder
    assert builder.dependencies == {"workload_test": "ADD_COND_RUNNING",
                                    "workload_test_other": "ADD_COND_RUNNING"}


def test_add_tag(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test adding tags to the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    assert len(builder.tags) == 0

    assert builder.add_tag("key_test", "abc") == builder
    assert builder.tags == [("key_test", "abc")]

    assert builder.add_tag("key_test", "bcd") == builder
    assert builder.tags == [("key_test", "abc"), ("key_test", "bcd")]


def test_add_rule(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test adding rules to the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    assert len(builder.allow_rules) == 0

    assert builder.add_allow_rule("Write", ["mask"]) == builder
    assert builder.allow_rules == [("Write", ["mask"])]

    assert len(builder.deny_rules) == 0

    assert builder.add_deny_rule("Read", ["mask"]) == builder
    assert builder.deny_rules == [("Read", ["mask"])]


def test_add_config(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test adding configurations to the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    assert len(builder.configs) == 0

    assert builder.add_config("alias_Test", "config1") == builder
    assert builder.configs == {"alias_Test": "config1"}


def test_add_file(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test adding files to the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    assert len(builder.files) == 0

    assert builder.add_file(File.from_data(
        "file_mount_point", data="file_content")
    ) == builder
    assert builder.add_file(File.from_binary_data(
        "file_mount_point", binary_data="ialsdfvJKGU65e")
    ) == builder
    assert builder.files[0].mount_point == "file_mount_point"
    assert builder.files[0].content == Data(value="file_content")
    assert builder.files[1].mount_point == "file_mount_point"
    assert builder.files[1].content == BinaryData(value="ialsdfvJKGU65e")


def test_build(
        builder: WorkloadBuilder
        ):  # pylint: disable=redefined-outer-name
    """
    Test building a Workload instance from the WorkloadBuilder instance.

    Args:
        builder (WorkloadBuilder): The WorkloadBuilder fixture.
    """
    with pytest.raises(
            WorkloadBuilderException,
            match="Workload can not be built without a name."
            ):
        builder.build()
    builder = builder.workload_name("workload_test")

    with pytest.raises(
            WorkloadBuilderException,
            match="Workload can not be built without an agent name."
            ):
        builder.build()
    builder = builder.agent_name("agent_Test")

    with pytest.raises(
            WorkloadBuilderException,
            match="Workload can not be built without a runtime."
            ):
        builder.build()
    builder = builder.runtime("runtime_test")

    with pytest.raises(
            WorkloadBuilderException,
            match="Workload can not be built without a runtime configuration."
            ):
        builder.build()

    workload = builder.runtime_config("config_test") \
        .restart_policy("NEVER") \
        .add_dependency("workload_test_other", "ADD_COND_RUNNING") \
        .add_tag("key_test", "abc") \
        .add_allow_rule("Write", ["mask"]) \
        .build()

    assert workload is not None
    assert isinstance(workload, Workload)

    assert workload.name == "workload_test"
    assert workload._workload.agent == "agent_Test"
    assert workload._workload.runtime == "runtime_test"
    assert workload._workload.runtimeConfig == "config_test"
    assert workload._workload.restartPolicy == _ank_base.RestartPolicy.NEVER
    assert workload._workload.dependencies == _ank_base.Dependencies(
        dependencies={"workload_test_other":
                      _ank_base.AddCondition.ADD_COND_RUNNING}
        )
    assert workload._workload.tags == _ank_base.Tags(
        tags=[_ank_base.Tag(key="key_test", value="abc")]
        )
    assert workload._workload.controlInterfaceAccess.allowRules == [
        _ank_base.AccessRightsRule(
            stateRule=_ank_base.StateRule(
                operation=_ank_base.ReadWriteEnum.RW_WRITE,
                filterMasks=["mask"]
            )
        )]
