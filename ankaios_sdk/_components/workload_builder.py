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

"""
This script defines the WorkloadBuilder class for
creating a Workload instance.

Classes
--------

- :class:`WorkloadBuilder`:
    A builder class to create a Workload object with a fluent interface.

Usage
------

- Create a workload using the WorkloadBuilder:
    .. code-block:: python

        workload = WorkloadBuilder() \\
            .workload_name("nginx") \\
            .agent_name("agent_A") \\
            .runtime("podman") \\
            .restart_policy("NEVER") \\
            .runtime_config("image: docker.io/library/nginx\\n"
                            + "commandOptions: [\\"-p\\", \\"8080:80\\"]") \\
            .add_dependency("other_workload", "ADD_COND_RUNNING") \\
            .add_tag("key1", "value1") \\
            .add_tag("key2", "value2") \\
            .build()
"""


__all__ = ["WorkloadBuilder"]


from .workload import Workload, AccessRightRule, File
from ..exceptions import WorkloadBuilderException


# pylint: disable=too-many-instance-attributes
class WorkloadBuilder:
    """
    A builder class to create a Workload object.

    :var str wl_name:
        The workload name.
    :var str wl_agent_name:
        The agent name.
    :var str wl_runtime:
        The runtime.
    :var str wl_runtime_config:
        The runtime configuration.
    :var str wl_restart_policy:
        The restart policy.
    :var dict dependencies:
        The dependencies.
    :var dict tags:
        The tags.
    :var list allow_rules:
        The list of allowed rules.
    :var list deny_rules:
        The list of denied rules.
    :var dict configs:
        The configs.
    :var list files:
        The files.
    """

    def __init__(self) -> None:
        """
        Initialize a WorkloadBuilder object.
        """
        self.wl_name = None
        self.wl_agent_name = None
        self.wl_runtime = None
        self.wl_runtime_config = None
        self.wl_restart_policy = None
        self.dependencies = {}
        self.tags = {}
        self.allow_rules = []
        self.deny_rules = []
        self.configs = {}
        self.files = []

    def workload_name(self, workload_name: str) -> "WorkloadBuilder":
        """
        Set the workload name.

        :param workload_name: The workload name to set.
        :type workload_name: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.wl_name = workload_name
        return self

    def agent_name(self, agent_name: str) -> "WorkloadBuilder":
        """
        Set the agent name.

        :param agent_name: The agent name to set.
        :type agent_name: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.wl_agent_name = agent_name
        return self

    def runtime(self, runtime: str) -> "WorkloadBuilder":
        """
        Set the runtime.

        :param runtime: The runtime to set.
        :type runtime: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.wl_runtime = runtime
        return self

    def runtime_config(self, runtime_config: str) -> "WorkloadBuilder":
        """
        Set the runtime configuration.

        :param runtime_config: The runtime configuration to set.
        :type runtime_config: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.wl_runtime_config = runtime_config
        return self

    def runtime_config_from_file(
        self, runtime_config_path: str
    ) -> "WorkloadBuilder":
        """
        Set the runtime configuration using a file.

        :param runtime_config_path: The path to the configuration file.
        :type runtime_config_path: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        with open(runtime_config_path, "r", encoding="utf-8") as file:
            self.wl_runtime_config = file.read()
        return self

    def restart_policy(self, restart_policy: str) -> "WorkloadBuilder":
        """
        Set the restart policy.

        :param restart_policy: The restart policy to set.
        :type restart_policy: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.wl_restart_policy = restart_policy
        return self

    def add_dependency(
        self, workload_name: str, condition: str
    ) -> "WorkloadBuilder":
        """
        Add a dependency.

        :param workload_name: The name of the dependent workload.
        :type workload_name: str
        :param condition: The condition for the dependency.
        :type condition: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.dependencies[workload_name] = condition
        return self

    def add_tag(self, key: str, value: str) -> "WorkloadBuilder":
        """
        Add a tag.

        :param key: The key of the tag.
        :type key: str
        :param value: The value of the tag.
        :type value: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.tags.update({key: value})
        return self

    def add_allow_state_rule(
        self, operation: str, filter_masks: list[str]
    ) -> "WorkloadBuilder":
        """
        Add an allow state rule to the workload.

        :param operation: The operation the rule allows.
        :type operation: str
        :param filter_masks: The list of filter masks.
        :type filter_masks: list

        :returns: The builder object.
        :rtype: WorkloadBuilder

        :raises WorkloadFieldException: If the operation is invalid.
        """
        self.allow_rules.append(
            AccessRightRule.state_rule(operation, filter_masks)
        )
        return self

    def add_deny_state_rule(
        self, operation: str, filter_masks: list[str]
    ) -> "WorkloadBuilder":
        """
        Add a deny state rule to the workload.

        :param operation: The operation the rule denies.
        :type operation: str
        :param filter_masks: The list of filter masks.
        :type filter_masks: list

        :returns: The builder object.
        :rtype: WorkloadBuilder

        :raises WorkloadFieldException: If the operation is invalid.
        """
        self.deny_rules.append(
            AccessRightRule.state_rule(operation, filter_masks)
        )
        return self

    def add_allow_log_rule(
        self, workload_names: list[str]
    ) -> "WorkloadBuilder":
        """
        Add an allow log rule to the workload.

        :param workload_names: The list of workload names the rule
            applies to.
        :type workload_names: list

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.allow_rules.append(AccessRightRule.log_rule(workload_names))
        return self

    def add_deny_log_rule(
        self, workload_names: list[str]
    ) -> "WorkloadBuilder":
        """
        Add an deny log rule to the workload.

        :param workload_names: The list of workload names the rule
            applies to.
        :type workload_names: list

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.deny_rules.append(AccessRightRule.log_rule(workload_names))
        return self

    def add_config(self, alias: str, name: str) -> "WorkloadBuilder":
        """
        Link a configuration to the workload.

        :param alias: The alias of the configuration.
        :type alias: str
        :param name: The name of the configuration.
        :type name: str

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.configs[alias] = name
        return self

    def add_file(self, file: File) -> "WorkloadBuilder":
        """
        Link a workload file to the workload.

        :param file: The file object to mount to the workload.
        :type file: File

        :returns: The builder object.
        :rtype: WorkloadBuilder
        """
        self.files.append(file)
        return self

    def build(self) -> Workload:
        """
        Build the Workload object.
        Required fields: workload name, agent name, runtime and
        runtime configuration.

        :returns: The built Workload object.
        :rtype: Workload

        :raises WorkloadBuilderException: If required fields are not set.
        """
        if self.wl_name is None:
            raise WorkloadBuilderException(
                "Workload can not be built without a name."
            )

        workload = Workload(self.wl_name)

        if self.wl_agent_name is None:
            raise WorkloadBuilderException(
                "Workload can not be built without an agent name."
            )
        if self.wl_runtime is None:
            raise WorkloadBuilderException(
                "Workload can not be built without a runtime."
            )
        if self.wl_runtime_config is None:
            raise WorkloadBuilderException(
                "Workload can not be built without a runtime configuration."
            )

        workload.update_agent_name(self.wl_agent_name)
        workload.update_runtime(self.wl_runtime)
        workload.update_runtime_config(self.wl_runtime_config)

        if self.wl_restart_policy is not None:
            workload.update_restart_policy(self.wl_restart_policy)
        if len(self.dependencies) > 0:
            workload.update_dependencies(self.dependencies)
        if len(self.tags) > 0:
            workload.update_tags(self.tags)
        if len(self.allow_rules) > 0:
            workload.update_allow_rules(self.allow_rules)
        if len(self.deny_rules) > 0:
            workload.update_deny_rules(self.deny_rules)
        if len(self.configs) > 0:
            workload.update_configs(self.configs)
        if len(self.files) > 0:
            workload.update_files(self.files)

        return workload
