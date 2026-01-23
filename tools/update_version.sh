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
sdk_version=""
ankaios_version=""
api_version=""

usage() {
    echo "Usage: $0 [--sdk <VERSION>] [--ank <VERSION>] [--api <VERSION>] [--help]"
    echo "Update the SDK, Ankaios and API versions."
    echo "You can update all of them at once or one by one."
    echo "  --sdk <VERSION>    The new version of the SDK."
    echo "  --ank <VERSION>    The new version of Ankaios."
    echo "  --api <VERSION>    The new version for the supported API."
    echo "  --help             Display this help message and exit."
    echo ""
    echo "Example:"
    echo "  $0 --sdk 0.1.0 --ank 0.1.0 --api v1"
    exit 1
}

parse_arguments() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --sdk)
                shift
                sdk_version="$1"
                ;;
            --ank)
                shift
                ankaios_version="$1"
                ;;
            --api)
                shift
                api_version="$1"
                ;;
            --help|-h)
                usage
                ;;
            *)
                echo "Unknown argument: $1"
                usage
                ;;
        esac
        shift
    done
}

if [ "$#" -eq 0 ]; then
    usage
fi

parse_arguments "$@"

if [ -z "$sdk_version" ] && [ -z "$ankaios_version" ] && [ -z "$api_version" ]; then
    echo "You must specify at least one version to update."
    usage
fi

if [ -n "$sdk_version" ]; then
    echo "Updating SDK version to $sdk_version"
    sed -i "s/^version = .*/version = $sdk_version/" "$base_dir"/setup.cfg
fi

if [ -n "$ankaios_version" ]; then
    echo "Updating Ankaios version to $ankaios_version"
    sed -i "s/^ankaios_version = .*/ankaios_version = $ankaios_version/" "$base_dir"/setup.cfg
    sed -i "s/^ANKAIOS_VERSION = .*/ANKAIOS_VERSION = \"$ankaios_version\"/" "$base_dir"/ankaios_sdk/utils.py
fi

if [ -n "$api_version" ]; then
    echo "Updating API version to $api_version"
    sed -i "s/^SUPPORTED_API_VERSION = .*/SUPPORTED_API_VERSION = \"$api_version\"/" "$base_dir"/ankaios_sdk/utils.py
fi
