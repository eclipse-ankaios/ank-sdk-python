# Agent Instructions

## 1) Understand the purpose

This project is the **Python SDK for Eclipse Ankaios** — a lightweight workload
orchestrator for automotive embedded devices and HPCs. The SDK gives Python
workloads running inside an Ankaios-managed container access to the Ankaios
Control Interface to manage (start, stop, update) other workloads and read
cluster state.

The SDK is published on PyPI as `ankaios-sdk`. Current version and compatible
Ankaios version are in `setup.cfg` under `[metadata]`.

## 2) Non-negotiable rules

- **Never break existing public API** — must keep semantic alignment with other Ankaios SDKs
- **Tests must cover behavior, not lines** — write tests for what the code is
  supposed to do, not to satisfy a coverage metric. Coverage is a reviewer
  hint, not a goal; gaming it with shallow assertions is a defect.
  Concretely required:
  - Every distinct behavior and postcondition gets its own test
  - Every error condition is tested in every way it can be triggered
  - Every variant of a result type is exercised: both the success and failure
    paths of a function, every enum variant that can be returned
- **Pylint score must stay at 10.0/10** — no new lint violations
- **PEP 8 compliance is mandatory** — zero violations
- **Never invent container images** — if an image is needed, ask the user
- **Exclude generated proto files from all checks** — `*_pb2.py` / `*_pb2_grpc.py` are auto-generated; never edit them
- **Keep the solution minimal** — avoid unrelated refactors or speculative features

## 3) Development reference

Read [DEVELOPMENT.md](DEVELOPMENT.md) before making changes. It covers setup,
how to run checks, and all code and test conventions.

## 4) Architecture

The SDK communicates with the Ankaios agent via a Unix socket at
`/run/ankaios/control_interface` (two FIFOs: `input` and `output`). Messages
are length-delimited protobuf (`_control_api` wrapping `_ank_base`).

`ControlInterface` runs a background reader thread that deserializes incoming
messages and dispatches them to `Ankaios` via callbacks. `Ankaios` routes
responses to the correct caller using a request-ID queue.

`Ankaios` is the primary entry point, typically used as a context manager:

```python
from ankaios_sdk import Ankaios

with Ankaios() as ankaios:
    state = ankaios.get_state(timeout=5)
```

Use `_ank_base` (from `ankaios_sdk._protos`) for proto message construction in
tests. Never import `_pb2` files directly from outside the `_protos` package.
User-facing code must not expose proto objects.

## 5) Exceptions

All exceptions derive from `AnkaiosException` (see `ankaios_sdk/exceptions.py`).
