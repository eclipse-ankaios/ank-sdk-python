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
This module defines the Manifest class for handling ankaios manifests.

Classes
-------

- Manifest:
    Represents a workload manifest and provides methods \
    to validate and load it.

Usage
-----

- Load a manifest from a file:
    .. code-block:: python

        manifest = Manifest.from_file("path/to/manifest.yaml")

- Load a manifest from a string:
    .. code-block:: python

        manifest = Manifest.from_string("apiVersion: 1.0\\nworkloads: {}")

- Load a manifest from a dictionary:
    .. code-block:: python

        manifest = Manifest.from_dict({"apiVersion": "1.0", "workloads": {}})
"""

import yaml
from .._protos import _ank_base
from ..exceptions import InvalidManifestException
from .workload import Workload
from ..utils import WORKLOADS_PREFIX, CONFIGS_PREFIX, _to_config_item


class Manifest:
    """
    Represents a workload manifest.
    The manifest can be loaded from a yaml file, string or dictionary.
    """

    def __init__(self, desired_state: _ank_base.State) -> None:
        """
        Initializes a Manifest instance with the given manifest data.
        For creation, it is recommended to use the from_file, from_string or
        from_dict methods.
        The manifest data is validated upon initialization.

        Args:
            desired_state (_ank_base.State): The desired state proto.

        Raises:
            ValueError: If the manifest data is invalid.
        """
        self._desired_state: _ank_base.State = desired_state

    @staticmethod
    def from_file(file_path: str) -> "Manifest":
        """
        Loads a manifest from a file.

        Args:
            file_path (str): The path to the manifest file.

        Returns:
            Manifest: An instance of the Manifest class with the loaded data.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If there is an error parsing the YAML file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return Manifest.from_string(file.read())
        except Exception as e:
            raise ValueError(f"Error reading manifest file: {e}") from e

    @staticmethod
    def from_string(manifest: str) -> "Manifest":
        """
        Creates a Manifest instance from a YAML string.

        Args:
            manifest (str): The YAML string representing the manifest.

        Returns:
            Manifest: An instance of the Manifest class with the parsed data.

        Raises:
            ValueError: If there is an error parsing the YAML string.
        """
        try:
            return Manifest.from_dict(yaml.safe_load(manifest))
        except Exception as e:
            raise ValueError(f"Error parsing manifest: {e}") from e

    @staticmethod
    def from_dict(manifest: dict) -> "Manifest":
        """
        Creates a Manifest instance from a dictionary.

        Args:
            manifest (dict): The dictionary representing the manifest.

        Returns:
            Manifest: An instance of the Manifest class with the given data.
        """
        desired_state = _ank_base.State()
        if "apiVersion" not in manifest.keys():
            raise InvalidManifestException("apiVersion is missing.")
        desired_state.apiVersion = manifest["apiVersion"]
        if "workloads" in manifest.keys():
            workloads = manifest["workloads"]
            for wl_name, wl_data in workloads.items():
                try:
                    workload = Workload._from_dict(wl_name, wl_data)
                    desired_state.workloads.workloads[wl_name].CopyFrom(
                        workload._to_proto()
                    )
                except Exception as e:
                    raise InvalidManifestException(
                        f"Error building workload {wl_name}: {e}"
                    ) from e
        if "configs" in manifest.keys():
            configs = manifest["configs"]
            for key, value in configs.items():
                desired_state.configs.configs[key].CopyFrom(
                    _to_config_item(value)
                )
        return Manifest(desired_state)

    def _calculate_masks(self) -> list[str]:
        """
        Calculates the masks for the manifest. This includes
        the names of the workloads and of the configs.

        Returns:
            list[str]: A list of masks.
        """
        masks = []
        if self._desired_state.workloads.workloads:
            masks.extend(
                [
                    f"{WORKLOADS_PREFIX}.{key}"
                    for key in sorted(
                        self._desired_state.workloads.workloads.keys()
                    )
                ]
            )
        if self._desired_state.configs.configs:
            masks.extend(
                [
                    f"{CONFIGS_PREFIX}.{key}"
                    for key in sorted(
                        self._desired_state.configs.configs.keys()
                    )
                ]
            )
        return masks

    def _to_desired_state(self) -> _ank_base.State:
        """
        Returns the desired state proto.

        Returns:
            _ank_base.State: The desired state proto.
        """
        return self._desired_state
