# Basic Command Interface Example Applications for the Python SDK

This basic example applications show how the Ankaios Python SDK can be used to interact with a running cluster by using the command interface to communicate directly with the Ankaios Server from outside an Ankaios managed container.

## Prerequisites

Install Ankaios using the [installation guide](https://eclipse-ankaios.github.io/ankaios/latest/usage/installation/#setup-with-script).
The agent needs Podman to run the example workloads. Unix domain sockets require
an Ankaios version with support for `unix://` endpoints.

Install the SDK with the `command` extra from the repository root:

```shell
pip install -e ".[command]"
```

## Starting Ankaios

From the repository root, enter the examples directory:

```shell
cd examples/command_interface
```

[start_ankaios.sh](start_ankaios.sh) starts a server and an agent named `agent_A`
in the background and waits for the agent to connect. Choose one transport:

```shell
# Plaintext TCP on 127.0.0.1:25551 (default)
./start_ankaios.sh

# Alternatively, a Unix domain socket in ankaios_run/
./start_ankaios.sh unix
```

The script uses `ank-server`, `ank-agent` and `ank` from `/usr/local/bin`.
To use another installation:

```shell
ANK_BIN_DIR=/path/to/ankaios/executables ./start_ankaios.sh
```

Logs, PID files and agent runtime files are stored in the ignored `ankaios_run/`
directory. Startup refuses to proceed if an Ankaios server or agent is already
running. If startup fails, the script attempts to stop the processes it started;
check the logs for details.

You can also use an already running cluster instead of these helper scripts.
The server listens on one endpoint, either TCP or a Unix domain socket.
For Unix sockets, use `unix://<absolute-path>` and ensure your user has access
to the socket; no TLS or `--insecure` flag is used.

## Running the examples

Run the scripts from this directory after Ankaios is ready.

Each script takes the server URL as its first argument, which selects the transport: `http://...` for TCP or `unix://...` for a Unix domain socket. It defaults to `http://127.0.0.1:25551`. The agent name, where used, is the second argument (default `agent_A`):

```shell
# TCP (default URL)
python3 basic_test.py

# Unix domain socket
python3 basic_test.py "unix://$PWD/ankaios_run/ankaios.sock" agent_A
```

The examples create and delete workloads named `dynamic_nginx` (port 8080) and
`count_to_five`. Use a development cluster where these names are not already used.

## Stopping Ankaios

If you started Ankaios with the helper script, stop it with:

```shell
./stop_ankaios.sh
```

[stop_ankaios.sh](stop_ankaios.sh) stops the agent and server using the recorded
PIDs and removes the example Unix socket. Logs and agent runtime files remain
for inspection. It does **not** stop or remove Podman containers; interrupted
examples can leave workload containers that you need to clean up manually.
If you started Ankaios manually, stop those processes yourself.

## Examples

This folder currently contains the following example scripts:

### `basic_test.py`

Applies a workload, waits for it to reach the `RUNNING` state, updates it, then deletes it, printing the workload states after every change.

### `logs_events_test.py`

Registers for events on a workload, applies it, then streams its logs (printing them) until they stop, printing any events received along the way.

### `connection_lifecycle_test.py`

Connects and disconnects several times in a row, printing the workload states each time. Takes only the server URL as argument.

### `test_reconnect.py`

Requests the workload states every second until interrupted (Ctrl+C), to observe the reconnect behaviour when the server is restarted. Takes only the server URL as argument.
