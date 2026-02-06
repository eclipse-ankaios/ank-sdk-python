#!/bin/bash

# Copyright (c) 2026 Elektrobit Automotive GmbH
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

# Configuration
REPO="eclipse-ankaios/ankaios"
WORKFLOW_NAME="build.yml"
JOB_NAME="Build Linux {target} debian package"
ARTIFACT_NAME="ankaios-linux-{target}-bin"
INSTALL_LATEST_URL="https://github.com/eclipse-ankaios/ankaios/releases/latest/download/install.sh"
INSTALL_VERSION_URL="https://github.com/eclipse-ankaios/ankaios/releases/download/<version>/install.sh"
INSTALL_PATH="/usr/local/bin"
TEMP_DIR=$(mktemp -d)

# Variables
branch_name=""
action_id=""
version=""
gh_token=""

target=""
mode=""  # branch, action, version

usage() {
    echo "Usage: $0 [--branch <name>] [--action <id>] [--version <version>] [--latest] [--token <value>] [--help]"
    echo "Fetch the requested Ankaios binaries from Github."
    echo ""
    echo "  -b / --branch  <name>    Get binaries from the last successful action on this branch."
    echo "  -a / --action  <id>      Get binaries from the matching action."
    echo "  -v / --version <value>   Get binaries from this specific release version (example: v0.1.0)."
    echo "  -l / --latest            Get binaries from the latest release of Ankaios."
    echo "  -t / --token   <value>   GitHub token for authentication."
    echo "  -h / --help              Display this help message and exit."
    echo ""
    echo "Example:"
    echo "  $0 --branch main --token ghp_xxxxxxxxxxxxx"
    exit 1
}

multiple_arguments_error() {
    echo "Error: Only one of --branch, --action, --version, or --latest can be specified." >&2
    usage
}

parse_arguments() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --branch|-b)
                shift
                branch_name="$1"
                if [ -n "$mode" ]; then
                    multiple_arguments_error
                fi
                mode="branch"
                ;;
            --action|-a)
                shift
                action_id="$1"
                if [ -n "$mode" ]; then
                    multiple_arguments_error
                fi
                mode="action"
                ;;
            --version|-v)
                shift
                version="$1"
                if [ -n "$mode" ]; then
                    multiple_arguments_error
                fi
                mode="version"
                ;;
            --latest|-l)
                version="latest"
                if [ -n "$mode" ]; then
                    multiple_arguments_error
                fi
                mode="version"
                ;;
            --token|-t)
                shift
                gh_token="$1"
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
if [ -z "$mode" ]; then
    echo "Error: One of --branch, --action, --version, or --latest must be specified." >&2
    usage
fi

# Function to get target platform
get_target() {
    case "$(uname -m 2>/dev/null)" in
        x86_64|amd64)  echo amd64 ;;
        aarch64|arm64) echo arm64 ;;
        *)
            echo "Error: target architecture not supported" >&2
            exit 1
            ;;
    esac
}
target=$(get_target)

# Install by version

install_by_version() {
    if [ "$version" = "latest" ]; then
        curl -sfL "$INSTALL_LATEST_URL" | bash -
    else
        VERSION_URL=${INSTALL_VERSION_URL//<version>/$version}
        curl -sfL "$VERSION_URL" | bash -s -- -v "$version"
    fi
}
if [ "$mode" = "version" ]; then
    install_by_version
    exit 0
fi

# Install by branch

branch_exists() {
    if curl -s "https://api.github.com/repos/$REPO/branches/$1" | grep -q '"name":'; then
        return 0
    else
        return 1
    fi
}
get_action_id_for_branch() {
    # Get workflow ID
    WORKFLOW_ID=$(curl -s "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW_NAME" | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

    if [ -z "$WORKFLOW_ID" ]; then
        echo "Error: Workflow '$WORKFLOW_NAME' not found" >&2
        exit 1
    fi

    # Get recent runs and find one with successful job
    local job_name="${JOB_NAME//\{target\}/$target}"
    RUN_ID=$(curl -s "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW_ID/runs?branch=$branch_name&per_page=10" | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)
for run in data.get('workflow_runs', []):
    run_id = run['id']
    jobs_url = f\"https://api.github.com/repos/$REPO/actions/runs/{run_id}/jobs\"
    import urllib.request
    jobs_data = json.loads(urllib.request.urlopen(jobs_url).read())
    for job in jobs_data.get('jobs', []):
        if job['name'] == '$job_name' and job['conclusion'] == 'success':
            print(run_id)
            sys.exit(0)
")

    if [ -z "$RUN_ID" ]; then
        echo "Error: No runs with successful '$job_name' job found on branch '$branch_name'" >&2
        exit 1
    fi

    echo "$RUN_ID"
}
if [ "$mode" = "branch" ]; then
    if ! branch_exists "$branch_name"; then
        echo "Error: Branch '$branch_name' does not exist in repository '$REPO'" >&2
        exit 1
    fi

    action_id=$(get_action_id_for_branch)
    echo "Action ID found: $action_id"
fi

# Cleanup function
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Install by action

# Get artifact name
artifact_name="${ARTIFACT_NAME//\{target\}/$target}"

# Fetch artifact list
ARTIFACT_JSON=$(curl -s "https://api.github.com/repos/$REPO/actions/runs/$action_id/artifacts")

# Find artifact ID
ARTIFACT_ID=$(echo "$ARTIFACT_JSON" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for artifact in data.get('artifacts', []):
        if artifact.get('name') == '$artifact_name':
            print(artifact.get('id'))
            sys.exit(0)
    print('ERROR: Artifact not found', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)

if echo "$ARTIFACT_ID" | grep -q "ERROR"; then
    echo "Error: Could not find artifact '$artifact_name' in action $action_id" >&2
    exit 1
fi

echo "Downloading artifact..."

provide_token() {
    if [ -n "$GITHUB_TOKEN" ]; then
        gh_token="$GITHUB_TOKEN"
    else
        echo -n "Enter GitHub token: "
        read -sr gh_token
    fi
}
check_token() {
    if ! curl -s -H "Authorization: Bearer $gh_token" "https://api.github.com/user" | grep -q '"login":'; then
        echo "Error: Invalid GitHub token." >&2
        exit 1
    fi
}

if [ -z "$gh_token" ]; then
    provide_token
fi
check_token

# Download artifact - gh token required
HTTP_CODE=$(curl -L -w "%{http_code}" -o "$TEMP_DIR/artifact.zip" \
    -H "Authorization: Bearer $gh_token" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$REPO/actions/artifacts/$ARTIFACT_ID/zip")

if [ "$HTTP_CODE" != "200" ]; then
    echo "Error: Failed to download artifact (HTTP $HTTP_CODE)" >&2
    exit 1
fi

# Extract artifact
cd "$TEMP_DIR"
unzip -q artifact.zip

# Verify binaries
if [ ! -f "ank" ] || [ ! -f "ank-server" ] || [ ! -f "ank-agent" ]; then
    echo "Error: Expected binaries not found in artifact" >&2
    exit 1
fi

# Install binaries
echo "Installing binaries to $INSTALL_PATH..."

if [ -w "$INSTALL_PATH" ]; then
    SUDO=""
else
    SUDO="sudo"
fi

$SUDO cp ank "$INSTALL_PATH/ank"
$SUDO cp ank-server "$INSTALL_PATH/ank-server"
$SUDO cp ank-agent "$INSTALL_PATH/ank-agent"

$SUDO chmod +x "$INSTALL_PATH/ank"
$SUDO chmod +x "$INSTALL_PATH/ank-server"
$SUDO chmod +x "$INSTALL_PATH/ank-agent"

echo "Installation complete!"
