# Agent Instructions

## 1) Understand the purpose

This file provides operational guidance for AI agents working in the
**ank-sdk-python** repository.

This project is the **Python SDK for Eclipse Ankaios** — a lightweight workload
orchestrator for automotive embedded devices and High Performance Computing
Platforms (HPCs). The SDK gives Python workloads running inside an
Ankaios-managed container access to the Ankaios Control Interface, so they can
manage (start, stop, update) other workloads and read cluster state.

The SDK is published on PyPI as `ankaios-sdk`. The current version and its
compatible Ankaios version are defined in `setup.cfg` under `[metadata]`.

## 2) Follow non-negotiable rules

- **Never break existing public API** — the SDK must keep semantic alignment
  with other Ankaios SDKs
- **100% test coverage is enforced** — every new or changed code path must be
  covered by unit tests
- **Pylint score must stay at 10.0/10** — no new lint violations are allowed
- **PEP 8 compliance is mandatory** — zero violations accepted
- **Never invent container images** — if an image is needed for examples or
  tests, ask the user
- **Exclude generated proto files from all checks** — `*_pb2.py` and
  `*_pb2_grpc.py` are auto-generated; never edit them manually
- **Keep the solution minimal** — avoid unrelated refactors, extra helpers, or
  speculative features

## 3) Understand the project layout

```text
ank-sdk-python/
├── ankaios_sdk/                  # Main SDK package
│   ├── __init__.py               # Top-level exports (re-exports everything public)
│   ├── ankaios.py                # Ankaios class — the primary user-facing API
│   ├── exceptions.py             # All SDK exceptions (all derive from AnkaiosException)
│   ├── utils.py                  # Constants, AnkaiosLogLevel, helper functions
│   ├── _components/              # Internal submodules, all re-exported via __init__.py
│   │   ├── workload.py           # Workload and AccessRightRule classes
│   │   ├── workload_builder.py   # WorkloadBuilder (fluent builder pattern)
│   │   ├── workload_state.py     # WorkloadExecutionState, WorkloadInstanceName,
│   │   │                         #   WorkloadState, WorkloadStateCollection,
│   │   │                         #   WorkloadStateEnum, WorkloadSubStateEnum
│   │   ├── complete_state.py     # CompleteState, AgentAttributes
│   │   ├── manifest.py           # Manifest (load from file/string/dict)
│   │   ├── request.py            # Request types: GetStateRequest,
│   │   │                         #   UpdateStateRequest, LogsRequest,
│   │   │                         #   LogsCancelRequest, EventsRequest,
│   │   │                         #   EventsCancelRequest
│   │   ├── response.py           # Response, ResponseType, UpdateStateSuccess,
│   │   │                         #   LogEntry, LogsStopResponse, EventEntry
│   │   ├── control_interface.py  # ControlInterface, ControlInterfaceState
│   │   ├── log_campaign.py       # LogCampaignResponse, LogQueue
│   │   ├── event_campaign.py     # EventQueue
│   │   └── file.py               # File, DataFileContent, BinaryFileContent
│   └── _protos/                  # Auto-generated protobuf files (do NOT edit)
│       ├── <version>/            # Proto source files for the current version
│       ├── ank_base_pb2.py       # Generated from ank_base.proto
│       ├── control_api_pb2.py    # Generated from control_api.proto
│       └── __init__.py           # Re-exports as _ank_base and _control_api
├── tests/                        # Unit tests (mirrors the structure of ankaios_sdk)
│   ├── test_ankaios.py
│   ├── test_complete_state.py
│   ├── test_control_interface.py
│   ├── test_manifest.py
│   ├── test_utils.py
│   ├── test_workload_builder.py
│   ├── test_event_campaign.py
│   ├── test_log_campaign.py
│   ├── workload/                 # Tests for Workload, AccessRightRule, File
│   ├── request/                  # Tests for each Request type
│   ├── response/                 # Tests for Response types
│   └── workload_state/           # Tests for WorkloadState types and enums
├── examples/                     # Usage examples and sample manifests
├── tools/                        # Helper scripts (fetch_protos.sh, update_version.sh, etc.)
├── docs/                         # Sphinx documentation sources
├── run_checks.py                 # Unified check runner (tests, coverage, lint, pep8)
├── setup.py                      # Build script; also downloads proto files on install
├── setup.cfg                     # Package metadata, pytest and coverage configuration
└── .pylintrc                     # Pylint config (disables E1101 and W0212 project-wide)
```

## 4) Set up the development environment

```sh
# Install the SDK with all dev dependencies
pip install -e ".[dev]"
```

If tests fail with strange protobuf-related errors, the proto files may be
stale. Re-fetch them:

```sh
pip install -e .
# or for a specific Ankaios branch:
ANKAIOS_PROTO_BRANCH=my-feature-branch pip install -e .
```

## 5) Run checks

All checks are driven through `run_checks.py`. Only one check type can be run
at a time.

### Run unit tests

```sh
python3 run_checks.py --utest
```

Pass extra pytest arguments directly after the flag:

```sh
# Run a single test file
python3 run_checks.py --utest tests/test_ankaios.py

# Run tests matching a keyword
python3 run_checks.py --utest -k test_apply_workload

# Run with full traceback on failures
python3 run_checks.py --utest --full-trace
```

Reports are saved to `reports/utest/utest_report.xml`.

### Run coverage (enforces 100%)

```sh
python3 run_checks.py --cov
```

HTML report: `reports/coverage/html/index.html`

### Run pylint (enforces 10.0/10)

```sh
python3 run_checks.py --lint
```

Report saved to `reports/pylint/pylint_report.txt`.

### Run PEP 8 style check (enforces zero violations)

```sh
python3 run_checks.py --pep8
```

Report saved to `reports/codestyle/codestyle_report.txt`.
Generated proto files (`*_pb2.py`, `*_pb2_grpc.py`) are excluded automatically.

## 6) Understand the architecture

### Control Interface

The SDK communicates with the Ankaios agent via a Unix socket at
`/run/ankaios/control_interface` (two FIFOs: `input` and `output`). Messages
are serialized as length-delimited protobuf (`_control_api` messages wrapping
`_ank_base` messages).

`ControlInterface` runs a background reader thread that deserializes incoming
messages and dispatches them to the `Ankaios` object via callbacks. `Ankaios`
routes responses to the correct caller using a request-ID queue.

### Ankaios class — primary API

`Ankaios` is the main entry point. It is typically used as a context manager:

```python
from ankaios_sdk import Ankaios

with Ankaios() as ankaios:
    state = ankaios.get_state(timeout=5)
```

Key public methods:

| Method                                          | Description                                           |
| ----------------------------------------------- | ----------------------------------------------------- |
| `apply_manifest(manifest)`                      | Apply a manifest (create/update workloads + configs)  |
| `delete_manifest(manifest)`                     | Delete workloads and configs defined in a manifest    |
| `apply_workload(workload)`                      | Add or update a single workload                       |
| `get_workload(name)`                            | Retrieve a workload by name                           |
| `delete_workload(name)`                         | Delete a workload                                     |
| `get_state(field_masks, timeout)`               | Get `CompleteState`, optionally filtered              |
| `get_workload_states()`                         | Get all workload execution states                     |
| `wait_for_workload_to_reach_state(...)`         | Poll until state matches                              |
| `update_configs / add_config / get_configs ...` | Manage Ankaios configs                                |
| `set_agent_tags / get_agents / get_agent`       | Read/write agent metadata                             |
| `request_logs(workload_names)`                  | Start a real-time log stream (`LogCampaignResponse`)  |
| `stop_receiving_logs(log_campaign)`             | Stop a log stream                                     |
| `register_event(filter)`                        | Subscribe to cluster events (returns `EventQueue`)    |
| `unregister_event(event_queue)`                 | Unsubscribe from events                               |

### Key constants (from `utils.py`)

| Constant                         | Meaning                                   |
| -------------------------------- | ----------------------------------------- |
| `DEFAULT_CONTROL_INTERFACE_PATH` | Base path for the control interface FIFOs |
| `WORKLOADS_PREFIX`               | Field mask prefix for workloads           |
| `CONFIGS_PREFIX`                 | Field mask prefix for configs             |
| `AGENTS_PREFIX`                  | Field mask prefix for agents              |
| `ANKAIOS_VERSION`                | Compatible Ankaios release version        |
| `SUPPORTED_API_VERSION`          | Manifest API version string               |

### Protobuf internals

Use `_ank_base` (from `ankaios_sdk._protos`) for low-level proto message
construction in tests. Never import `_pb2` files directly from outside the
`_protos` package. User-facing code must not expose proto objects.

## 7) Follow code and test conventions

### Code style

- PEP 8 enforced — max line length from `pycodestyle` defaults (79 chars)
- Every module, class, and public method must have a docstring following the
  existing style (see any `_components/*.py` for the pattern)
- Module-level `__all__` lists are required for all public modules
- Protected members (prefixed `_`) are used intentionally to hide internals
  from users; pylint `W0212` is suppressed project-wide
- Use `get_logger()` from `utils.py` — do not use `logging.getLogger` directly
- License header (Apache-2.0 SPDX) must appear at the top of every new source
  file

### Test conventions

- Tests live in `tests/` and mirror the `ankaios_sdk/_components/` structure
- Use `unittest.mock.patch` and `MagicMock` for all external dependencies
  (file I/O, the control interface socket,
  `ControlInterface.connect/disconnect/connected`)
- Each test module exports a `generate_test_<thing>()` helper function that
  other test modules can import to build fixtures
- Use `pytest.raises(ExceptionType)` for exception path testing
- Do **not** test the generated proto files or `__init__.py` re-exports (both
  are excluded from coverage)
- Accessing private members (e.g., `ankaios._control_interface`) in tests is
  normal and expected

### Typical test setup pattern

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

## 8) Understand the exception hierarchy

All exceptions derive from `AnkaiosException`:

| Exception                   | When raised                                      |
| --------------------------- | ------------------------------------------------ |
| `WorkloadFieldException`    | Invalid value for a workload field               |
| `WorkloadBuilderException`  | WorkloadBuilder used incorrectly                 |
| `InvalidManifestException`  | Manifest YAML is malformed or missing fields     |
| `ConnectionClosedException` | Control interface connection was closed          |
| `ResponseException`         | Unparseable response received                    |
| `ControlInterfaceException` | File I/O or connection operation failed          |
| `AnkaiosProtocolException`  | Unexpected message received from Ankaios         |
| `AnkaiosResponseError`      | Ankaios returned an error response               |

## 9) Work with the Workload builder

The fluent builder is the recommended way to create workloads:

```python
from ankaios_sdk import Workload

workload = Workload.builder() \
    .workload_name("nginx") \
    .agent_name("agent_A") \
    .runtime("podman") \
    .restart_policy("NEVER") \
    .runtime_config("image: docker.io/library/nginx\n"
                    + "commandOptions: [\"-p\", \"8080:80\"]") \
    .add_dependency("other_workload", "ADD_COND_RUNNING") \
    .add_tag("key1", "value1") \
    .build()
```

Valid `restart_policy` values: `NEVER`, `ON_FAILURE`, `ALWAYS`

Valid dependency conditions: `ADD_COND_RUNNING`, `ADD_COND_SUCCEEDED`,
`ADD_COND_FAILED`

## 10) Use helper scripts

All scripts are in `tools/` and support `--help`:

- `tools/fetch_protos.sh` — download proto files from a specific Ankaios branch
- `tools/update_version.sh` — bump SDK, Ankaios, and API versions across the
  project
- `tools/generate_docs.sh` — build Sphinx HTML docs into `docs/build/`
- `tools/install_ankaios.sh` — install Ankaios runtime (from release or CI
  artifacts)
