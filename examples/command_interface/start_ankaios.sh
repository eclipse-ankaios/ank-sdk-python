#!/bin/bash
# Copyright (c) 2026 Elektrobit Automotive GmbH
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
RUN_DIR="${SCRIPT_DIR}/ankaios_run"
DEFAULT_ANKAIOS_BIN_PATH="/usr/local/bin"
ANK_BIN_DIR=${ANK_BIN_DIR:-${DEFAULT_ANKAIOS_BIN_PATH}}

display_usage() {
    echo "Usage: $0 [tcp|unix]"
    echo "Start an Ankaios server and agent_A for the command interface examples."
    echo "  tcp:  plaintext TCP on 127.0.0.1:25551 (default)"
    echo "  unix: Unix domain socket at ${RUN_DIR}/ankaios.sock"
    echo "Set ANK_BIN_DIR to override /usr/local/bin."
}

TLS_FLAGS=()
case ${1:-tcp} in
    tcp)
        SERVER_ADDRESS="127.0.0.1:25551"
        SERVER_URL="http://${SERVER_ADDRESS}"
        TLS_FLAGS=(--insecure)
        ;;
    unix)
        SERVER_ADDRESS="unix://${RUN_DIR}/ankaios.sock"
        SERVER_URL="${SERVER_ADDRESS}"
        ;;
    -h|--help)
        display_usage
        exit 0
        ;;
    *)
        display_usage >&2
        exit 1
        ;;
esac
if (( $# > 1 )); then
    display_usage >&2
    exit 1
fi

for name in ank-server ank-agent ank; do
    if [[ ! -x "${ANK_BIN_DIR}/${name}" ]]; then
        echo "Missing executable: ${ANK_BIN_DIR}/${name}" >&2
        exit 2
    fi
done

if pgrep -x ank-server >/dev/null || pgrep -x ank-agent >/dev/null; then
    echo "Ankaios is already running. Stop it before starting these examples." >&2
    exit 3
fi
if [[ -e "${RUN_DIR}/ank-server.pid" || -e "${RUN_DIR}/ank-agent.pid" ||
      -e "${RUN_DIR}/ankaios.sock" ]]; then
    echo "Runtime files already exist. Run ./stop_ankaios.sh first." >&2
    exit 3
fi

umask 077
mkdir -p "${RUN_DIR}/agent"
chmod 700 "${RUN_DIR}" "${RUN_DIR}/agent"

cleanup_on_failure() {
    echo "Startup failed. Check logs in '${RUN_DIR}'." >&2
    "${SCRIPT_DIR}/stop_ankaios.sh"
}
trap cleanup_on_failure ERR

echo "Starting Ankaios server on '${SERVER_ADDRESS}'."
RUST_LOG=debug "${ANK_BIN_DIR}/ank-server" "${TLS_FLAGS[@]}" \
    --address "${SERVER_ADDRESS}" > "${RUN_DIR}/ankaios-server.log" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${RUN_DIR}/ank-server.pid"

echo "Starting Ankaios agent 'agent_A'."
RUST_LOG=debug "${ANK_BIN_DIR}/ank-agent" "${TLS_FLAGS[@]}" \
    --name agent_A --server-url "${SERVER_URL}" \
    --run-folder "${RUN_DIR}/agent" > "${RUN_DIR}/ankaios-agent.log" 2>&1 &
AGENT_PID=$!
echo "${AGENT_PID}" > "${RUN_DIR}/ank-agent.pid"

for (( attempt = 0; attempt < 20; attempt++ )); do
    kill -0 "${SERVER_PID}"
    kill -0 "${AGENT_PID}"
    if timeout 2 "${ANK_BIN_DIR}/ank" "${TLS_FLAGS[@]}" \
        --server-url "${SERVER_URL}" get agents 2>/dev/null |
        grep -qw agent_A; then
        echo "Ankaios is ready. Logs are in '${RUN_DIR}'."
        echo "Run: python3 basic_test.py ${SERVER_URL}"
        echo "Stop with: ./stop_ankaios.sh"
        exit 0
    fi
    sleep 1
done

echo "Ankaios did not become ready in time." >&2
cleanup_on_failure
exit 4
