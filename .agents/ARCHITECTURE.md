# Architecture (Agent Reference)

Read this before making changes to `ControlInterface`, `Ankaios`, the
protocol layer, or exception handling.

## Control Interface

The SDK communicates with the Ankaios agent via a Unix socket at
`/run/ankaios/control_interface` (two FIFOs: `input` and `output`). Messages
are length-delimited protobuf (`_control_api` wrapping `_ank_base`).

`ControlInterface` runs a background reader thread that deserializes
incoming messages and dispatches them to `Ankaios` via callbacks. `Ankaios`
routes responses to the correct caller using a request-ID queue.

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
