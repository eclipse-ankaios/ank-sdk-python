#!/bin/bash
# Copyright (c) 2026 Elektrobit Automotive GmbH
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
RUN_DIR="${SCRIPT_DIR}/ankaios_run"

if (( $# > 0 )); then
    echo "Usage: $0" >&2
    exit 1
fi

for name in ank-agent ank-server; do
    PID_FILE="${RUN_DIR}/${name}.pid"
    if [[ ! -f "${PID_FILE}" ]]; then
        continue
    fi
    read -r PID < "${PID_FILE}"
    if [[ ! "${PID}" =~ ^[1-9][0-9]*$ ]]; then
        echo "Invalid PID in '${PID_FILE}'; refusing to stop a process." >&2
        exit 1
    fi
    if kill -0 "${PID}" 2>/dev/null; then
        if [[ $(ps -p "${PID}" -o comm=) != "${name}" ]]; then
            echo "PID ${PID} is not ${name}; refusing to stop it." >&2
            exit 1
        fi
        echo "Stopping ${name} (${PID})."
        kill "${PID}"
        for (( attempt = 0; attempt < 50; attempt++ )); do
            if ! kill -0 "${PID}" 2>/dev/null ||
                [[ $(ps -p "${PID}" -o stat=) == Z* ]]; then
                break
            fi
            sleep 0.1
        done
        if kill -0 "${PID}" 2>/dev/null &&
            [[ $(ps -p "${PID}" -o stat=) != Z* ]]; then
            echo "${name} did not stop; keeping '${PID_FILE}'." >&2
            exit 1
        fi
    else
        echo "${name} (${PID}) is no longer running."
    fi
    rm -- "${PID_FILE}"
done

if [[ -S "${RUN_DIR}/ankaios.sock" ]]; then
    rm -- "${RUN_DIR}/ankaios.sock"
fi
echo "Ankaios stopped. Logs and agent runtime files remain in '${RUN_DIR}'."
echo "Containers are not stopped or removed by this script."
