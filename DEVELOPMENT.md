# Development Guide

This guide provides information about the development tools and workflows available for this project.

## Quick Start

### Project Setup

Install the SDK in development mode with the dev dependencies:

```shell
pip install -e ".[dev]"
```

## Commands and Scripts

All checks go through [run_checks.py](./run_checks.py) (one flag at a time):

```shell
python3 run_checks.py --utest   # unit tests
python3 run_checks.py --cov     # coverage report (use as a review hint, not a target)
python3 run_checks.py --lint    # pylint (enforces 10.0/10)
python3 run_checks.py --pep8    # PEP 8 style (enforces zero violations)
```

Extra arguments are forwarded to the underlying tool (pytest / pylint / pycodestyle):

```shell
python3 run_checks.py --utest tests/test_ankaios.py   # single file
python3 run_checks.py --utest -k test_apply_workload  # by keyword
```

The [tools/](tools/) folder contains helper scripts for specific tasks — see [tools/README.md](tools/README.md) for details. All scripts support `--help`:

- `fetch_protos.sh` — download proto files from a specific Ankaios branch
- `update_version.sh` — bump SDK, Ankaios, and API versions across the project
- `generate_docs.sh` — build Sphinx HTML docs into `docs/build/`
- `install_ankaios.sh` — install Ankaios runtime (release or CI artifacts)

## Code and Test Conventions

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

## Updating Documentation

When making changes to project documentation, keep the following in mind:

**Documentation custom handling:**

There are markdown files which are part of the published documentation. Because the links do not work directly, a [custom code](docs/source/conf.py) replaces them with the correct linkage.

## Troubleshooting

### Tests fail with strange errors regarding the protobuf objects

The proto files do not match the local code. Re-fetch them:

```shell
pip install -e .
# or for a specific Ankaios branch:
ANKAIOS_PROTO_BRANCH=my-feature-branch pip install -e .
```

The fetching logic is in [setup.py](setup.py) (`extract_the_proto_files`).

## Additional Resources

- [Contributing Guidelines](CONTRIBUTING.md)
- [Python Coding Guidelines](https://peps.python.org/pep-0008/)
