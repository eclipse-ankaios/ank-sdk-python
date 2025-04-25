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

# Path to the repo root
GIT_DIR="../"

# Get sorted tags
git fetch --tags
tags=$(git tag | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V)

declare -A latest_versions=()

# Group by minor and get the latest patch version
while read -r tag; do
    base_version=$(echo "$tag" | sed -E 's/^(v[0-9]+\.[0-9]+)\..*/\1/')
    latest_versions["$base_version"]="$tag"
done <<< "$tags"

# Compose version lists
latest_list=$(printf "%s\n" "${latest_versions[@]}" | sort -V)
BRANCHES="main,$(echo "$latest_list" | paste -sd, -)"
MAIN_BRANCH=$(echo "$latest_list" | sort -V | tail -n 1)

echo "Using branches: $BRANCHES"
echo "Main branch: $MAIN_BRANCH"

# Run sphinx-versioned
# For all tags: --branch main,+v*,-*rc*
sphinx-versioned -O "build_versioned" \
  --git-root "$GIT_DIR" \
  --local-conf source/conf.py \
  --branch "$BRANCHES" \
  --main-branch "$MAIN_BRANCH"
