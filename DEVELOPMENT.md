# Development Guide

This guide provides information about the development tools and workflows available for this project.

## Quick Start

### Project Setup

Install the SDK in development mode with the dev dependencies:

```shell
pip install -e ".[dev]"
```

## Commands and Scripts

The project provides a unified check runner ([run_checks.py](./run_checks.py)) for common development workflows. For a complete list of the available checks and actions, run `python3 run_checks.py --help`.

In addition, the [tools](tools/) folder contains helper scripts for specific tasks. Check the tools [readme](tools/README.md) for more info.

## Updating Documentation

When making changes to project documentation, keep the following in mind:

**Documentation custom handling:**

There are markdown files which are part of the published documentation. Because the links do not work directly, a [custom code](docs/source/conf.py) replaces them with the correct linkage.

## Troubleshooting

### Tests fail with strange errors regarding the protobuf objects

If this is the case, the proto files do not match the local code. The fetching of the proto files is documented in the [setup.py](setup.py) script, in the `extract_the_proto_files` method. It might be the case that the proto files must be fetched again.

## Additional Resources

- [Contributing Guidelines](CONTRIBUTING.md)
- [Python Coding Guidelines](https://peps.python.org/pep-0008/)
