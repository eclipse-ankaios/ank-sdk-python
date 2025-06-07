# Copyright 2024 The Ankaios Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Manifest V2 component for Ankaios SDK."""

class ManifestV2:
    """Represents a V2 manifest for Ankaios workloads."""

    def __init__(self, manifest_version: str = "2.0", workloads: dict = None, 
                 dependencies: list = None, metadata: dict = None):
        """Initializes the ManifestV2 object.

        Args:
            manifest_version: The version of the manifest. Defaults to "2.0".
            workloads: A dictionary defining the workloads.
            dependencies: A list of dependencies.
            metadata: A dictionary for metadata.
        
        Raises:
            ValueError: If workloads is not provided.
        """
        self.manifest_version = manifest_version
        self.workloads = workloads if workloads is not None else {}
        self.dependencies = dependencies if dependencies is not None else []
        self.metadata = metadata if metadata is not None else {}

        if not self.workloads:
            raise ValueError("workloads is required")

    def to_dict(self) -> dict:
        """Converts the manifest to a dictionary.

        Returns:
            A dictionary representation of the manifest.
        """
        return {
            "manifest_version": self.manifest_version,
            "workloads": self.workloads,
            "dependencies": self.dependencies,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ManifestV2':
        """Creates a ManifestV2 object from a dictionary.

        Args:
            data: A dictionary containing manifest data.

        Returns:
            A ManifestV2 object.
        """
        return cls(
            manifest_version=data.get("manifest_version", "2.0"),
            workloads=data.get("workloads"), # Let constructor handle None -> {}
            dependencies=data.get("dependencies"),
            metadata=data.get("metadata")
        )

    def __eq__(self, other: object) -> bool:
        """Compares two ManifestV2 objects for equality.

        Args:
            other: The object to compare with.

        Returns:
            True if the objects are equal, False otherwise.
        """
        if not isinstance(other, ManifestV2):
            return False
        return (
            self.manifest_version == other.manifest_version and
            self.workloads == other.workloads and
            self.dependencies == other.dependencies and
            self.metadata == other.metadata
        )