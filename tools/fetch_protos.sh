#!/bin/bash
set -e

# Script to fetch the proto files from the Ankaios repository
# Usage: ./fetch_protos.sh <branch> [-v|--version <sdk_version>]

# Parse arguments
if [ $# -lt 1 ]; then
    echo "Error: Missing required argument <branch>" >&2
    echo "Usage: $0 <branch> [-v|--version <sdk_version>]" >&2
    exit 1
fi

BRANCH="$1"
shift

# Parse optional version argument
SDK_VERSION=""
while [ $# -gt 0 ]; do
    case "$1" in
        --version|-v)
            if [ -z "$2" ]; then
                echo "Error: version flag requires a value" >&2
                exit 1
            fi
            SDK_VERSION="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            echo "Usage: $0 <branch> [-v|--version <sdk_version>]" >&2
            exit 1
            ;;
    esac
done

# Extract SDK version from setup.cfg if not provided
if [ -z "$SDK_VERSION" ]; then
    SETUP_CFG="setup.cfg"
    if [ ! -f "$SETUP_CFG" ]; then
        echo "Error: setup.cfg not found in current directory" >&2
        exit 1
    fi

    SDK_VERSION=$(grep "^version = " "$SETUP_CFG" | sed 's/^version = //' | tr -d ' ')

    if [ -z "$SDK_VERSION" ]; then
        echo "Error: Could not extract version from $SETUP_CFG" >&2
        exit 1
    fi

    echo "Using SDK version from setup.cfg: $SDK_VERSION"
fi

# Setup paths
PROTO_DIR="ankaios_sdk/_protos/${SDK_VERSION}"
BASE_URL="https://raw.githubusercontent.com/eclipse-ankaios/ankaios/refs/heads/${BRANCH}/ankaios_api/proto"
PROTO_FILES=("ank_base.proto" "control_api.proto")

# Clean and create target directory
if [ -d "$PROTO_DIR" ]; then
    rm -rf "$PROTO_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to clean directory $PROTO_DIR" >&2
        exit 1
    fi
fi

mkdir -p "$PROTO_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create directory $PROTO_DIR" >&2
    exit 1
fi

# Download proto files
for PROTO_FILE in "${PROTO_FILES[@]}"; do
    URL="${BASE_URL}/${PROTO_FILE}"
    TARGET_PATH="${PROTO_DIR}/${PROTO_FILE}"

    HTTP_CODE=$(curl -s -w "%{http_code}" -o "$TARGET_PATH" "$URL")

    if [ "$HTTP_CODE" -ne 200 ]; then
        echo "Error: Failed to download $PROTO_FILE (HTTP $HTTP_CODE)" >&2
        echo "URL: $URL" >&2
        rm -f "$TARGET_PATH"
        exit 1
    fi

    if [ ! -s "$TARGET_PATH" ]; then
        echo "Error: Downloaded $PROTO_FILE is empty" >&2
        rm -f "$TARGET_PATH"
        exit 1
    fi

    echo "Successfully downloaded $PROTO_FILE"
done

echo "Done."
