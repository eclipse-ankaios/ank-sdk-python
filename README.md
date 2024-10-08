<picture style="padding-bottom: 1em;">
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/eclipse-ankaios/ankaios/blob/main/logo/Ankaios__logo_for_dark_bgrd_clipped.png">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/eclipse-ankaios/ankaios/blob/main/logo/Ankaios__logo_for_light_bgrd_clipped.png">
  <img alt="Shows Ankaios logo" src="https://github.com/eclipse-ankaios/ankaios/blob/main/logo/Ankaios__logo_for_light_bgrd_clipped.png">
</picture>

# Ankaios Python SDK for Eclipse Ankaios

Eclipse Ankaios provides workload and container orchestration for automotive
High Performance Computing Software (HPCs). While it can be used for various
fields of applications, it is developed from scratch for automotive use cases
and provides a slim yet powerful solution to manage containerized applications.

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
pip install -e .[dev]
```

## Usage

After installation, you can use the Ankaios SDK to configure and run workloads and request
the state of the Ankaios system and the connected agents. For more information, you can check
the documentation (TBD).

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
  ankaios.run_workload(workload)

  # Request the state of the system, filtered with the current workload
  complete_state = ankaios.get_state(
    timeout=5,
    field_mask=["workloadStates.agent_A.dynamic_nginx"])

  # Get the workload states present in the complete_state
  workload_states_dict = complete_state.get_workload_states().get_as_dict()

  # Get the state of the desired workload
  dynamic_nginx_state = workload_states_dict["agent_A"]["dynamic_nginx"].values()[0]

  # Check state
  if dynamic_nginx_state.state == WorkloadStateEnum.RUNNING and
    dynamic_nginx_state.substate == WorkloadSubStateEnum.RUNNING_OK:
    print("Workload started running succesfully")
  elif dynamic_nginx_state.state == WorkloadStateEnum.FAILED:
    print("Workload failed with the following substate: {}".format(
      dynamic_nginx_state.substate.name
    ))
```

## Contributing

This project welcomes contributions and suggestions. Before contributing, make sure to read the
[contribution guideline](CONTRIBUTING.md).

## License

Ankaios Python SDK is licensed using the Apache License Version 2.0.
