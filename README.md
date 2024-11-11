<picture style="padding-bottom: 1em;">
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/eclipse-ankaios/ankaios/refs/heads/main/logo/Ankaios__logo_for_dark_bgrd_clipped.png">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/eclipse-ankaios/ankaios/refs/heads/main/logo/Ankaios__logo_for_light_bgrd_clipped.png">
  <img alt="Shows Ankaios logo" src="https://raw.githubusercontent.com/eclipse-ankaios/ankaios/refs/heads/main/logo/Ankaios__logo_for_light_bgrd_clipped.png">
</picture>

# Python SDK for Eclipse Ankaios

![Build](https://github.com/eclipse-ankaios/ank-sdk-python/actions/workflows/build.yml/badge.svg?job=build)
![PyPI - Version](https://img.shields.io/pypi/v/ankaios_sdk)
![Python](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11%20|%203.12%20|%203.13-blue)
![OS](https://img.shields.io/badge/os-independent-lightgrey)

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
[![Ankaios](https://img.shields.io/badge/main_project-repo-blue)](https://github.com/eclipse-ankaios/ankaios)
[![Slack](https://img.shields.io/badge/slack-join-blue?logo=slack)](https://join.slack.com/t/ankaios/shared_invite/zt-2inyhbehh-iVp3YZD09VIgybv8D1gDpQ)

[Eclipse Ankaios](https://github.com/eclipse-ankaios/ankaios) provides workload and container orchestration for automotive
High Performance Computers (HPCs). While it can be used for various fields of
applications, it is developed from scratch for automotive use cases and provides
a slim yet powerful solution to manage containerized applications.

The Python SDK provides easy access from the container (workload) point-of-view
to manage the Ankaios system. A workload can use the Python SDK to start, stop and
update other workloads and configs and get the state of the Ankaios system.

## Installation

### Install via pip

```sh
pip install ankaios-sdk
```

### Clone and Local Build

```sh
# Clone repository
git clone https://github.com/eclipse-ankaios/ank-sdk-python.git
cd ank-sdk-python

# Install in editable mode
pip install -e .

# If you plan on contributing or running tests locally
pip install -e ".[dev]"
```

> **Note:**  
> Depending on your Linux distribution, it could be that you need to create and activate a [virtual environment](https://docs.python.org/3/library/venv.html) to run the pip commands.

## Compatibility

Please make sure the Python SDK is compatible with the version of Ankaios you are using. For information regarding versioning, please refer to this table:

| Ankaios    | Python SDK |
| -------- | ------- |
| 0.4.x and below | No Python SDK available. Please update Ankaios. |
| 0.5.x | 0.5.x     |

## Usage

After installation, you can use the Ankaios SDK to configure and run workloads and request
the state of the Ankaios system and the connected agents.

Example:
```python
from ankaios_sdk import Workload, Ankaios, WorkloadStateEnum, AnkaiosException

# Create a new Ankaios object.
# The connection to the control interface is automatically done at this step.
ankaios = Ankaios()

# Create a new workload
workload = Workload.builder() \
  .workload_name("dynamic_nginx") \
  .agent_name("agent_A") \
  .runtime("podman") \
  .restart_policy("NEVER") \
  .runtime_config("image: docker.io/library/nginx\ncommandOptions: [\"-p\", \"8080:80\"]") \
  .build()

try:
  # Run the workload
  update_response = ankaios.apply_workload(workload)

  # Get the WorkloadInstanceName to check later if the workload is running
  workload_instance_name = update_response.added_workloads[0]

  # Request the execution state based on the workload instance name
  ret = ankaios.get_execution_state_for_instance_name(workload_instance_name)
  if ret is not None:
    print(f"State: {ret.state}, substate: {ret.substate}, info: {ret.additional_info}")

  # Wait until the workload reaches the running state
  try:
    ankaios.wait_for_workload_to_reach_state(
      workload_instance_name,
      state=WorkloadStateEnum.RUNNING,
      timeout=5
      )
  except TimeoutError:
    print("Workload didn't reach the required state in time.")
  else:
    print("Workload reached the RUNNING state.")

# Catch the AnkaiosException in case something went wrong with apply_workload
except AnkaiosException as e:
  print("Ankaios Exception occured: ", e)

# Request the state of the system, filtered with the agent name
complete_state = ankaios.get_state(
  timeout=5,
  field_masks=["workloadStates.agent_A"])

# Get the workload states present in the complete_state
workload_states_dict = complete_state.get_workload_states().get_as_dict()

# Print the states of the workloads:
for workload_name in workload_states_dict["agent_A"]:
  for workload_id in workload_states_dict["agent_A"][workload_name]:
    print(f"Workload {workload_name} with id {workload_id} has the state "
          + str(workload_states_dict["agent_A"] \
                [workload_name][workload_id].state))
```

## Contributing

This project welcomes contributions and suggestions. Before contributing, make sure to read the
[contribution guideline](CONTRIBUTING.md).

## License

Ankaios Python SDK is licensed using the Apache License Version 2.0.
