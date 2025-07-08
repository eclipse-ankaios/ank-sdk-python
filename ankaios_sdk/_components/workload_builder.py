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

- WorkloadBuilder:
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


from .workload import Workload, AccessRightRule
from ..exceptions import WorkloadBuilderException


# pylint: disable=too-many-instance-attributes
class WorkloadBuilder:
    """
    A builder class to create a Workload object.

    Attributes:
        wl_name (str): The workload name.
        wl_agent_name (str): The agent name.
        wl_runtime (str): The runtime.
        wl_runtime_config (str): The runtime configuration.
        wl_restart_policy (str): The restart policy.
        dependencies (dict): The dependencies.
        tags (list): The tags.
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
        self.tags = []
        self.allow_rules = []
        self.deny_rules = []
        self.configs = {}

    def workload_name(self, workload_name: str) -> "WorkloadBuilder":
        """
        Set the workload name.

        Args:
            workload_name (str): The workload name to set.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.wl_name = workload_name
        return self

    def agent_name(self, agent_name: str) -> "WorkloadBuilder":
        """
        Set the agent name.

        Args:
            agent_name (str): The agent name to set.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.wl_agent_name = agent_name
        return self

    def runtime(self, runtime: str) -> "WorkloadBuilder":
        """
        Set the runtime.

        Args:
            runtime (str): The runtime to set.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.wl_runtime = runtime
        return self

    def runtime_config(self, runtime_config: str) -> "WorkloadBuilder":
        """
        Set the runtime configuration.

        Args:
            runtime_config (str): The runtime configuration to set.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.wl_runtime_config = runtime_config
        return self

    def runtime_config_from_file(
            self, runtime_config_path: str
            ) -> "WorkloadBuilder":
        """
        Set the runtime configuration using a file.

        Args:
            runtime_config_path (str): The path to the configuration file.

        Returns:
            WorkloadBuilder: The builder object.
        """
        with open(runtime_config_path, "r", encoding="utf-8") as file:
            self.wl_runtime_config = file.read()
        return self

    def restart_policy(self, restart_policy: str) -> "WorkloadBuilder":
        """
        Set the restart policy.

        Args:
            restart_policy (str): The restart policy to set.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.wl_restart_policy = restart_policy
        return self

    def add_dependency(
            self, workload_name: str, condition: str
            ) -> "WorkloadBuilder":
        """
        Add a dependency.

        Args:
            workload_name (str): The name of the dependent workload.
            condition (str): The condition for the dependency.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.dependencies[workload_name] = condition
        return self

    def add_tag(self, key: str, value: str) -> "WorkloadBuilder":
        """
        Add a tag.

        Args:
            key (str): The key of the tag.
            value (str): The value of the tag.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.tags.append((key, value))
        return self

    def add_allow_state_rule(
            self, operation: str, filter_masks: list[str]
            ) -> "WorkloadBuilder":
        """
        Add an allow state rule to the workload.

        Args:
            operation (str): The operation the rule allows.
            filter_masks (list): The list of filter masks.

        Returns:
            WorkloadBuilder: The builder object.

        Raises:
            WorkloadFieldException: If the operation is invalid.
        """
        self.allow_rules.append(AccessRightRule.state_rule(
            operation, filter_masks
        ))
        return self

    def add_deny_state_rule(
            self, operation: str, filter_masks: list[str]
            ) -> "WorkloadBuilder":
        """
        Add a deny state rule to the workload.

        Args:
            operation (str): The operation the rule denies.
            filter_masks (list): The list of filter masks.

        Returns:
            WorkloadBuilder: The builder object.

        Raises:
            WorkloadFieldException: If the operation is invalid.
        """
        self.deny_rules.append(AccessRightRule.state_rule(
            operation, filter_masks
        ))
        return self

    def add_allow_log_rule(
            self, workload_names: list[str]
            ) -> "WorkloadBuilder":
        """
        Add an allow log rule to the workload.

        Args:
            workload_names (list): The list of workload names the rule
                applies to.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.allow_rules.append(AccessRightRule.log_rule(
            workload_names
        ))
        return self

    def add_deny_log_rule(
            self, workload_names: list[str]
            ) -> "WorkloadBuilder":
        """
        Add an deny log rule to the workload.

        Args:
            workload_names (list): The list of workload names the rule
                applies to.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.deny_rules.append(AccessRightRule.log_rule(
            workload_names
        ))
        return self

    def add_config(self, alias: str, name: str) -> "WorkloadBuilder":
        """
        Link a configuration to the workload.

        Args:
            alias (str): The alias of the configuration.
            name (str): The name of the configuration.
        """
        self.configs[alias] = name
        return self

    def build(self) -> Workload:
        """
        Build the Workload object.
        Required fields: workload name, agent name, runtime and
        runtime configuration.

        Returns:
            Workload: The built Workload object.

        Raises:
            WorkloadBuilderException: If required fields are not set.
        """
        if self.wl_name is None:
            raise WorkloadBuilderException(
                "Workload can not be built without a name.")

        workload = Workload(self.wl_name)

        if self.wl_agent_name is None:
            raise WorkloadBuilderException(
                "Workload can not be built without an agent name.")
        if self.wl_runtime is None:
            raise WorkloadBuilderException(
                "Workload can not be built without a runtime.")
        if self.wl_runtime_config is None:
            raise WorkloadBuilderException(
                "Workload can not be built without a runtime configuration.")

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

        return workload
