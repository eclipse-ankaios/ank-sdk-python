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
This script defines the Workload and WorkloadBuilder classes for
creating and managing workloads.

Classes
--------

- Workload:
    Represents a workload with various attributes and methods to update them.
- WorkloadBuilder:
    A builder class to create a Workload object with a fluent interface.

Usage
------

- Create a workload using the WorkloadBuilder:
    .. code-block:: python

        workload = Workload.builder()
            .workload_name("nginx")
            .agent_name("agent_A")
            .runtime("podman")
            .restart_policy("NEVER")
            .runtime_config("image: docker.io/library/nginx\\n"
                            + "commandOptions: [\"-p\", \"8080:80\"]")
            .add_dependency("other_workload", "ADD_COND_RUNNING")
            .add_tag("key1", "value1")
            .add_tag("key2", "value2")
            .build()

- Update fields of the workload:
    .. code-block:: python

        workload.update_agent_name("agent_B")

- Update dependencies:
    .. code-block:: python

        deps = workload.get_dependencies()
        deps["other_workload"] = "ADD_COND_SUCCEEDED"
        workload.update_dependencies(deps)

- Update tags:
    .. code-block:: python

        tags = workload.get_tags()
        tags.pop("key1")
        workload.update_tags(tags)

- Print the updated workload:
    .. code-block:: python

        print(workload)
"""


__all__ = ["Workload", "WorkloadBuilder"]


from .._protos import _ank_base
from ..exceptions import WorkloadFieldException, WorkloadBuilderException


# pylint: disable=too-many-public-methods
class Workload:
    """
    A class to represent a workload.

    Attributes:
        name (str): The workload name.
    """
    def __init__(self, name: str) -> None:
        """
        Initialize a Workload object.

        The Workload object should be created using the
        Workload.builder() method.

        Args:
            name (str): The workload name.
        """
        self._workload = _ank_base.Workload()
        self.name = name
        self._main_mask = f"desiredState.workloads.{self.name}"
        self.masks = [self._main_mask]

    def __str__(self) -> str:
        """
        Return a string representation of the Workload object.

        Returns:
            str: String representation of the Workload object.
        """
        return str(self._to_proto())

    @staticmethod
    def builder() -> "WorkloadBuilder":
        """
        Return a WorkloadBuilder object.

        Returns:
            WorkloadBuilder: A builder object to create a Workload.
        """
        return WorkloadBuilder()

    def update_workload_name(self, name: str) -> None:
        """
        Set the workload name.

        Args:
            name (str): The workload name to update.
        """
        self.name = name
        self._add_mask(self._main_mask)

    def update_agent_name(self, agent_name: str) -> None:
        """
        Set the agent name for the workload.

        Args:
            agent_name (str): The agent name to update.
        """
        self._workload.agent = agent_name
        self._add_mask(f"{self._main_mask}.agent")

    def update_runtime(self, runtime: str) -> None:
        """
        Set the runtime for the workload.

        Args:
            runtime (str): The runtime to update.
        """
        self._workload.runtime = runtime
        self._add_mask(f"{self._main_mask}.runtime")

    def update_runtime_config(self, config: str) -> None:
        """
        Set the runtime-specific configuration for the workload.

        Args:
            config (str): The runtime configuration to update.
        """
        self._workload.runtimeConfig = config
        self._add_mask(f"{self._main_mask}.runtimeConfig")

    def update_runtime_config_from_file(self, config_file: str) -> None:
        """
        Set the runtime-specific configuration for the workload from a file.

        Args:
            config_file (str): The path to the configuration file.
        """
        with open(config_file, "r", encoding="utf-8") as file:
            self.update_runtime_config(file.read())

    def update_restart_policy(self, policy: str) -> None:
        """
        Set the restart policy for the workload.
        Supported values: `NEVER`, `ON_FAILURE`, `ALWAYS`.

        Args:
            policy (str): The restart policy to update.

        Raises:
            WorkloadFieldException: If an invalid restart policy is provided.
        """
        if policy not in _ank_base.RestartPolicy.keys():
            raise WorkloadFieldException(
                "restart policy", policy, _ank_base.RestartPolicy.keys()
            )
        self._workload.restartPolicy = _ank_base.RestartPolicy.Value(policy)
        self._add_mask(f"{self._main_mask}.restartPolicy")

    def get_dependencies(self) -> dict:
        """
        Return the dependencies of the workload.

        Returns:
            dict: A dictionary of dependencies with workload names \
                as keys and conditions as values.
        """
        deps = dict(self._workload.dependencies.dependencies)
        for dep in deps:
            deps[dep] = _ank_base.AddCondition.Name(deps[dep])
        return deps

    def update_dependencies(self, dependencies: dict[str, str]) -> None:
        """
        Update the dependencies of the workload.
        Supported conditions: `ADD_COND_RUNNING`, `ADD_COND_SUCCEEDED`,
        `ADD_COND_FAILED`.

        Args:
            dependencies (dict): A dictionary of dependencies with
                workload names and condition as values.

        Raises:
            WorkloadFieldException: If an invalid condition is provided.
        """
        self._workload.dependencies.dependencies.clear()
        for workload_name, condition in dependencies.items():
            if condition not in _ank_base.AddCondition.keys():
                raise WorkloadFieldException(
                    "dependency condition", condition,
                    _ank_base.AddCondition.keys()
                )
            self._workload.dependencies.dependencies[workload_name] = \
                _ank_base.AddCondition.Value(condition)
        self._add_mask(f"{self._main_mask}.dependencies")

    def add_tag(self, key: str, value: str) -> None:
        """
        Add a tag to the workload.

        Args:
            key (str): The key of the tag.
            value (str): The value of the tag.
        """
        tag = _ank_base.Tag(key=key, value=value)
        self._workload.tags.tags.append(tag)
        if f"{self._main_mask}.tags" not in self.masks:
            self._add_mask(f"{self._main_mask}.tags.{key}")

    def get_tags(self) -> list[tuple[str, str]]:
        """
        Return the tags of the workload.

        Returns:
            list: A list of tuples containing tag keys and values.
        """
        tags = []
        for tag in self._workload.tags.tags:
            tags.append((tag.key, tag.value))
        return tags

    def update_tags(self, tags: list) -> None:
        """
        Update the tags of the workload.

        Args:
            tags (list): A list of tuples containing tag keys and values.
        """
        while len(self._workload.tags.tags) > 0:
            self._workload.tags.tags.pop()
        for key, value in tags:
            tag = _ank_base.Tag(key=key, value=value)
            self._workload.tags.tags.append(tag)
        self.masks = [mask for mask in self.masks if not mask.startswith(
            f"{self._main_mask}.tags"
            )]
        self._add_mask(f"{self._main_mask}.tags")

    def _generate_access_right_rule(self,
                                    operation: str,
                                    filter_masks: list[str]
                                    ) -> _ank_base.AccessRightsRule:
        """
        Generate an access rights rule for the workload.

        Args:
            operation (str): The operation the rule allows.
            filter_masks (list): The list of filter masks.

        Returns:
            _ank_base.AccessRightsRule: The access rights rule generated.

        Raises:
            WorkloadFieldException: If an invalid operation is provided.
        """
        enum_mapper = {
            "Nothing": _ank_base.ReadWriteEnum.RW_NOTHING,
            "Write": _ank_base.ReadWriteEnum.RW_WRITE,
            "Read": _ank_base.ReadWriteEnum.RW_READ,
            "ReadWrite": _ank_base.ReadWriteEnum.RW_READ_WRITE,
        }
        if operation not in enum_mapper:
            raise WorkloadFieldException(
                "rule operation", operation, enum_mapper.keys()
            )
        return _ank_base.AccessRightsRule(
            stateRule=_ank_base.StateRule(
                operation=enum_mapper[operation],
                filterMasks=filter_masks
            )
        )

    def _access_right_rule_to_str(self, rule: _ank_base.AccessRightsRule
                                  ) -> tuple[str, list[str]]:
        """
        Convert an access rights rule to a tuple.

        Args:
            rule (_ank_base.AccessRightsRule): The access
                rights rule to convert.

        Returns:
            tuple: A tuple containing operation and filter masks.
        """
        enum_mapper = {
            _ank_base.ReadWriteEnum.RW_NOTHING: "Nothing",
            _ank_base.ReadWriteEnum.RW_WRITE: "Write",
            _ank_base.ReadWriteEnum.RW_READ: "Read",
            _ank_base.ReadWriteEnum.RW_READ_WRITE: "ReadWrite",
        }
        return (
            enum_mapper[rule.stateRule.operation],
            rule.stateRule.filterMasks
        )

    def get_allow_rules(self) -> list[tuple[str, list[str]]]:
        """
        Return the allow rules of the workload.

        Returns:
            list: A list of tuples containing operation and filter masks.
        """
        rules = []
        for rule in self._workload.controlInterfaceAccess.allowRules:
            rules.append(self._access_right_rule_to_str(rule))
        return rules

    def update_allow_rules(self, rules: list[tuple[str, list[str]]]) -> None:
        """
        Update the allow rules of the workload.
        Supported values: `Nothing`, `Write`, `Read`, `ReadWrite`.

        Args:
            rules (list): A list of tuples containing
                operation and filter masks.

        Raises:
            WorkloadFieldException: If an invalid operation is provided
        """
        while len(self._workload.controlInterfaceAccess.allowRules) > 0:
            self._workload.controlInterfaceAccess.allowRules.pop()
        for operation, filter_masks in rules:
            self._workload.controlInterfaceAccess.allowRules.append(
                self._generate_access_right_rule(operation, filter_masks)
            )
        self._add_mask(f"{self._main_mask}.controlInterfaceAccess.allowRules")

    def get_deny_rules(self) -> list[tuple[str, list[str]]]:
        """
        Return the deny rules of the workload.

        Returns:
            list: A list of tuples containing operation and filter masks.
        """
        rules = []
        for rule in self._workload.controlInterfaceAccess.denyRules:
            rules.append(self._access_right_rule_to_str(rule))
        return rules

    def update_deny_rules(self, rules: list[tuple[str, list[str]]]) -> None:
        """
        Update the deny rules of the workload.
        Supported values: `Nothing`, `Write`, `Read`, `ReadWrite`.

        Args:
            rules (list): A list of tuples containing
                operation and filter masks.

        Raises:
            WorkloadFieldException: If an invalid operation is provided
        """
        while len(self._workload.controlInterfaceAccess.denyRules) > 0:
            self._workload.controlInterfaceAccess.denyRules.pop()
        for operation, filter_masks in rules:
            self._workload.controlInterfaceAccess.denyRules.append(
                self._generate_access_right_rule(operation, filter_masks)
            )
        self._add_mask(f"{self._main_mask}.controlInterfaceAccess.denyRules")

    def add_config(self, alias: str, name: str) -> None:
        """
        Link a configuration to the workload.

        Args:
            alias (str): The alias of the configuration.
            name (str): The name of the configuration.
        """
        self._workload.configs.configs[alias] = name
        # Currently the mask is for all configs, not for individual aliases
        self._add_mask(f"{self._main_mask}.configs")

    def get_configs(self) -> dict[str, str]:
        """
        Return the configurations linked to the workload.

        Returns:
            dict[str, str]: A dict containing the alias as key and name of the
                configuration as value.
        """
        config_mappings = {}
        for alias, name in self._workload.configs.configs.items():
            config_mappings[alias] = name
        return config_mappings

    def update_configs(self, configs: dict[str, str]) -> None:
        """
        Update the configurations linked to the workload.

        Args:
            configs (dict[str, str]): A tuple containing the alias and
                name of the configurations.
        """
        self._workload.configs.configs.clear()
        for alias, name in configs.items():
            self.add_config(alias, name)

    def _add_mask(self, mask: str) -> None:
        """
        Add a mask to the list of masks.

        Args:
            mask (str): The mask to add.
        """
        if self._main_mask not in self.masks and mask not in self.masks:
            self.masks.append(mask)

    # pylint: disable=too-many-branches
    @staticmethod
    def _from_dict(workload_name: str, dict_workload: dict) -> "Workload":
        """
        Convert a dictionary to a Workload object.

        Args:
            workload_name (str): The name of the workload.
            dict_workload (dict): The dictionary to convert.

        Returns:
            Workload: The Workload object created from the dictionary.
        """
        workload = Workload.builder().workload_name(workload_name)
        if "agent" in dict_workload:
            workload = workload.agent_name(dict_workload["agent"])
        if "runtime" in dict_workload:
            workload = workload.runtime(dict_workload["runtime"])
        if "runtimeConfig" in dict_workload:
            workload = workload.runtime_config(dict_workload["runtimeConfig"])
        if "restartPolicy" in dict_workload:
            workload = workload.restart_policy(dict_workload["restartPolicy"])
        if "dependencies" in dict_workload:
            for dep_key, dep_value in dict_workload["dependencies"].items():
                workload = workload.add_dependency(dep_key, dep_value)
        if "tags" in dict_workload:
            for tag in dict_workload["tags"]:
                workload = workload.add_tag(tag["key"], tag["value"])
        if "controlInterfaceAccess" in dict_workload:
            if "allowRules" in dict_workload["controlInterfaceAccess"]:
                for rule in dict_workload[
                        "controlInterfaceAccess"][
                        "allowRules"
                        ]:
                    workload = workload.add_allow_rule(
                        rule["operation"], rule["filterMask"]
                    )
            if "denyRules" in dict_workload["controlInterfaceAccess"]:
                for rule in dict_workload[
                        "controlInterfaceAccess"][
                        "denyRules"
                        ]:
                    workload = workload.add_deny_rule(
                        rule["operation"], rule["filterMask"]
                    )
        if "configs" in dict_workload:
            for alias, name in dict_workload["configs"].items():
                workload = workload.add_config(alias, name)

        return workload.build()

    def _to_proto(self) -> _ank_base.Workload:
        """
        Convert the Workload object to a proto message.

        Returns:
            _ank_base.Workload: The proto message representation
                of the Workload object.
        """
        return self._workload

    def _from_proto(self, proto: _ank_base.Workload) -> None:
        """
        Convert the proto message to a Workload object.

        Args:
            proto (_ank_base.Workload): The proto message to convert.
        """
        self._workload = proto
        self.masks = []


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

    def add_allow_rule(
            self, operation: str, filter_masks: list[str]
            ) -> "WorkloadBuilder":
        """
        Add an allow rule to the workload.

        Args:
            operation (str): The operation the rule allows.
            filter_masks (list): The list of filter masks.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.allow_rules.append((operation, filter_masks))
        return self

    def add_deny_rule(
            self, operation: str, filter_masks: list[str]
            ) -> "WorkloadBuilder":
        """
        Add a deny rule to the workload.

        Args:
            operation (str): The operation the rule denies.
            filter_masks (list): The list of filter masks.

        Returns:
            WorkloadBuilder: The builder object.
        """
        self.deny_rules.append((operation, filter_masks))
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
