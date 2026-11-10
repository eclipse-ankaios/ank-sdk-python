# Basic Command Interface Example Applications for the Python SDK

This basic example applications show how the Ankaios Python SDK can be used to interact with a running cluster by using the command interface to communicate directly with the Ankaios Server from outside an Ankaios managed container.

## Prerequisites

In order to run the examples, an Ankaios server and at least one agent must already be running and reachable. A server listens on **one** endpoint only, either TCP or a Unix domain socket, so pick the transport you want to test and start the server and agent accordingly.

**Option 1: TCP**

```shell
ank-server --insecure --address 0.0.0.0:25551 &
ank-agent --insecure --name agent_A --server-url http://127.0.0.1:25551 &
```

**Option 2: Unix domain socket** (`unix://<absolute-path>`)

No TLS is used, so do not pass `--insecure`. The socket is created with mode `0660`, so your user needs write access to the socket file, for example by being in the socket's group (see `--socket-group` of `ank-server`). Remove a stale socket file first if the server was not shut down cleanly.

```shell
ank-server --address unix:///tmp/ankaios.sock &
ank-agent --name agent_A --server-url unix:///tmp/ankaios.sock &
```

Install the SDK with the `command` extra from the repository root:

```shell
pip install -e ".[command]"
```

## Running the examples

Enter the examples dir:

```shell
cd examples/command_interface
```

Each script takes the server URL as its first argument, which selects the transport: `http://...` for TCP or `unix://...` for a Unix domain socket. It defaults to `http://127.0.0.1:25551`. The agent name, where used, is the second argument (default `agent_A`):

```shell
# TCP (default URL)
python3 basic_test.py

# Unix domain socket
python3 basic_test.py unix:///tmp/ankaios.sock agent_A
```

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

### `common.py`

Shared helpers used by the scripts above.
