# Agent Instructions

## Purpose

Python SDK for Eclipse Ankaios — enables workloads inside an Ankaios cluster to start/stop/update
workloads, read state, stream logs, subscribe to events, and manage configs.

The SDK is published on PyPI as `ankaios-sdk`. Current version and
compatible Ankaios version are in `setup.cfg` under `[metadata]`.

## Always applicable

- **Never invent container images** — if an image is needed, ask the user.
- **Keep the solution minimal** — avoid unrelated refactors or speculative
  features.

## Task-specific references

Read these only when they apply to the task at hand:

- [DEVELOPMENT.md](DEVELOPMENT.md) — required before making any code
  change: setup, how to run checks, code and test conventions.
- [.agents/CODING_STANDARDS.md](.agents/CODING_STANDARDS.md) — required
  before making any code or test change: API compatibility, coverage
  philosophy, lint/PEP 8 enforcement, generated proto file handling.
- [.agents/ARCHITECTURE.md](.agents/ARCHITECTURE.md) — required before
  touching `ControlInterface`, `Ankaios`, the protocol layer, or exception
  handling.
