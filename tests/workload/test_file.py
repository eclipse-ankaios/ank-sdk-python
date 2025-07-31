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
This module contains unit tests for the File class and related data classes
in the ankaios_sdk.
"""

import pytest
from ankaios_sdk._components.file import (
    File,
    DataFileContent,
    BinaryFileContent,
)
from ankaios_sdk._protos import _ank_base


# Test data constants
TEST_MOUNT_POINT = "/etc/config.txt"
TEST_DATA_CONTENT = "sample text content"
TEST_BINARY_MOUNT_POINT = "/etc/binary.bin"
TEST_BINARY_CONTENT = "iVBORw0KGgoAAAABCAcSJAAAADUlEHgAHgJ/PchI7wAAArkJggg=="

FILE_DICT_WITH_DATA = {
    "mount_point": TEST_MOUNT_POINT,
    "content": {"data": TEST_DATA_CONTENT},
}

FILE_DICT_WITH_BINARY = {
    "mount_point": TEST_BINARY_MOUNT_POINT,
    "content": {"binaryData": TEST_BINARY_CONTENT},
}

FILE_PROTO_WITH_DATA = _ank_base.File(
    mountPoint=TEST_MOUNT_POINT, data=TEST_DATA_CONTENT
)

FILE_PROTO_WITH_BINARY = _ank_base.File(
    mountPoint=TEST_BINARY_MOUNT_POINT, binaryData=TEST_BINARY_CONTENT
)


def generate_test_data_file():
    """
    Helper function to generate a File instance with text data.

    Returns:
        File: A File instance containing text data.
    """
    return File.from_data(TEST_MOUNT_POINT, TEST_DATA_CONTENT)


def generate_test_binary_file():
    """
    Helper function to generate a File instance with binary data.

    Returns:
        File: A File instance containing binary data.
    """
    return File.from_binary_data(TEST_BINARY_MOUNT_POINT, TEST_BINARY_CONTENT)


def test_data_creation():
    """
    Test creating a Data instance.
    """
    data = DataFileContent("test content")
    assert data.value == "test content"


def test_data_equality():
    """
    Test Data equality comparison.
    """
    data1 = DataFileContent("test content")
    data2 = DataFileContent("test content")
    data3 = DataFileContent("different content")

    assert data1 == data2
    assert data1 != data3


def test_binary_data_creation():
    """
    Test creating a BinaryData instance.
    """
    binary_data = BinaryFileContent("binary content")
    assert binary_data.value == "binary content"


def test_binary_data_equality():
    """
    Test BinaryData equality comparison.
    """
    binary1 = BinaryFileContent("binary content")
    binary2 = BinaryFileContent("binary content")
    binary3 = BinaryFileContent("different binary")

    assert binary1 == binary2
    assert binary1 != binary3


def test_file_init_with_data():
    """
    Test File initialization with Data content.
    """
    data = DataFileContent("test content")
    file_obj = File("/etc/test.txt", data)

    assert file_obj.mount_point == "/etc/test.txt"
    assert file_obj.content == data
    assert isinstance(file_obj.content, DataFileContent)


def test_file_init_with_binary_data():
    """
    Test File initialization with BinaryData content.
    """
    binary_data = BinaryFileContent("binary content")
    file_obj = File("/etc/test.bin", binary_data)

    assert file_obj.mount_point == "/etc/test.bin"
    assert file_obj.content == binary_data
    assert isinstance(file_obj.content, BinaryFileContent)


def test_from_data_classmethod():
    """
    Test File.from_data class method.
    """
    file_obj = File.from_data("/etc/config.txt", "sample text")

    assert file_obj.mount_point == "/etc/config.txt"
    assert isinstance(file_obj.content, DataFileContent)
    assert file_obj.content.value == "sample text"

    data_file = File.from_data("/etc/empty.txt", "")
    assert isinstance(data_file.content, DataFileContent)
    assert data_file.content.value == ""


def test_from_binary_data_classmethod():
    """
    Test File.from_binary_data class method.
    """
    file_obj = File.from_binary_data("/etc/binary.bin", "binary content")

    assert file_obj.mount_point == "/etc/binary.bin"
    assert isinstance(file_obj.content, BinaryFileContent)
    assert file_obj.content.value == "binary content"

    binary_file = File.from_binary_data("/etc/empty.bin", "")
    assert isinstance(binary_file.content, BinaryFileContent)
    assert binary_file.content.value == ""


def test_to_dict():
    """
    Test to_dict method with different file types.
    """
    # Test with data file
    data_file = generate_test_data_file()
    result = data_file.to_dict()
    assert result == FILE_DICT_WITH_DATA

    # Test with binary file
    binary_file = generate_test_binary_file()
    result = binary_file.to_dict()
    assert result == FILE_DICT_WITH_BINARY


def test_from_dict():
    """
    Test _from_dict static method.
    """
    # Test with data content
    file_obj = File._from_dict(FILE_DICT_WITH_DATA)

    assert file_obj.mount_point == TEST_MOUNT_POINT
    assert isinstance(file_obj.content, DataFileContent)
    assert file_obj.content.value == TEST_DATA_CONTENT

    # Test with binary data content
    file_obj = File._from_dict(FILE_DICT_WITH_BINARY)

    assert file_obj.mount_point == TEST_BINARY_MOUNT_POINT
    assert isinstance(file_obj.content, BinaryFileContent)
    assert file_obj.content.value == TEST_BINARY_CONTENT


def test_from_dict_invalid_format():
    """
    Test _from_dict static method with invalid format.
    """
    # Test with empty content
    file_dict = {"mount_point": "/etc/invalid.txt", "content": {}}

    with pytest.raises(ValueError, match="Invalid file dictionary format"):
        File._from_dict(file_dict)

    # Test with missing content
    file_dict = {"mount_point": "/etc/invalid.txt"}

    with pytest.raises(ValueError, match="Invalid file dictionary format"):
        File._from_dict(file_dict)


def test_to_proto():
    """
    Test _to_proto method with different file types.
    """
    # Test with data file
    data_file = generate_test_data_file()
    proto_file = data_file._to_proto()

    assert isinstance(proto_file, _ank_base.File)
    assert proto_file.mountPoint == TEST_MOUNT_POINT
    assert proto_file.data == TEST_DATA_CONTENT
    assert proto_file.binaryData == ""

    # Test with binary file
    binary_file = generate_test_binary_file()
    proto_file = binary_file._to_proto()

    assert isinstance(proto_file, _ank_base.File)
    assert proto_file.mountPoint == TEST_BINARY_MOUNT_POINT
    assert proto_file.data == ""
    assert proto_file.binaryData == TEST_BINARY_CONTENT


def test_from_proto():
    """
    Test _from_proto static method.
    """
    # Test with data content
    file_obj = File._from_proto(FILE_PROTO_WITH_DATA)

    assert file_obj.mount_point == TEST_MOUNT_POINT
    assert isinstance(file_obj.content, DataFileContent)
    assert file_obj.content.value == TEST_DATA_CONTENT

    # Test with binary data content
    file_obj = File._from_proto(FILE_PROTO_WITH_BINARY)

    assert file_obj.mount_point == TEST_BINARY_MOUNT_POINT
    assert isinstance(file_obj.content, BinaryFileContent)
    assert file_obj.content.value == TEST_BINARY_CONTENT


def test_from_proto_invalid_format():
    """
    Test _from_proto static method with invalid format.
    """
    proto_file = _ank_base.File(mountPoint="/etc/invalid.txt")

    with pytest.raises(ValueError, match="Invalid protobuf file format"):
        File._from_proto(proto_file)


def test_str_method():
    """
    Test __str__ method.
    """
    data_file = generate_test_data_file()
    str_representation = str(data_file)

    # The string should contain the proto representation
    assert TEST_MOUNT_POINT in str_representation
    assert TEST_DATA_CONTENT in str_representation
