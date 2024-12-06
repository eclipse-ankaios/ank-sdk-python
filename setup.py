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

import os
from setuptools import setup, find_packages
import configparser

PROJECT_DIR = "ankaios_sdk"
ANKAIOS_RELEASE_LINK = "https://github.com/eclipse-ankaios/ankaios/releases/download/v{version}/{file}"
PROTO_FILES = ["ank_base.proto", "control_api.proto"]

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'setup.cfg'))


def extract_the_proto_files():
    """ Download the proto files from the ankaios release branch. """
    import requests

    ankaios_version = config['metadata']['ankaios_version']

    for file in PROTO_FILES:
        file_url = ANKAIOS_RELEASE_LINK.format(version=ankaios_version, file=file)
        file_path = f"{PROJECT_DIR}/_protos/{file}"
        if os.path.exists(file_path):
            continue
        try:
            response = requests.get(file_url)
            response.raise_for_status()
            with open(file_path, 'w', encoding="utf-8") as f:
                f.write(response.text)
        except requests.exceptions.RequestException as e:
            print(f"Error: Failed to download {file} from {file_url}.")
            raise e


def generate_protos():
    """Generate python protobuf files from the proto files."""
    from grpc_tools import protoc

    protos_dir = f"{PROJECT_DIR}/_protos"
    proto_files = PROTO_FILES

    for proto_file in proto_files:
        proto_path = os.path.join(protos_dir, proto_file)
        if not os.path.exists(proto_path):
            raise Exception(f"Error: {proto_file} not found.")
        output_file = proto_path.replace('.proto', '_pb2.py')

        if not os.path.exists(output_file) or os.path.getmtime(proto_path) > os.path.getmtime(output_file):
            print(f"Compiling {proto_path}...")
            command = [
                'grpc_tools.protoc',
                f'-I={protos_dir}',
                f'--python_out={protos_dir}',
                f'--grpc_python_out={protos_dir}',
                proto_path
            ]
            if protoc.main(command) != 0:
                raise Exception(f"Error: {proto_file} compilation failed")

            # Fix the import path in the generated control_api_pb2
            # https://github.com/protocolbuffers/protobuf/issues/1491#issuecomment-261914766
            if "control_api" in proto_file:
                with open(output_file, 'r') as file:
                    filedata = file.read()
                    newdata = filedata.replace(
                        "import ank_base_pb2 as ank__base__pb2",
                        "from . import ank_base_pb2 as ank__base__pb2")
                with open(output_file, 'w') as file:
                    file.write(newdata)


setup(
    description="Eclipse Ankaios Python SDK - provides a convenient Python interface for interacting with the Ankaios platform.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://eclipse-ankaios.github.io/ankaios/latest/",
    python_requires='>=3.9',
    package_dir={'': '.'},
    packages=find_packages(where="."),
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    project_urls={
        "Documentation": "https://eclipse-ankaios.github.io/ank-sdk-python/",
        "Source": "https://github.com/eclipse-ankaios/ank-sdk-python",
        "Bug Tracker": "https://github.com/eclipse-ankaios/ank-sdk-python/issues",
    },
    install_requires=[
        "protobuf==5.27.2",  # Protocol Buffers
        "PyYAML",  # Used to parse manifest files
    ],
    setup_requires=[
        "protobuf==5.27.2",  # Protocol Buffers
        "grpcio-tools==1.67.1",  # Needed for an OS independent protoc
        "requests",  # Used to download the proto files
    ],
    extras_require={
        # Development dependencies
        'dev': [
            'pytest',  # Testing framework
            'pytest-cov',  # Coverage plugin
            'pylint',  # Linter
            'pycodestyle',  # Style guide checker
        ],
        # Documentation dependencies
        'docs': [
            'sphinx',  # Documentation generator
            'sphinx-rtd-theme',  # Read the Docs theme
            'sphinx-autodoc-typehints',  # Type hints support
            'sphinx-mdinclude',  # Markdown include support
            'google-api-python-client',  # Required for the Google API docstring extension
        ],
    },
)


extract_the_proto_files()
generate_protos()
