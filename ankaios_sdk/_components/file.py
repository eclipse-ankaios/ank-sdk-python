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
This module defines the File class for
handling files mounted to Ankaios workloads.

Classes
-------

- :class:`File`:
    Represents a file that can be mounted to an Ankaios workload.
- :class:`DataFileContent`:
    Represents text-based file content.
- :class:`BinaryFileContent`:
    Represents binary file content.

Union Types
-----------

- :class:`FileContent`:
    Union type for file content, which can be either
    :py:class:`DataFileContent` or :py:class:`BinaryFileContent`.

Usage
-----

- Create a File instance from text data:
    .. code-block:: python

        file = File.from_data(
                    mount_point="/path/to/mount",
                    data="file content")

- Create a File instance from binary data:
    .. code-block:: python

        file = File.from_binary_data(
                    mount_point="/path/to/mount",
                    binary_data="binary content")

- Convert a File instance to a dictionary:
    .. code-block:: python

        file_dict = file.to_dict()

- Get the content and check it's type:
    .. code-block:: python

        file = File()
        if isinstance(file.content, DataFileContent):
            print("Text file content:", file.content.value)
        elif isinstance(file.content, BinaryFileContent):
            print("Binary file content:", file.content.value)
"""


__all__ = ["File", "DataFileContent", "BinaryFileContent"]


from dataclasses import dataclass
from typing import Union
from .._protos import _ank_base


@dataclass
class DataFileContent:
    """
    This class is used to represent text-based file content.

    :var str value:
        The text content value.
    """

    value: str


@dataclass
class BinaryFileContent:
    """
    This class is used to represent binary file content.

    :var str value:
        The binary content value as a `Base64` encoded string.
    """

    value: str


FileContent = Union[DataFileContent, BinaryFileContent]


class File:
    """
    This class represents a file able to be mounted to an Ankaios workload.
    It can hold either text-based or binary content.

    :var str mount_point:
        The mount point of the file.
    :var FileContent content:
        The content of the file,
        which can be either text or binary.
    """

    def __init__(self, mount_point: str, content: FileContent) -> None:
        """
        Initialize a File instance.

        :param mount_point: The mount point of the file.
        :type mount_point: str
        :param content: The content of the file,
            which can be either text or binary.
        :type content: FileContent
        """
        self.mount_point = mount_point
        self.content: FileContent = content

    @classmethod
    def from_data(cls, mount_point: str, data: str) -> "File":
        """
        Create a File instance from text data.

        :param mount_point: The mount point of the file.
        :type mount_point: str
        :param data: The text content of the file.
        :type data: str

        :returns: A File instance with text-based content.
        :rtype: File
        """
        return cls(
            mount_point=mount_point, content=DataFileContent(value=data)
        )

    @classmethod
    def from_binary_data(cls, mount_point: str, binary_data: str) -> "File":
        """
        Create a File instance from binary data.

        :param mount_point: The mount point of the file.
        :type mount_point: str
        :param binary_data: The binary content of the file.
        :type binary_data: str

        :returns: A File instance with binary content.
        :rtype: File
        """
        return cls(
            mount_point=mount_point,
            content=BinaryFileContent(value=binary_data),
        )

    def __str__(self) -> str:
        """
        Return a string representation of the File object.

        :returns: String representation of the File object.
        :rtype: str
        """
        return str(self._to_proto())

    def to_dict(self) -> dict:
        """
        Convert the File instance to a dictionary representation.

        :returns: The dictionary representation of the File instance.
        :rtype: dict

        :raises ValueError: If the file content type is unsupported.
        """
        dict_conv = {"mount_point": self.mount_point}
        if isinstance(self.content, DataFileContent):
            dict_conv["content"] = {"data": self.content.value}
        elif isinstance(self.content, BinaryFileContent):
            dict_conv["content"] = {"binaryData": self.content.value}
        else:  # pragma: no cover
            raise ValueError(
                "Unsupported file content type. "
                "Expected Data or BinaryData."
            )
        return dict_conv

    @staticmethod
    def _from_dict(file_dict: dict) -> "File":
        """
        Create a File instance from a dictionary representation.

        :param file_dict: The dictionary containing file information.
        :type file_dict: dict

        :returns: A File instance created from the dictionary.
        :rtype: File

        :raises ValueError: If the file dictionary format is invalid.
        """
        mount_point = file_dict.get("mount_point")
        content = file_dict.get("content")

        if not content:
            raise ValueError(
                "Invalid file dictionary format. Expected 'content' key."
            )

        if content.get("data"):
            return File.from_data(
                mount_point=mount_point, data=file_dict["content"]["data"]
            )
        if content.get("binaryData"):
            return File.from_binary_data(
                mount_point=mount_point,
                binary_data=file_dict["content"]["binaryData"],
            )
        # Unreachable code, as the content must be either data or binaryData.
        raise ValueError(
            "Invalid file dictionary format. "
            "Expected 'data' or 'binaryData' key."
        )  # pragma: no cover

    def _to_proto(self) -> _ank_base.File:
        """
        Convert the File instance to a protobuf representation.

        :returns: The protobuf representation of the File instance.
        :rtype: _ank_base.File

        :raises ValueError: If the file content type is unsupported.
        """
        if isinstance(self.content, DataFileContent):
            return _ank_base.File(
                mountPoint=self.mount_point, data=self.content.value
            )
        if isinstance(self.content, BinaryFileContent):
            return _ank_base.File(
                mountPoint=self.mount_point, binaryData=self.content.value
            )
        # Unreachable code, as the content type
        # is checked in the methods above.
        raise ValueError(
            "Unsupported file content type. Expected Data or BinaryData."
        )  # pragma: no cover

    @staticmethod
    def _from_proto(proto_file: _ank_base.File) -> "File":
        """
        Create a File instance from a protobuf representation.

        :param proto_file: The protobuf file representation.
        :type proto_file: _ank_base.File

        :returns: A File instance created from the protobuf representation.
        :rtype: File

        :raises ValueError: If the protobuf file format is invalid.
        """
        if proto_file.data:
            return File.from_data(
                mount_point=proto_file.mountPoint, data=proto_file.data
            )
        if proto_file.binaryData:
            return File.from_binary_data(
                mount_point=proto_file.mountPoint,
                binary_data=proto_file.binaryData,
            )
        # Unreachable code, as the protobuf
        # should always have one of these fields.
        raise ValueError(
            "Invalid protobuf file format. "
            "Expected 'data' or 'binaryData' field."
        )  # pragma: no cover
