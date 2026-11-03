# Command Interface Examples

Standalone scripts that connect to an Ankaios server directly over
the Command Interface (`ConnectionType.COMMAND_INTERFACE`) which uses 
the gRPC protocol, , from *outside* a workload — unlike the
apps in [`../examples`](../examples), which run *inside* a workload
via the control interface.

## Prerequisites

An Ankaios server (and at least one agent) must already be running
and reachable. A server listens on **one** endpoint only, either TCP or
a Unix domain socket, so pick the transport you want to test and start
the server and agent accordingly.

**Option 1: TCP**

```shell
ank-server --insecure --address 0.0.0.0:25551 &
ank-agent --insecure --name agent_A --server-url http://127.0.0.1:25551 &
```

**Option 2: Unix domain socket** (`unix://<absolute-path>`)

No TLS is used, so do not pass `--insecure`. The socket is created with
mode `0660`, so your user needs read and write access to the socket file,
for example by being in the socket's group (see `--socket-group` of
`ank-server`). Remove a stale socket file first if the server was not
shut down cleanly.

```shell
ank-server --address unix:///tmp/ankaios.sock &
ank-agent --name agent_A --server-url unix:///tmp/ankaios.sock &
```

Install the SDK with the `command` extra from the repository root:

```shell
pip install -e ".[command]"
```

## Running

Every script takes the server URL as its first argument, which selects
the transport: `http://...` for TCP or `unix://...` for a Unix domain
socket. It defaults to `http://127.0.0.1:25551`. The agent name, where
used, is the second argument (default `agent_A`):

```shell
cd command_example

# TCP (default URL)
python3 basic_test.py

# Unix domain socket
python3 basic_test.py unix:///tmp/ankaios.sock agent_A
```

The other scripts are run the same way.

To see the SDK reconnect, run `test_reconnect.py` and restart the server
while it runs. Over a Unix domain socket, a missing or inaccessible
socket fails right away with a clear error.

## Scripts

- **`basic_test.py`** — applies a workload, waits for it to reach the
  `RUNNING` state, updates it, then deletes it, printing the
  workload states after every change.
- **`logs_events_test.py`** — registers for events on a workload,
  applies it, then streams its logs (printing them) until they stop,
  printing any events received along the way.
- **`connection_lifecycle_test.py`** — connects and disconnects several
  times in a row, printing the workload states each time (`[server_url]`
  only, no agent name).
- **`test_reconnect.py`** — requests the workload states every second
  until interrupted (Ctrl+C), to observe the reconnect behaviour when
  the server is restarted (`[server_url]` only, no agent name).
- **`common.py`** — shared helpers used by the scripts above.
