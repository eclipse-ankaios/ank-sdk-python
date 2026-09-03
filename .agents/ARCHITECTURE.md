# Architecture (Agent Reference)

Read this before making changes to `ControlInterfaceConnection`,
`CommandInterfaceConnection`, `Ankaios`, the protocol layer, or exception
handling.

## Connections

`Ankaios` talks to Ankaios through one of two interchangeable connections,
both implementing the `Connection` abstract base class
(`ankaios_sdk/_components/connection/connection.py`), picked via
`ConnectionType` at construction time:

- **Control Interface** (`ConnectionType.CONTROL_INTERFACE`, default) — used
  from inside an Ankaios-managed workload. Communicates via named pipes at
  `/run/ankaios/control_interface` (two FIFOs: `input` and `output`).
  Messages are length-delimited protobuf (`_control_api` wrapping
  `_ank_base`). Implemented by `ControlInterfaceConnection`.
- **Command Interface** (`ConnectionType.COMMAND_INTERFACE`) — used from
  outside a workload, connecting directly to the Ankaios server over gRPC.
  Only available if the SDK was installed with the `command` extra. Implemented
  by `CommandInterfaceConnection`.

Both run a background reader thread that deserializes incoming messages and
dispatches them to `Ankaios` via callbacks. `Ankaios` routes responses to the
correct caller using a request-ID queue.

`Ankaios` is the primary entry point, typically used as a context manager:

```python
from ankaios_sdk import Ankaios

with Ankaios() as ankaios:
    state = ankaios.get_state(timeout=5)
```

Use `_ank_base` (from `ankaios_sdk._protos`) for proto message construction
in tests. Never import `_pb2` files directly from outside the `_protos`
package. User-facing code must not expose proto objects.

## Exceptions

All exceptions derive from `AnkaiosException` (see
`ankaios_sdk/exceptions.py`).
