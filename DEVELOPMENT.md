# Development Guide

This guide provides information about the development tools and workflows available for this project.

## Quick Start

### Project Setup

Install the SDK in development mode with the dev dependencies:

```shell
pip install -e ".[dev]"
```

The project provides a unified check runner ([run_checks.py](./run_checks.py)) for common development workflows and helper scripts in the [tools](tools) directory for specific tasks. See the sections below for details.

## Development Checks

Common development commands via [run_checks.py](./run_checks.py). Run `python3 run_checks.py --help` for a complete list.

### Testing

| Command                         | Description                |
|---------------------------------|----------------------------|
| `python3 run_checks.py --utest` | Run unit tests with pytest |
| `python3 run_checks.py --cov`   | Run coverage analysis      |

### Code Quality

| Command                        | Description               |
|--------------------------------|---------------------------|
| `python3 run_checks.py --lint` | Run pylint linter         |
| `python3 run_checks.py --pep8` | Run PEP8 codestyle checks |

Additional arguments can be passed after the flag, e.g.:

```shell
python3 run_checks.py --utest --full-trace
```

## Helper Scripts

The [tools](tools) directory contains utility scripts for specific tasks. All scripts support the `--help` flag for detailed usage information.

### generate_docs.sh

Generates project documentation using Sphinx. Creates a temporary virtual environment, installs documentation dependencies, builds the HTML docs, and cleans up.

Output is saved to `docs/build`.

### update_version.sh

Updates SDK, Ankaios, and API versions across the project. Supports updating versions individually or all at once.

## Development Workflow

### Before Committing

Always run these checks before creating a pull request:

```shell
python3 run_checks.py --utest    # All tests pass
python3 run_checks.py --cov      # Coverage at 100%
python3 run_checks.py --lint     # Pylint score 10.0/10
python3 run_checks.py --pep8     # No PEP8 violations
```

### Updating Documentation

When making changes to project documentation, keep the following in mind:

**Documentation custom handling:**

There are markdown files which are prt of the published documentation. Because the links
do not work directly, a [custom code](docs/source/conf.py) replaces them with the correct linkage.

**Adding new tools:**

When adding a new tool or script to the [tools](tools) directory:

1. Update this DEVELOPMENT.md file with the tool's description and usage
2. Ensure the script includes a `--help` option with detailed usage information
3. Follow the pattern established by existing scripts

## Troubleshooting

### Tests fail with strange errors regarding the protobuf objects

If this is the case, the proto files do not match the local code. The fetching of the proto files is documented in the [setup.py](setup.py) script, in the `extract_the_proto_files` method. It might be the case that the proto files msut be fetched again.

## Additional Resources

- [Contributing Guidelines](CONTRIBUTING.md)
- [Python Coding Guidelines](https://peps.python.org/pep-0008/)
