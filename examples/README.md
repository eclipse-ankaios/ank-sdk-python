# Basic Example Applications for the Python SDK

This basic example applications show how the Ankaios Python SDK can be used to interact with a running cluster.

## Prerequisites

In order to run the examples, Ankaios must be installed and available on the system. To install Ankaios, take a look at the [installation guide](https://eclipse-ankaios.github.io/ankaios/latest/usage/installation/#setup-with-script).

Alternatively you can compile from source and provide the path to the executables to the run scripts with the `ANK_BIN_DIR` environment variable.

[!IMPORTANT]
Make sure that no other Ankaios instance is running on the local machine. If there is an instance running, the example could change its configuration. The stop script would even stop all running instances and **delete all podman containers**. 

## Building and running

To build and run an example, just execute the `run_example.sh` script with the name of the target example as an argument. The the `hello_ankaios` example, the command would be:

```shell
./run_example.sh hello_ankaios
```

Of course, you are free to build manually if needed by calling the following command from inside an example folder:

```shell
podman build -t <example name>:latest .
```

## Stopping the example

To stop the example just call

```shell
./stop_example.sh
```

[!WARNING]
The stop script terminates all running ankaios instances, both server and agents and **delete all podman containers** on the system. If you don't want this, you would need to clean up manually. 

## Examples

This folder currently contains two examples:

### `hello_ankaios` 

This example executes a workload that runs the example script from the main [README](../README.md) of this repo.

Feel free to update the code in the example and test it with the `run_example.sh` script.

To view the log of the `hello_ankaios` workload just use the convenience script:

```shell
 ./ank-logs.sh hello_ankaios
```

## `sleepy` 

`sleepy` is an "empty" workload that just executes an endless sleep. 

This examples has the Python SDK installed and allows to execute an interactive shell in the container in order to manually trigger Python commands to interact with Ankaios.

To `exec` into the container, a convenience script is provided:

```shell
./ank-exec-bash.sh sleepy
```

where the argument of the script is the Ankaios workload name.

The script will run an interactive shell in the container where you can start the Python interpreter and start interacting with Ankaios, e.g.:

```shell
root@231bc8f2bca4:/usr/src/app# python3
Python 3.12.7 (main, Oct 19 2024, 01:09:09) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from ankaios_sdk import Workload, Ankaios, WorkloadStateEnum, AnkaiosException
>>> ankaios = Ankaios()
[2025-01-15 06:36:30] State changed to INITIALIZED
[2025-01-15 06:36:30] Started reading from the input pipe.
>>> print(f"state: {ankaios.get_state(field_masks=["workloadStates"])}")
state: desiredState {
  configs {
  }
}
workloadStates {
  agentStateMap {
    key: "agent_Py_SDK"
    value {
      wlNameStateMap {
        key: "sleepy"
...
```