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
This module contains unit tests for the Manifest class in the ankaios_sdk.
"""

from unittest.mock import patch, mock_open
import pytest
from ankaios_sdk._protos import _ank_base
from ankaios_sdk import Manifest, InvalidManifestException
from ankaios_sdk.utils import WORKLOADS_PREFIX, CONFIGS_PREFIX


MANIFEST_CONTENT = """apiVersion: v0.1
workloads:
  nginx_test:
    runtime: podman
    restartPolicy: NEVER
    agent: agent_A
    configs:
        ports: test_ports
    runtimeConfig: |
      image: image/test
configs:
    test_ports:
        port: \"8081\""""

MANIFEST_DICT = {
    'apiVersion': 'v0.1',
    'workloads': {
        'nginx_test': {
            'runtime': 'podman',
            'restartPolicy': 'NEVER',
            'agent': 'agent_A',
            "configs": {
                "ports": "test_ports"
            },
            'runtimeConfig': 'image: image/test\n'
        }
    },
    'configs': {
        "test_ports": {
            "port": "8081"
        }
    }
}
MANIFEST_PROTO = _ank_base.State(
    apiVersion="v0.1",
    workloads=_ank_base.WorkloadMap(
        workloads={
            "nginx_test": _ank_base.Workload(
                agent="agent_A",
                runtime="podman",
                runtimeConfig="image: image/test\n",
                restartPolicy=_ank_base.NEVER,
                configs=_ank_base.ConfigMappings(
                    configs={
                        "ports": "test_ports",
                    }
                )
            )
        }
    ),
    configs=_ank_base.ConfigMap(
        configs={
            "test_ports": _ank_base.ConfigItem(
                object=_ank_base.ConfigObject(
                    fields={
                        "port": _ank_base.ConfigItem(
                            String="8081"
                        )
                    }
                )
            )
        }
    )
)


def test_from_file():
    """
    Test the from_file method of the Manifest class,
    ensuring it correctly loads a manifest from a file and handles errors.
    """
    with patch("builtins.open", mock_open(read_data=MANIFEST_CONTENT)), \
            patch("ankaios_sdk.Manifest.from_string") as mock_from_string:
        _ = Manifest.from_file("manifest.yaml")
        mock_from_string.assert_called_once_with(MANIFEST_CONTENT)

    with pytest.raises(ValueError, match="Error reading manifest file"):
        _ = Manifest.from_file("invalid_path")


def test_from_string():
    """
    Test the from_string method of the Manifest class,
    ensuring it correctly parses a manifest from a YAML
    string and handles errors.
    """
    with patch("ankaios_sdk.Manifest.from_dict") as mock_from_dict:
        _ = Manifest.from_string(MANIFEST_CONTENT)
        mock_from_dict.assert_called_once_with(MANIFEST_DICT)

    with pytest.raises(ValueError, match="Error parsing manifest"):
        _ = Manifest.from_string("invalid_manifest")


def test_from_dict():
    """
    Test the from_dict method of the Manifest class,
    ensuring it correctly creates a Manifest instance
    from a dictionary and handles errors.
    """
    manifest = Manifest.from_dict(MANIFEST_DICT)
    desired_state = manifest._to_desired_state()
    assert desired_state == MANIFEST_PROTO

    with pytest.raises(InvalidManifestException,
                       match="apiVersion is missing."):
        manifest = Manifest.from_dict({})

    with pytest.raises(InvalidManifestException):
        _ = Manifest.from_dict({'apiVersion': 'v0.1', 'workloads':
                                {'nginx_test': {}}})

    with pytest.raises(InvalidManifestException):
        _ = Manifest.from_dict({'apiVersion': 'v0.1', 'workloads':
                                {'nginx_test': {'invalid_key': ''}}})


def test_calculate_masks():
    """
    Test the calculated masks for the manifest data,
    ensuring they are correctly generated based on the workload names.
    """
    manifest_dict = MANIFEST_DICT.copy()
    manifest_dict["workloads"]["nginx_test_other"] = {
            'runtime': 'podman',
            'restartPolicy': 'NEVER',
            'agent': 'agent_B',
            'runtimeConfig': 'image: image/test'
        }
    manifest = Manifest.from_dict(manifest_dict)
    assert len(manifest._calculate_masks()) == 3
    assert manifest._calculate_masks() == [
        f"{WORKLOADS_PREFIX}.nginx_test_other",
        f"{WORKLOADS_PREFIX}.nginx_test",
        f"{CONFIGS_PREFIX}.test_ports"
    ]


def test_manifest_only_configs():
    """
    Test the manifest with only configs.
    """
    manifest_dict = MANIFEST_DICT.copy()
    manifest_dict.pop("workloads")
    manifest = Manifest.from_dict(manifest_dict)
    assert len(manifest._calculate_masks()) == 1
    assert manifest._calculate_masks() == [f"{CONFIGS_PREFIX}.test_ports"]
