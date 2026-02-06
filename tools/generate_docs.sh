#!/bin/bash

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

set -e

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
base_dir="$script_dir/.."

usage() {
    echo "Usage: $0 [--help]"
    echo ""
    echo "Generate project documentation using Sphinx."
    echo "Creates a temporary virtual environment, installs documentation"
    echo "dependencies, builds the HTML docs, and cleans up."
    echo ""
    echo "Output is saved to docs/build."
    echo ""
    echo "  --help    Display this help message and exit."
    exit 0
}

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    usage
fi

python3 -m venv docs_env
source docs_env/bin/activate

pip install ".[docs]"

cd "$base_dir/docs"

# make html
sphinx-build -b html source build -W --keep-going

cd "$base_dir"

deactivate
rm -rf docs_env

echo "Documentation generated successfully in docs/build"
