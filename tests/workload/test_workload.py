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
This module contains unit tests for the Workload class in the ankaios_sdk.

Fixtures:
    workload: Returns a Workload instance with some default values.

Helper Functions:
    generate_workload: Helper function to generate a Workload instance
        with some default values.
"""

from unittest.mock import patch, mock_open
import pytest
from ankaios_sdk import (
    Workload,
    WorkloadBuilder,
    WorkloadFieldException,
    AccessRightRule,
    File,
)
from ankaios_sdk._protos import _ank_base
from ankaios_sdk.utils import WORKLOADS_PREFIX


WORKLOAD_PROTO = _ank_base.WorkloadMap(
    workloads={
        "dynamic_nginx": _ank_base.Workload(
            agent="agent_A",
            runtime="podman",
            runtimeConfig=r"image: control_interface_prod:0.1\n",
            restartPolicy=_ank_base.ALWAYS,
            tags=_ank_base.Tags(
                tags=[_ank_base.Tag(key="owner", value="Ankaios team")]
            ),
            dependencies=_ank_base.Dependencies(
                dependencies={"nginx": _ank_base.ADD_COND_RUNNING}
            ),
            controlInterfaceAccess=_ank_base.ControlInterfaceAccess(
                allowRules=[
                    _ank_base.AccessRightsRule(
                        stateRule=_ank_base.StateRule(
                            operation=_ank_base.RW_WRITE,
                            filterMasks=[
                                "desiredState.workloads.dynamic_nginx"
                            ],
                        )
                    ),
                    _ank_base.AccessRightsRule(
                        logRule=_ank_base.LogRule(workloadNames=["nginx"])
                    ),
                ],
                denyRules=[
                    _ank_base.AccessRightsRule(
                        stateRule=_ank_base.StateRule(
                            operation=_ank_base.RW_READ,
                            filterMasks=[
                                "desiredState.workloads.dynamic_nginx"
                            ],
                        )
                    )
                ],
            ),
            configs=_ank_base.ConfigMappings(
                configs={
                    "str": "config_1",
                    "array": "config_2",
                    "dict": "config_3",
                }
            ),
            files=_ank_base.Files(
                files=[
                    _ank_base.File(mountPoint="./mount_point", data="data_1"),
                    _ank_base.File(
                        mountPoint="./mount_point_2",
                        binaryData="binary_data_1",
                    ),
                ]
            ),
        )
    }
)


def generate_test_workload(workload_name: str = "workload_test") -> Workload:
    """
    Helper function to generate a Workload instance with some default values.

    Returns:
        Workload: A Workload instance.
    """
    return (
        Workload.builder()
        .workload_name(workload_name)
        .agent_name("agent_Test")
        .runtime("runtime_test")
        .restart_policy("NEVER")
        .runtime_config("config_test")
        .add_dependency("workload_test_other", "ADD_COND_RUNNING")
        .add_tag("key1", "value1")
        .add_tag("key2", "value2")
        .add_allow_state_rule(
            "Write", [f"{WORKLOADS_PREFIX}.another_workload"]
        )
        .add_deny_state_rule(
            "Read", ["workloadStates.agent_Test.another_workload"]
        )
        .add_config("alias_test", "config1")
        .add_file(File.from_data("./dummy_mount_point", data="dummy_data"))
        .build()
    )


@pytest.fixture
def workload() -> Workload:
    """
    Fixture that returns a Workload instance with some default values.

    Returns:
        Workload: A Workload instance.
    """
    return generate_test_workload()


def test_builder(workload):  # pylint: disable=redefined-outer-name
    """
    Test the builder method of the Workload class.

    Args:
        workload (Workload): The Workload fixture.
    """
    builder = workload.builder()
    assert builder is not None
    assert isinstance(builder, WorkloadBuilder)


def test_update_fields(
    workload: Workload,
):  # pylint: disable=redefined-outer-name
    """
    Test updating various fields of the Workload instance.

    Args:
        workload (Workload): The Workload fixture.
    """
    assert workload.masks == [f"{WORKLOADS_PREFIX}.workload_test"]

    workload.update_workload_name("new_workload_test")
    assert workload.name == "new_workload_test"

    workload.update_agent_name("new_agent_Test")
    assert workload._workload.agent == "new_agent_Test"

    workload.update_runtime("new_runtime_test")
    assert workload._workload.runtime == "new_runtime_test"

    workload.update_runtime_config("new_config_test")
    assert workload._workload.runtimeConfig == "new_config_test"

    with patch(
        "builtins.open", mock_open(read_data="new_config_test_from_file")
    ):
        workload.update_runtime_config_from_file("new_config_test_from_file")
        assert workload._workload.runtimeConfig == "new_config_test_from_file"

    with pytest.raises(WorkloadFieldException):
        workload.update_restart_policy("INVALID_POLICY")
    workload.update_restart_policy("ON_FAILURE")
    assert workload._workload.restartPolicy == _ank_base.ON_FAILURE


def test_dependencies(
    workload: Workload,
):  # pylint: disable=redefined-outer-name
    """
    Test adding and updating dependencies of the Workload instance.

    Args:
        workload (Workload): The Workload fixture.
    """
    deps = workload.get_dependencies()
    assert len(deps) == 1
    deps["other_workload_test"] = "ADD_COND_SUCCEEDED"

    with pytest.raises(WorkloadFieldException):
        workload.update_dependencies(
            {"other_workload_test": "ADD_COND_DANCING"}
        )

    workload.update_dependencies(deps)
    assert len(workload.get_dependencies()) == 2

    deps.pop("other_workload_test")
    workload.update_dependencies(deps)
    assert len(workload.get_dependencies()) == 1


def test_tags(workload: Workload):  # pylint: disable=redefined-outer-name
    """
    Test adding and updating tags of the Workload instance.

    Args:
        workload (Workload): The Workload fixture.
    """
    assert len(workload.get_tags()) == 2

    # Allow duplicate tags
    workload.add_tag("key1", "new_value1")
    assert len(workload.get_tags()) == 3

    tags = workload.get_tags()
    tags = tags[1:]
    workload.update_tags(tags)

    assert len(workload.get_tags()) == 2


def test_rules(workload: Workload):  # pylint: disable=redefined-outer-name
    """
    Test adding and updating allow and deny rules of the Workload instance.

    Args:
        workload (Workload): The Workload fixture.
    """
    allow_rules = workload.get_allow_rules()
    deny_rules = workload.get_deny_rules()
    print([str(elem) for elem in allow_rules])
    assert len(allow_rules) == 1
    assert len(deny_rules) == 1

    with pytest.raises(WorkloadFieldException):
        workload.update_allow_rules(
            [AccessRightRule.state_rule("Invalid", ["mask"])]
        )

    with pytest.raises(WorkloadFieldException):
        workload.update_deny_rules(
            [AccessRightRule.state_rule("Invalid", ["mask"])]
        )

    allow_rules.append(
        AccessRightRule.state_rule(
            "Write", [f"{WORKLOADS_PREFIX}.another_workload"]
        )
    )
    deny_rules.append(
        AccessRightRule.state_rule(
            "Read", ["workloadStates.agent_Test.another_workload"]
        )
    )

    workload.update_allow_rules(allow_rules)
    workload.update_deny_rules(deny_rules)

    assert len(workload.get_allow_rules()) == 2
    assert len(workload.get_deny_rules()) == 2


def test_configs(workload: Workload):  # pylint: disable=redefined-outer-name
    """
    Test adding and updating configurations of the Workload instance.

    Args:
        workload (Workload): The Workload fixture.
    """
    assert len(workload.get_configs()) == 1

    workload.add_config("alias_other", "config2")
    configs = workload.get_configs()
    assert len(configs) == 2

    configs["alias_new"] = "config3"
    workload.update_configs(configs)

    assert len(workload.get_configs()) == 3


def test_files(workload: Workload):  # pylint: disable=redefined-outer-name
    """
    Test adding and updating files of the Workload instance.
    Args:
        workload (Workload): The Workload fixture.
    """
    assert len(workload.get_files()) == 1

    print(workload)

    workload.add_file(File.from_data("./new_mount_point", data="new_data"))
    files = workload.get_files()
    assert len(files) == 2

    files.append(
        File.from_binary_data(
            "./another_new_mount_point",
            binary_data="Asday9843uf092ASASASXZXZ90u988huj",
        )
    )
    workload.update_files(files)
    assert len(workload.get_files()) == 3

    workload.update_files(
        [File.from_data("./replaced_mount_point", data="replaced_data")]
    )
    assert len(workload.get_files()) == 1


def test_to_proto(workload: Workload):  # pylint: disable=redefined-outer-name
    """
    Test converting the Workload instance to protobuf message.

    Args:
        workload (Workload): The Workload fixture.
    """
    proto = workload._to_proto()
    assert proto is not None
    assert proto.agent == "agent_Test"
    assert proto.runtime == "runtime_test"
    assert proto.restartPolicy == _ank_base.NEVER
    assert proto.runtimeConfig == "config_test"
    assert proto.dependencies.dependencies == {
        "workload_test_other": _ank_base.ADD_COND_RUNNING
    }
    assert proto.tags == _ank_base.Tags(
        tags=[
            _ank_base.Tag(key="key1", value="value1"),
            _ank_base.Tag(key="key2", value="value2"),
        ]
    )


def test_proto():
    """
    Test converting the workload to and from a proto.
    """
    workload_new = Workload("workload_test")
    workload_new._from_proto(WORKLOAD_PROTO)
    assert workload_new._to_proto() == WORKLOAD_PROTO


def test_from_to_dict():
    """Test converting a Workload instance to and from a dictionary."""
    workload_new = generate_test_workload()

    workload_other = Workload._from_dict(
        workload_new.name, workload_new.to_dict()
    )

    assert str(workload_new) == str(workload_other)


@pytest.mark.parametrize(
    "function_name, data, mask",
    [
        (
            "update_workload_name",
            {"name": "workload_test"},
            f"{WORKLOADS_PREFIX}.workload_test",
        ),
        (
            "update_agent_name",
            {"agent_name": "agent_Test"},
            f"{WORKLOADS_PREFIX}.workload_test.agent",
        ),
        (
            "update_runtime",
            {"runtime": "runtime_test"},
            f"{WORKLOADS_PREFIX}.workload_test.runtime",
        ),
        (
            "update_restart_policy",
            {"policy": "NEVER"},
            f"{WORKLOADS_PREFIX}.workload_test.restartPolicy",
        ),
        (
            "update_runtime_config",
            {"config": "config_test"},
            f"{WORKLOADS_PREFIX}.workload_test.runtimeConfig",
        ),
        (
            "update_dependencies",
            {"dependencies": {"workload_test_other": "ADD_COND_RUNNING"}},
            f"{WORKLOADS_PREFIX}.workload_test.dependencies",
        ),
        (
            "add_tag",
            {"key": "key1", "value": "value1"},
            f"{WORKLOADS_PREFIX}.workload_test.tags.key1",
        ),
        (
            "update_tags",
            {"tags": [("key1", "value1"), ("key2", "value2")]},
            f"{WORKLOADS_PREFIX}.workload_test.tags",
        ),
        (
            "update_allow_rules",
            {"rules": [AccessRightRule.state_rule("Write", ["mask"])]},
            f"{WORKLOADS_PREFIX}.workload_test."
            + "controlInterfaceAccess.allowRules",
        ),
        (
            "update_deny_rules",
            {"rules": [AccessRightRule.state_rule("Read", ["mask"])]},
            f"{WORKLOADS_PREFIX}.workload_test."
            + "controlInterfaceAccess.denyRules",
        ),
        (
            "add_config",
            {"alias": "alias_test", "name": "config_test"},
            f"{WORKLOADS_PREFIX}.workload_test.configs",
        ),
        (
            "add_file",
            {"file": File.from_data("./dummy_mount_point", data="dummy_data")},
            f"{WORKLOADS_PREFIX}.workload_test.files",
        ),
    ],
)
def test_mask_generation(function_name: str, data: dict, mask: str):
    """
    Test the generation of masks when updating fields of the Workload instance.

    Args:
        function_name (str): The name of the function to call on
            the Workload instance.
        data (dict): The data to pass to the function.
        mask (str): The expected mask to be generated.
    """
    my_workload = Workload("workload_test")
    my_workload.masks = []

    # Call function and assert the mask has been added
    getattr(my_workload, function_name)(**data)
    assert my_workload.masks == [mask]

    # Updating the mask again should not add a new mask
    getattr(my_workload, function_name)(**data)
    assert len(my_workload.masks) == 1
