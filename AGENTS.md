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
- **100% test coverage is enforced** — every new or changed code path must be covered
- **Pylint score must stay at 10.0/10** — no new lint violations
- **PEP 8 compliance is mandatory** — zero violations
- **Never invent container images** — if an image is needed, ask the user
- **Exclude generated proto files from all checks** — `*_pb2.py` / `*_pb2_grpc.py` are auto-generated; never edit them
- **Keep the solution minimal** — avoid unrelated refactors or speculative features

## 3) Development environment

```sh
pip install -e ".[dev]"
```

If tests fail with protobuf errors, re-fetch proto files:

```sh
pip install -e .
# or for a specific branch:
ANKAIOS_PROTO_BRANCH=my-feature-branch pip install -e .
```

## 4) Run checks

All checks go through `run_checks.py` (one flag at a time):

```sh
python3 run_checks.py --utest   # unit tests
python3 run_checks.py --cov     # coverage (enforces 100%)
python3 run_checks.py --lint    # pylint (enforces 10.0/10)
python3 run_checks.py --pep8    # PEP 8 style (enforces zero violations)
```

All commands accept extra arguments that are forwarded to the underlying tool
(pytest / pylint / pycodestyle), e.g.:

```sh
python3 run_checks.py --utest tests/test_ankaios.py   # single file
python3 run_checks.py --utest -k test_apply_workload  # by keyword
```

## 5) Architecture

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

## 6) Code and test conventions

- Max line length: 79 chars (pycodestyle default)
- Every module, class, and public method needs a docstring (follow existing style in `_components/*.py`)
- Module-level `__all__` is required for all public modules
- Use `get_logger()` from `utils.py` — not `logging.getLogger` directly
- Apache-2.0 SPDX license header at the top of every new source file
- Tests mirror the `ankaios_sdk/_components/` structure
- Use `unittest.mock.patch` / `MagicMock` for all external dependencies
- Each test module exports a `generate_test_<thing>()` helper for fixtures
- Accessing private members in tests (e.g. `ankaios._control_interface`) is normal

**Typical test setup pattern:**

```python
from unittest.mock import patch, PropertyMock
from ankaios_sdk import Ankaios, ControlInterfaceState

def generate_test_ankaios() -> Ankaios:
    with patch("ankaios_sdk.ControlInterface.connect"), patch(
        "ankaios_sdk.ControlInterface.connected", new_callable=PropertyMock
    ) as mock_connected:
        mock_connected.return_value = True
        ankaios = Ankaios()
    ankaios._control_interface._state = ControlInterfaceState.CONNECTED
    return ankaios
```

## 7) Exceptions

All exceptions derive from `AnkaiosException` (see `ankaios_sdk/exceptions.py`).

## 8) Helper scripts (`tools/`, all support `--help`)

- `fetch_protos.sh` — download proto files from a specific Ankaios branch
- `update_version.sh` — bump SDK, Ankaios, and API versions across the project
- `generate_docs.sh` — build Sphinx HTML docs into `docs/build/`
- `install_ankaios.sh` — install Ankaios runtime (release or CI artifacts)
