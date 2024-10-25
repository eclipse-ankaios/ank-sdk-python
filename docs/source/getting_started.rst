Getting started
===============

For installation of the Ankaios SDK, see the `Installation section <index.html#installation>`_.

Once the SDK is installed, you can start using it by importing the module and creating a client object.

.. code-block:: python

    from ankaios import Ankaios

    ankaios = Ankaios()

The initialization of the Ankaios object will automatically connect to the fifo pipes of the control interface. Once this is done,
the communication with the Ankaios ecosystem can be started.

**Apply a manifest**
--------------------

Considering we have a manifest file with a workload called ``nginx_test`` and a config called ``test_ports``. The manifest file is as follows:

.. code-block:: yaml
    :caption: my_manifest.yaml

    apiVersion: v0.1
    workloads:
        nginx_test:
            runtime: podman
            restartPolicy: NEVER
            agent: agent_A
            configs:
                ports: test_ports
            runtimeConfig: |
                image: image/test
    configs:
        test_ports:
            port: \"8081\"

The manifest can now be applied using the following code:

.. code-block:: python

    from ankaios import Ankaios, Manifest

    # Create an Ankaios object
    ankaios = Ankaios()

    # Load the manifest from the file
    manifest = Manifest.from_file('my_manifest.yaml')

    # Apply the manifest and get the result
    ret = ankaios.apply_manifest(manifest)

    # Get the workload instance name
    wl_instance_name = ret["added_workloads"][0]

    # Print the instance name
    print(wl_instance_name)

IF the operation is succesfull, the result will contain a list with the added workloads that contains the workload instance name of our own.
The workload instance name contains the name of the workload, the agent it is running on and an unique identifier.

**Update a workload**
---------------------

Considering we have the above workload running, we can update certain parameters of the workload. For this example, we will update the `restartPolicy`. To be able to pin-point
the exact workload we want to modify, we must know the workload instance name. This can be obtained as a result when starting the workload (either using `apply_manifest` or other methods),
deleting or modifying a one.. In case we don't have the workload instance name, we can take all the workloads that have the same name as the one we are looking for (or the agent).
For simplisity, we will consider the workload instance name is known.

.. code-block:: python

    from ankaios import Ankaios

    # Create an Ankaios object
    ankaios = Ankaios()

    # Considering we have the workload instance name
    wl_instance_name = WorkloadInstanceName(...)

    # Get the workload base don the instance name
    workload = ankaios.get_workload_with_instance_name(wl_instance_name)

    # Update the restart policy
    ret = workload.update_restart_policy("ALWAYS")

    # Unpack the result
    added_workloads = ret["added_workloads"]
    deleted_workloads = ret["deleted_workloads"]

Depending on the updated parameter, the workload can be restarted or not. If this is the case, the `deleted_workloads` will contain the old instance name and 
the `added_workloads` will contain the new one.

**Get the state of a workload**
-------------------------------

Having a workload running in the Ankaios system, we can retrieve the state of the workload. The state has two fields, a primary state and a substate (See `Workload States <workload_state.html>`_).
Using the workload instance name, we can get the state of our specific workload.

.. code-block:: python

    from ankaios import Ankaios

    # Create an Ankaios object
    ankaios = Ankaios()

    # Considering we have the workload instance name
    wl_instance_name = WorkloadInstanceName(...)

    # Get the workload state based on the instance name
    execution_state = ankaios.get_execution_state_for_instance_name(wl_instance_name)

    # Output the state
    print(execution_state.state)
    print(execution_state.substate)
    print(execution_state.info)

If the workload instance name is not known, the state can be retrieved using the workload name or the agent name. This will return a `WorkloadStateCollection <workload_state.html#workloadstatecollection-class>`_
that contains all the workload states that match.

**Get the complete state**
--------------------------

The complete state of the Ankaios system can be retrieved using the following code:

.. code-block:: python

    from ankaios import Ankaios

    # Create an Ankaios object
    ankaios = Ankaios()

    # Get the complete state
    complete_state = ankaios.get_state()

    # Output the state
    print(complete_state)

The complete state contains information regarding the workloads running in the ANkaios cluster, configurations and agents. The state can be filtered using filter masks
(See `get_state <ankaios.html#ankaios_sdk.ankaios.Ankaios.get_state>`_).

**Delete a workload**
---------------------

To delete a workload, there are multiple methods. We can either use the same manifest that we used to start it and call `delete_manifest` with it or we can
delete the workload based on it's name. In this example, we will delete the workload using the manifest. Considering the same manifest as before (`my_manifest.yaml <getting_started.html#id1>`_):

.. code-block:: python

    from ankaios import Ankaios, Manifest

    # Create an Ankaios object
    ankaios = Ankaios()

    # Load the manifest from the file
    manifest = Manifest.from_file('my_manifest.yaml')

    # Delete the manifest (this will delete the workload contained in the manifest)
    ret = ankaios.delete_manifest(manifest)

    # Get the workload instance name
    wl_instance_name = ret["deleted_workloads"][0]

    # Print the instance name of the deleted workload
    print(wl_instance_name)

Notes
-----

* Exceptions might be raised during the usage of the sdk. For this, please see the `Exceptions section <exceptions.html>`_.
* For any issue or feature request, please see the `Issues section <https://github.com/eclipse-ankaios/ank-sdk-python/issues>`_.
