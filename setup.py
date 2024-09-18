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
from grpc_tools import protoc


PROJECT_NAME = "AnkaiosSDK"


def generate_protos():
    """Generate python protobuf files from the proto files."""
    protos_dir = f"{PROJECT_NAME}/_protos"
    proto_files = ["ank_base.proto", "control_api.proto"]

    for proto_file in proto_files:
        proto_path = os.path.join(protos_dir, proto_file)
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
            

generate_protos()


setup(
    name=PROJECT_NAME,
    version="0.1.0",
    license="Apache-2.0",
    author="Elektrobit Automotive GmbH and Ankaios contributors",
    # author_email="",
    description="Eclipse Ankaios Python SDK provides a convenient python interface for interacting with the Ankaios platform.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://eclipse-ankaios.github.io/ankaios/latest/",
    python_requires='>=3.6',
    package_dir={'': '.'},
    packages=find_packages(where="."),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Documentation": "https://eclipse-ankaios.github.io/ankaios/latest/",
        "Source": "https://github.com/eclipse-ankaios/ank-sdk-python",
        "Bug Tracker": "https://github.com/eclipse-ankaios/ank-sdk-python/issues",
    },
    install_requires=[
        "setuptools",
        "protobuf",
        "grpcio-tools",
    ],
)
