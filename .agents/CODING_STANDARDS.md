# Coding Standards (Agent Reference)

These rules apply whenever an agent changes source code or tests in this
repository. For setup, running checks, and general code/test conventions,
see [DEVELOPMENT.md](../DEVELOPMENT.md).

## API and compatibility

- **Never break existing public API** — must keep semantic alignment with
  other Ankaios SDKs.
- **Exclude generated proto files from all checks** — `*_pb2.py` /
  `*_pb2_grpc.py` are auto-generated; never edit them.

## Testing

- **Tests must cover behavior, not lines** — write tests for what the code
  is supposed to do, not to satisfy a coverage metric. Coverage is a
  reviewer hint, not a goal; gaming it with shallow assertions is a defect.
  Concretely required:
  - Every distinct behavior and postcondition gets its own test
  - Every error condition is tested in every way it can be triggered
  - Every variant of a result type is exercised: both the success and
    failure paths of a function, every enum variant that can be returned

## Static analysis

- **Pylint score must stay at 10.0/10** — no new lint violations.
- **PEP 8 compliance is mandatory** — zero violations.
