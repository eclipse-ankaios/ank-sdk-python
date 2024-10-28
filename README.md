<picture style="padding-bottom: 1em;">
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/eclipse-ankaios/ankaios/blob/main/logo/Ankaios__logo_for_dark_bgrd_clipped.png">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/eclipse-ankaios/ankaios/blob/main/logo/Ankaios__logo_for_light_bgrd_clipped.png">
  <img alt="Shows Ankaios logo" src="https://github.com/eclipse-ankaios/ankaios/blob/main/logo/Ankaios__logo_for_light_bgrd_clipped.png">
</picture>

# Ankaios Python SDK for Eclipse Ankaios

Eclipse Ankaios provides workload and container orchestration for automotive
High Performance Computers (HPCs). While it can be used for various fields of
applications, it is developed from scratch for automotive use cases and provides
a slim yet powerful solution to manage containerized applications.

The Python SDK provides easy access from the container (workload) point-of-view
to manage the Ankaios system. A workload can use the Python SDK to run other workloads
and get the state of the Ankaios system. 

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

## Usage

After installation, you can use the Ankaios SDK to configure and run workloads and request
the state of the Ankaios system and the connected agents.

Example:
```python
from ankaios_sdk import Workload, Ankaios, WorkloadStateEnum, WorkloadSubStateEnum

# Connect to control interface
with Ankaios() as ankaios:
  # Create a new workload
  workload = Workload.builder() \
    .workload_name("dynamic_nginx") \
    .agent_name("agent_A") \
    .runtime("podman") \
    .restart_policy("NEVER") \
    .runtime_config("image: docker.io/library/nginx\ncommandOptions: [\"-p\", \"8080:80\"]") \
    .build()

  # Run the workload
  ret = ankaios.apply_workload(workload)

  # Check if the workload is scheduled and get the WorkloadInstanceName
  if ret is not None:
    workload_instance_name = ret["added_workloads"][0]

  # Request the workload state based on the workload instance name
  ret = ankaios.get_workload_state_for_instance_name(workload_instance_name)
  if ret is not None:
    print(f"State: {ret.state}, substate: {ret.substate}, info: {ret.additional_info}")

  # Wait until the workload reaches the running state
  ret = ankaios.wait_for_workload_to_reach_state(
    workload_instance_name,
    state=WorkloadStateEnum.RUNNING,
    timeout=5
    )
  if ret:
    print("Workload reached the RUNNING state.")

  # Request the state of the system, filtered with the agent name
  complete_state = ankaios.get_state(
    timeout=5,
    field_mask=["workloadStates.agent_A"])

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
