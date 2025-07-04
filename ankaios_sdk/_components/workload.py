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
This script defines the Workload class for creating and managing workloads and
the AccessRightRule class for managing access rights.

Classes
--------

- Workload:
    Represents a workload with various attributes and methods to update them.
- AccessRightRule:
    Represents an access right rule for a workload. It can be either a
    state rule or a log rule.

Usage
------

- Create a workload using the WorkloadBuilder:
    .. code-block:: python

        workload = Workload.builder().build()

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

- Create an access state rule:
    .. code-block:: python

        rule = AccessRightRule.state_rule("Read", ["*"])

- Create an access log rule:
    .. code-block:: python

        rule = AccessRightRule.log_rule(['workload_A'])
"""


__all__ = ["Workload", "AccessRightRule"]

from typing import TYPE_CHECKING
from .._protos import _ank_base
from ..exceptions import WorkloadFieldException
from ..utils import get_logger, WORKLOADS_PREFIX


logger = get_logger()
if TYPE_CHECKING:
    from .workload_builder import WorkloadBuilder # pragma: no cover


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
        self._main_mask = f"{WORKLOADS_PREFIX}.{self.name}"
        self.masks = [self._main_mask]

    def __str__(self) -> str:
        """
        Return a string representation of the Workload object.

        Returns:
            str: String representation of the Workload object.
        """
        return str(self._to_proto())

    @staticmethod
    def builder() -> 'WorkloadBuilder':
        """
        Return a WorkloadBuilder object.

        Returns:
            WorkloadBuilder: A builder object to create a Workload.
        """
        from .workload_builder import WorkloadBuilder
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
            logger.error(
                "Invalid restart policy provided.")
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
                logger.error(
                    "Invalid dependency condition provided.")
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
        del self._workload.tags.tags[:]
        for key, value in tags:
            tag = _ank_base.Tag(key=key, value=value)
            self._workload.tags.tags.append(tag)
        self.masks = [mask for mask in self.masks if not mask.startswith(
            f"{self._main_mask}.tags"
            )]
        self._add_mask(f"{self._main_mask}.tags")

    def get_allow_rules(self) -> list['AccessRightRule']:
        """
        Return the allow rules of the workload.

        Returns:
            list: A list of AccessRightRules
        """
        rules = []
        for rule in self._workload.controlInterfaceAccess.allowRules:
            rules.append(AccessRightRule(rule))
        return rules

    def update_allow_rules(self, rules: list['AccessRightRule']) -> None:
        """
        Update the allow rules of the workload.

        Args:
            rules (list): A list of AccessRightRules.
        """
        del self._workload.controlInterfaceAccess.allowRules[:]
        for rule in rules:
            self._workload.controlInterfaceAccess.allowRules.append(
                rule._to_proto()
            )
        self._add_mask(f"{self._main_mask}.controlInterfaceAccess.allowRules")

    def get_deny_rules(self) -> list['AccessRightRule']:
        """
        Return the deny rules of the workload.

        Returns:
            list: A list of AccessRightRules
        """
        rules = []
        for rule in self._workload.controlInterfaceAccess.denyRules:
            rules.append(AccessRightRule(rule))
        return rules

    def update_deny_rules(self, rules: list['AccessRightRule']) -> None:
        """
        Update the deny rules of the workload.

        Args:
            rules (list): A list of AccessRightRules.
        """
        del self._workload.controlInterfaceAccess.denyRules[:]
        for rule in rules:
            self._workload.controlInterfaceAccess.denyRules.append(
                rule._to_proto()
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

    def to_dict(self) -> dict:
        """
        Convert the Workload object to a dictionary.

        Returns:
            dict: The dictionary representation of the Workload object.
        """
        workload_dict = {}
        if self._workload.agent:
            workload_dict["agent"] = self._workload.agent
        if self._workload.runtime:
            workload_dict["runtime"] = self._workload.runtime
        if self._workload.runtimeConfig:
            workload_dict["runtimeConfig"] = self._workload.runtimeConfig
        workload_dict["restartPolicy"] = _ank_base.RestartPolicy.Name(
            self._workload.restartPolicy
        )
        workload_dict["dependencies"] = {}
        if self._workload.dependencies:
            for dep_key, dep_value in \
                    self._workload.dependencies.dependencies.items():
                workload_dict["dependencies"][dep_key] = \
                    _ank_base.AddCondition.Name(dep_value)
        workload_dict["tags"] = []
        if self._workload.tags:
            for tag in self._workload.tags.tags:
                workload_dict["tags"].append(
                    {"key": tag.key, "value": tag.value}
                )
        workload_dict["controlInterfaceAccess"] = {}
        if self._workload.controlInterfaceAccess:
            workload_dict["controlInterfaceAccess"]["allowRules"] = []
            for rule in self._workload.controlInterfaceAccess.allowRules:
                access_rule = AccessRightRule(rule)
                workload_dict["controlInterfaceAccess"]["allowRules"].append(
                    access_rule.to_dict()
                )
            workload_dict["controlInterfaceAccess"]["denyRules"] = []
            for rule in self._workload.controlInterfaceAccess.denyRules:
                access_rule = AccessRightRule(rule)
                workload_dict["controlInterfaceAccess"]["denyRules"].append(
                    access_rule.to_dict()
                )
        workload_dict["configs"] = {}
        for alias, name in self._workload.configs.configs.items():
            workload_dict["configs"][alias] = name
        return workload_dict

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
                    workload = workload.add_allow_state_rule(
                        rule["operation"], rule["filterMask"]
                    )
            if "denyRules" in dict_workload["controlInterfaceAccess"]:
                for rule in dict_workload[
                        "controlInterfaceAccess"][
                        "denyRules"
                        ]:
                    workload = workload.add_deny_state_rule(
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


class AccessRightRule:
    """
    Represents an access right rule for a workload. It can be either a
    state rule or a log rule.
    """
    def __init__(self, rule: _ank_base.AccessRightsRule) -> None:
        """
        Initializes the AccessRightRule. For initialization, use
        the static methods `state_rule` or `log_rule`, depending
        on the type of rule you want to create.

        Args:
            rule (_ank_base.AccessRightsRule): The access right rule.
        """
        self._rule = rule

    def __str__(self) -> str:
        """
        Returns the string representation of the access right rule.

        Returns:
            str: The string representation of the access right rule.
        """
        if self.type == "StateRule":
            operation, filter_masks = self._state_rule_to_str(
                self._rule.stateRule
            )
            return f"StateRule: {operation}, {filter_masks}"
        if self.type == "LogRule":
            return f"LogRule: {self._rule.logRule.workloadNames}"
        return "Unknown rule"

    @property
    def type(self) -> str:
        """
        Returns the type of the access right rule.

        Returns:
            str: The type of the access right rule.
        """
        if self._rule.HasField("stateRule"):
            return "StateRule"
        if self._rule.HasField("logRule"):
            return "LogRule"
        return "Unknown"

    @staticmethod
    def state_rule(
            operation: str, filter_masks: list[str]
            ) -> 'AccessRightRule':
        """
        Create an access state rule for a workload.
        Supported operations: `Nothing`, `Write`, `Read`, `ReadWrite`.

        Args:
            operation (str): The operation the rule allows.
            filter_masks (list): The list of filter masks.

        Returns:
            AccessRightRule: The access right rule object.

        Raises:
            WorkloadFieldException: If an invalid operation is provided.
        """
        return AccessRightRule(
            _ank_base.AccessRightsRule(
                stateRule=AccessRightRule._generate_state_rule(
                    operation, filter_masks
                )
            )
        )

    @staticmethod
    def log_rule(
            workload_names: list[str]
            ) -> 'AccessRightRule':
        """
        Create an access log rule for a workload.

        Args:
            workload_names (list): The list of workload names.

        Returns:
            AccessRightRule: The access right rule object.
        """
        return AccessRightRule(
            _ank_base.AccessRightsRule(
                logRule=_ank_base.LogRule(
                    workloadNames=workload_names
                )
            )
        )

    def _to_proto(self) -> _ank_base.AccessRightsRule:
        """
        Convert the AccessRightRule object to a proto message.

        Returns:
            _ank_base.AccessRightsRule: The proto message representation
                of the AccessRightRule object.
        """
        return self._rule

    def to_dict(self) -> dict:
        """
        Convert the AccessRightRule object to a dictionary.

        Returns:
            dict: The dictionary representation of the AccessRightRule object.
        """
        if self.type == "StateRule":
            operation, filter_masks = self._state_rule_to_str(
                self._rule.stateRule
            )
            return {
                "type": "StateRule",
                "operation": operation,
                "filterMask": [str(mask) for mask in filter_masks]
            }
        if self.type == "LogRule":
            return {
                "type": "LogRule",
                "workloadNames": [
                    str(name) for name in self._rule.logRule.workloadNames
                    ]
            }
        return {
            "type": "Unknown"
        }

    @staticmethod
    def _generate_state_rule(operation: str,
                             filter_masks: list[str]
                             ) -> _ank_base.StateRule:
        """
        Generate an access rights rule for the workload.

        Args:
            operation (str): The operation the rule allows.
            filter_masks (list): The list of filter masks.

        Returns:
            _ank_base.StateRule: The state rule generated.

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
            logger.error(
                "Invalid state rule operation provided.")
            raise WorkloadFieldException(
                "state rule operation", operation, enum_mapper.keys()
            )
        return _ank_base.StateRule(
            operation=enum_mapper[operation],
            filterMasks=filter_masks
        )

    @staticmethod
    def _state_rule_to_str(rule: _ank_base.StateRule
                           ) -> tuple[str, list[str]]:
        """
        Convert an access rights rule to a tuple.

        Args:
            rule (_ank_base.StateRule): The state rule to convert.

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
            enum_mapper[rule.operation],
            rule.filterMasks
        )
