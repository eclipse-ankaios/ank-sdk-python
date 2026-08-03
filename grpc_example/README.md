# gRPC Connection Examples

Standalone scripts that connect to an Ankaios server directly over
gRPC (`ConnectionType.COMMAND_INTERFACE`), from *outside* a workload — unlike the
apps in [`../examples`](../examples), which run *inside* a workload
via the control interface.

## Prerequisites

An Ankaios server (and at least one agent) must already be running
and reachable, e.g. started locally with:

```shell
ank-server --insecure --address 0.0.0.0:25551 &
ank-agent --insecure --name agent_A --server-url http://127.0.0.1:25551 &
```

Install the SDK with the `grpc` extra from the repository root:

```shell
pip install -e ".[grpc]"
```

## Running

Each script takes the server URL and agent name as optional
positional arguments (defaulting to `http://127.0.0.1:25551` and
`agent_A`):

```shell
cd grpc_example
python3 basic_test.py [server_url] [agent_name]
python3 logs_events_test.py [server_url] [agent_name]
```

## Scripts

- **`basic_test.py`** — applies a workload, waits for it to reach the
  `RUNNING` state, updates it, then deletes it, printing the
  workload states after every change.
- **`logs_events_test.py`** — registers for events on a workload,
  applies it, then streams its logs (printing them) until they stop,
  printing any events received along the way.
- **`common.py`** — shared helpers used by the scripts above.
