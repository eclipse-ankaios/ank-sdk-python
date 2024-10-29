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
from ..exceptions import InvalidManifestException
from ..utils import WORKLOADS_PREFIX, CONFIGS_PREFIX


class Manifest():
    """
    Represents a workload manifest.
    The manifest can be loaded from a yaml file, string or dictionary.
    """
    def __init__(self, manifest: dict) -> None:
        """
        Initializes a Manifest instance with the given manifest data.

        Args:
            manifest (dict): The manifest data.

        Raises:
            ValueError: If the manifest data is invalid.
        """
        self._manifest: dict = manifest
        self.check()

    @staticmethod
    def from_file(file_path: str) -> 'Manifest':
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
            with open(file_path, 'r', encoding="utf-8") as file:
                return Manifest.from_string(file.read())
        except Exception as e:
            raise ValueError(f"Error reading manifest file: {e}") from e

    @staticmethod
    def from_string(manifest: str) -> 'Manifest':
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
    def from_dict(manifest: dict) -> 'Manifest':
        """
        Creates a Manifest instance from a dictionary.

        Args:
            manifest (dict): The dictionary representing the manifest.

        Returns:
            Manifest: An instance of the Manifest class with the given data.
        """
        return Manifest(manifest)

    def check(self) -> None:
        """
        Validates the manifest data.

        Raises:
            InvalidManifestException: If the manifest is invalid.
        """
        if "apiVersion" not in self._manifest.keys():
            raise InvalidManifestException("apiVersion is missing.")
        if "workloads" not in self._manifest.keys():
            raise InvalidManifestException("workloads is missing.")
        wl_allowed_keys = ["runtime", "agent", "restartPolicy",
                           "runtimeConfig", "dependencies", "tags",
                           "controlInterfaceAccess", "configs"]
        wl_mandatory_keys = ["runtime", "runtimeConfig", "agent"]
        for wl_name in self._manifest["workloads"]:
            # Check allowed keys
            for key in self._manifest["workloads"][wl_name].keys():
                if key not in wl_allowed_keys:
                    raise InvalidManifestException(
                        f"Invalid key in workload {wl_name}: {key}")
            # Check mandatory keys
            for key in wl_mandatory_keys:
                if key not in self._manifest["workloads"][wl_name].keys():
                    raise InvalidManifestException(
                        f"Mandatory key {key} missing in workload {wl_name}")

    def _calculate_masks(self) -> list[str]:
        """
        Calculates the masks for the manifest. This includes
        the names of the workloads and of the configs.

        Returns:
            list[str]: A list of masks.
        """
        masks = [f"{WORKLOADS_PREFIX}.{key}"
                 for key in self._manifest["workloads"].keys()]
        if "configs" in self._manifest.keys():
            masks.extend([f"{CONFIGS_PREFIX}.{key}"
                          for key in self._manifest["configs"].keys()])
        return masks
