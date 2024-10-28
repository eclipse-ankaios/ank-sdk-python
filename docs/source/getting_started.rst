Getting started
===============

For installation of the Ankaios SDK, see the `Installation section <index.html#installation>`_.

Once the SDK is installed, you can start using it by importing the module and creating an Ankaios object.

.. code-block:: python

    from ankaios import Ankaios

    ankaios = Ankaios()

The initialization of the Ankaios object will automatically connect to the fifo pipes of the control interface. Once this is done,
the communication with the Ankaios cluster can be started.

**Apply a manifest**
--------------------

Considering we have the following manifest file with a workload called ``nginx``:

.. code-block:: yaml
    :caption: my_manifest.yaml

    apiVersion: v0.1
    workloads:
        nginx:
            runtime: podman
            restartPolicy: NEVER
            agent: agent_A
            runtimeConfig: |
                image: image/nginx

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

    # Get the workload state based on the instance name
    execution_state = ankaios.get_execution_state_for_instance_name(wl_instance_name)

    # Output the state
    print(execution_state.state)
    print(execution_state.substate)
    print(execution_state.additional_info)

If the operation is successful, the result will contain a list with the added workloads that contains the workload instance name of the newly added workload.
The workload instance name contains the name of the workload, the agent it is running on and a unique identifier. Using it, we can request the current execution state of
the workload. The state has 3 elements: the primary state, the substate and additional information (See `Workload States <workload_state.html>`_).

**Get the complete state**
--------------------------

The complete state of the Ankaios system can be retrieved using the ``get_state`` method of the ``Ankaios`` class:

.. code-block:: python

    from ankaios import Ankaios

    # Create an Ankaios object
    ankaios = Ankaios()

    # Get the complete state
    complete_state = ankaios.get_state()

    # Output the state
    print(complete_state)

The complete state contains information regarding the workloads running in the Ankaios cluster, configurations and agents. The state can be filtered using filter masks
(See `get_state <ankaios.html#ankaios_sdk.ankaios.Ankaios.get_state>`_).

**Update a workload**
---------------------

Considering we have the above workload running, we can now modify it. For this example we will update the ``restartPolicy``. To be able to pinpoint
the exact workload we want to modify, we must know only it's name. 

.. code-block:: python

    from ankaios import Ankaios

    # Create an Ankaios object
    ankaios = Ankaios()

    # Get the workload based on the name
    workload = ankaios.get_workload("nginx")

    # Update the restart policy
    ret = workload.update_restart_policy("ALWAYS")

    # Unpack the result
    added_workloads = ret["added_workloads"]
    deleted_workloads = ret["deleted_workloads"]

Depending on the updated parameter, the workload can be restarted or not. If this is the case, the ``deleted_workloads`` will contain the old instance name and 
the ``added_workloads`` will contain the new one.

**Delete a workload**
---------------------

There are multiple methods to delete a workload: we can either use the same manifest that we used to start it and call ``delete_manifest`` or we can
delete the workload based on its name. In this example, we will delete the workload using the manifest. Considering the same manifest as before (`my_manifest.yaml <getting_started.html#id1>`_):

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

* Exceptions might be raised during the usage of the SDK. Please consult the `Exceptions section <exceptions.html>`_ for a complete list.
* For any issue or feature request, please see the `Contributing section <contributing.html>`_.
