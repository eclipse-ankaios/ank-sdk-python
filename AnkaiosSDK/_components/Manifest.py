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

import yaml
from .CompleteState import CompleteState


class Manifest():
    def __init__(self, manifest: dict) -> None:
        self._manifest: dict = manifest

        if not self.check():
            raise ValueError("Invalid manifest")

    @staticmethod
    def from_file(file_path: str) -> 'Manifest':
        try:
            with open(file_path, 'r') as file:
                return Manifest.from_string(file.read())
        except Exception as e:
            raise ValueError(f"Error reading manifest file: {e}")
    
    @staticmethod
    def from_string(manifest: str) -> 'Manifest':
        try:
            return Manifest.from_dict(yaml.safe_load(manifest))
        except Exception as e:
            raise ValueError(f"Error parsing manifest: {e}")
    
    @staticmethod
    def from_dict(manifest: dict) -> 'Manifest':
        return Manifest(manifest)
    
    def check(self) -> bool:
        if "apiVersion" not in self._manifest.keys():
            return False
        if "workloads" not in self._manifest.keys():
            return False
        wl_allowed_keys = ["runtime", "agent", "restartPolicy", "runtimeConfig", 
                           "dependencies", "tags", "controlInterfaceAccess"]
        for wl_name in self._manifest["workloads"]:
            for key in self._manifest["workloads"][wl_name].keys():
                if key not in wl_allowed_keys:
                    return False
        return True
    
    def calculate_masks(self) -> list[str]:
        return [f"desiredState.workloads.{key}" 
                for key in self._manifest["workloads"].keys()]
    
    def generate_complete_state(self) -> CompleteState:
        complete_state = CompleteState()
        complete_state._from_dict(self._manifest)
        return complete_state
