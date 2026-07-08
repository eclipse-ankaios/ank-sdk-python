# Agent Instructions

## Purpose

This project is the **Python SDK for Eclipse Ankaios** — a lightweight
workload orchestrator for automotive embedded devices and HPCs. The SDK
gives Python workloads running inside an Ankaios-managed container access
to the Ankaios Control Interface to manage (start, stop, update) other
workloads and read cluster state.

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
