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
This script defines the Workload and WorkloadBuilder classes for creating and managing workloads.

Classes:
    Workload: Represents a workload with various attributes and methods to update them.
    WorkloadBuilder: A builder class to create a Workload object with a fluent interface.

Usage:
    - Create a workload using the WorkloadBuilder:
        workload = Workload.builder() \
            .agent_name("agent_A") \
            .runtime("podman") \
            .restart_policy("NEVER") \
            .runtime_config("image: docker.io/library/nginx\n" +
                            "commandOptions: [\"-p\", \"8080:80\"]") \
            .add_dependency("other_workload", "RUNNING") \
            .add_tag("key1", "value1") \
            .add_tag("key2", "value2") \
            .build()

    - Update fields of the workload:
        workload.update_agent_name("agent_B")

    - Update dependencies:
        deps = workload.get_dependencies()
        deps["other_workload"] = "SUCCEEDED"
        workload.update_dependencies(deps)

    - Update tags:
        tags = workload.get_tags()
        tags.pop("key1")
        workload.update_tags(tags)

    - Print the updated workload:
        print(workload)
"""


from .._protos import _ank_base


__all__ = ["Workload", "WorkloadBuilder"]


class Workload:
    """
    A class to represent a workload.
    """
    def __init__(self) -> None:
        """
        Initialize a Workload object.
        """
        self._workload = _ank_base.Workload()

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

    def update_agent_name(self, agent_name: str) -> None:
        """
        Set the agent name for the workload.

        Args:
            agent_name (str): The agent name to update.
        """
        self._workload.agent = agent_name

    def update_runtime(self, runtime: str) -> None:
        """
        Set the runtime for the workload.

        Args:
            runtime (str): The runtime to update.
        """
        self._workload.runtime = runtime

    def update_runtime_config(self, config: str) -> None:
        """
        Set the runtime-specific configuration for the workload.

        Args:
            config (str): The runtime configuration to update.
        """
        self._workload.runtimeConfig = config

    def update_runtime_config_from_file(self, config_file: str) -> None:
        """
        Set the runtime-specific configuration for the workload from a file.

        Args:
            config_file (str): The path to the configuration file.
        """
        with open(config_file, "r", encoding="utf-8") as file:
            self._workload.runtimeConfig = file.read()

    def update_restart_policy(self, policy: str) -> None:
        """
        Set the restart policy for the workload.
        Supported values: 'NEVER', 'ON_FAILURE', 'ALWAYS'.

        Args:
            policy (str): The restart policy to update.

        Raises:
            ValueError: If an invalid restart policy is provided.
        """
        policy_map = {
            "NEVER": _ank_base.NEVER,
            "ON_FAILURE": _ank_base.ON_FAILURE,
            "ALWAYS": _ank_base.ALWAYS
        }

        if policy not in policy_map:
            raise ValueError("Invalid restart policy. Supported values " +
                             "'NEVER', 'ON_FAILURE', 'ALWAYS'.")
        self._workload.restartPolicy = policy_map[policy]

    def add_dependency(self, workload_name: str, condition: str) -> None:
        """
        Add a dependency to the workload.
        Supported values: 'RUNNING', 'SUCCEEDED', 'FAILED'.

        Args:
            workload_name (str): The name of the dependent workload.
            condition (str): The condition for the dependency.

        Raises:
            ValueError: If an invalid condition is provided.
        """
        condition_map = {
            "RUNNING": _ank_base.ADD_COND_RUNNING,
            "SUCCEEDED": _ank_base.ADD_COND_SUCCEEDED,
            "FAILED": _ank_base.ADD_COND_FAILED
        }

        if condition not in condition_map:
            raise ValueError("Invalid condition. Supported values: " +
                             "'RUNNING', 'SUCCEEDED', 'FAILED'.")
        self._workload.dependencies.dependencies[workload_name] = condition_map[condition]

    def get_dependencies(self) -> dict:
        """
        Return the dependencies of the workload.

        Returns:
            dict: A dictionary of dependencies with workload names as keys and conditions as values.
        """
        deps = dict(self._workload.dependencies.dependencies)
        for dep in deps:
            if deps[dep] == _ank_base.ADD_COND_RUNNING:
                deps[dep] = "RUNNING"
            elif deps[dep] == _ank_base.ADD_COND_SUCCEEDED:
                deps[dep] = "SUCCEEDED"
            elif deps[dep] == _ank_base.ADD_COND_FAILED:
                deps[dep] = "FAILED"
        return deps

    def update_dependencies(self, dependencies: dict) -> None:
        """
        Update the dependencies of the workload.

        Args:
            dependencies (dict): A dictionary of dependencies with workload names and values.
        """
        self._workload.dependencies.dependencies.clear()
        for workload_name, condition in dependencies.items():
            self.add_dependency(workload_name, condition)

    def add_tag(self, key: str, value: str) -> None:
        """
        Add a tag to the workload.

        Args:
            key (str): The key of the tag.
            value (str): The value of the tag.
        """
        tag = _ank_base.Tag(key=key, value=value)
        self._workload.tags.tags.append(tag)

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
            self.add_tag(key, value)

    def _to_proto(self) -> _ank_base.Workload:
        """
        Convert the Workload object to a proto message.

        Returns:
            _ank_base.Workload: The proto message representation of the Workload object.
        """
        return self._workload

    def _from_proto(self, proto: _ank_base.Workload) -> None:
        """
        Convert the proto message to a Workload object.

        Args:
            proto (_ank_base.Workload): The proto message to convert.
        """
        self._workload = proto


class WorkloadBuilder:
    """
    A builder class to create a Workload object.
    """
    def __init__(self) -> None:
        """
        Initialize a WorkloadBuilder object.
        """
        self.wl_agent_name = None
        self.wl_runtime = None
        self.wl_runtime_config = None
        self.wl_restart_policy = None
        self.dependencies = {}
        self.tags = []

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

    def runtime_config_from_file(self, runtime_config_path: str) -> "WorkloadBuilder":
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

    def add_dependency(self, workload_name: str, condition: str) -> "WorkloadBuilder":
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

    def build(self) -> Workload:
        """
        Build the Workload object.
        Required fields: agent name, runtime and runtime configuration.

        Returns:
            Workload: The built Workload object.

        Raises:
            ValueError: If required fields are not set.
        """
        workload = Workload()

        if self.wl_agent_name is None:
            raise ValueError("Workload can not be built without an agent name.")
        if self.wl_runtime is None:
            raise ValueError("Workload can not be built without a runtime.")
        if self.wl_runtime_config is None:
            raise ValueError("Workload can not be built without a runtime configuration.")

        workload.update_agent_name(self.wl_agent_name)
        workload.update_runtime(self.wl_runtime)
        workload.update_runtime_config(self.wl_runtime_config)

        if self.wl_restart_policy is not None:
            workload.update_restart_policy(self.wl_restart_policy)
        if len(self.dependencies) > 0:
            workload.update_dependencies(self.dependencies)
        if len(self.tags) > 0:
            workload.update_tags(self.tags)
        return workload
