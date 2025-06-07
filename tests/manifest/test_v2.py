import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Import the actual ManifestV2 class
from ankaios_sdk._components.manifest_v2 import ManifestV2

# Test initialization with valid parameters
def test_manifestv2_initialization():
    manifest = ManifestV2(
        manifest_version="2.0",
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    )
    assert manifest is not None
    assert manifest.manifest_version == "2.0"
    assert "test-workload" in manifest.workloads


# Test initialization with default manifest_version
def test_manifestv2_initialization_default_version():
    manifest = ManifestV2(
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    )
    assert manifest is not None
    assert manifest.manifest_version == "2.0"  # Default version
    assert "test-workload" in manifest.workloads


# Test validation of required fields
def test_manifestv2_missing_required_fields():
    with pytest.raises(ValueError):
        ManifestV2(manifest_version="2.0")


# Test to_dict method
def test_manifestv2_to_dict():
    manifest = ManifestV2(
        manifest_version="2.0",
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    )
    manifest_dict = manifest.to_dict()
    assert isinstance(manifest_dict, dict)
    assert manifest_dict["manifest_version"] == "2.0"
    assert "test-workload" in manifest_dict["workloads"]


# Test from_dict method
def test_manifestv2_from_dict():
    manifest_dict = {
        "manifest_version": "2.0",
        "workloads": {
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    }
    manifest = ManifestV2.from_dict(manifest_dict)
    assert manifest is not None
    assert manifest.manifest_version == "2.0"
    assert "test-workload" in manifest.workloads
    assert manifest.dependencies == []  # Check default for optional field
    assert manifest.metadata == {}    # Check default for optional field


# Test from_dict method with missing manifest_version
def test_manifestv2_from_dict_missing_manifest_version():
    manifest_dict = {
        "workloads": {
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    }
    manifest = ManifestV2.from_dict(manifest_dict)
    assert manifest is not None
    assert manifest.manifest_version == "2.0"  # Should default to 2.0
    assert "test-workload" in manifest.workloads
    assert manifest.dependencies == []
    assert manifest.metadata == {}


# Test equality comparison
def test_manifestv2_equality():
    manifest1 = ManifestV2(
        manifest_version="2.0",
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    )
    manifest2 = ManifestV2(
        manifest_version="2.0",
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    )
    assert manifest1 == manifest2


# Test inequality: different manifest_version
def test_manifestv2_inequality_different_version():
    manifest1 = ManifestV2(workloads={"wl1": {}})
    manifest2 = ManifestV2(manifest_version="2.1", workloads={"wl1": {}})
    assert manifest1 != manifest2


# Test inequality: different workloads
def test_manifestv2_inequality_different_workloads():
    manifest1 = ManifestV2(workloads={"wl1": {}})
    manifest2 = ManifestV2(workloads={"wl2": {}})
    assert manifest1 != manifest2


# Test inequality: different dependencies
def test_manifestv2_inequality_different_dependencies():
    manifest1 = ManifestV2(workloads={"wl1": {}}, dependencies=["dep1"])
    manifest2 = ManifestV2(workloads={"wl1": {}}, dependencies=["dep2"])
    assert manifest1 != manifest2


# Test inequality: different metadata
def test_manifestv2_inequality_different_metadata():
    manifest1 = ManifestV2(workloads={"wl1": {}}, metadata={"k": "v1"})
    manifest2 = ManifestV2(workloads={"wl1": {}}, metadata={"k": "v2"})
    assert manifest1 != manifest2


# Test inequality: different types
def test_manifestv2_inequality_different_type():
    manifest1 = ManifestV2(workloads={"wl1": {}})
    other_object = object()
    assert manifest1 != other_object


# Test optional fields
def test_manifestv2_optional_fields():
    manifest = ManifestV2(
        manifest_version="2.0",
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        },
        dependencies=["dep1", "dep2"],
        metadata={"key": "value"}
    )
    assert manifest.dependencies == ["dep1", "dep2"]
    assert manifest.metadata == {"key": "value"}


# Test serialization to JSON
def test_manifestv2_json_serialization():
    manifest = ManifestV2(
        manifest_version="2.0",
        workloads={
            "test-workload": {
                "runtime": "test-runtime",
                "command": ["test-command"],
            }
        }
    )
    manifest_dict = manifest.to_dict()
    json_str = json.dumps(manifest_dict)
    loaded_dict = json.loads(json_str)
    assert loaded_dict["manifest_version"] == "2.0"
    assert "test-workload" in loaded_dict["workloads"]


# Test with complex workload configuration
def test_manifestv2_complex_workload():
    manifest = ManifestV2(
        manifest_version="2.0",
        workloads={
            "complex-workload": {
                "runtime": "container",
                "command": ["run", "--verbose"],
                "args": ["arg1", "arg2"],
                "env": {"ENV1": "value1", "ENV2": "value2"},
                "resources": {
                    "cpu": "100m",
                    "memory": "256Mi"
                }
            }
        }
    )
    assert "complex-workload" in manifest.workloads
    assert manifest.workloads["complex-workload"]["runtime"] == "container"
    assert "args" in manifest.workloads["complex-workload"]
    assert "env" in manifest.workloads["complex-workload"]
    assert "resources" in manifest.workloads["complex-workload"]
