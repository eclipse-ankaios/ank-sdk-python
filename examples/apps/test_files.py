import time
from ankaios_sdk import (
    Ankaios,
    File,
    Workload,
    AnkaiosException,
    DataFileContent,
    BinaryFileContent,
)


# Create a new Ankaios object.
# The connection to the control interface is automatically done at this step.
with Ankaios() as ank:
    # Create a workload with text file
    workload_with_text_file = (
        Workload.builder()
        .workload_name("nginx_with_text_file")
        .agent_name("agent_Py_SDK")
        .runtime("podman")
        .restart_policy("NEVER")
        .runtime_config(
            'image: docker.io/library/nginx:latest\ncommandOptions: ["-p", "8081:80"]'
        )
        .add_file(
            File.from_data(
                "/usr/share/nginx/html/index.html",
                "<html><body><h1>Hello from Ankaios with text file!</h1></body></html>",
            )
        )
        .add_file(
            File.from_data(
                "/etc/nginx/conf.d/custom.conf",
                "server {\n    listen 80;\n    server_name localhost;\n    location / {\n        root /usr/share/nginx/html;\n        index index.html;\n    }\n}",
            )
        )
        .build()
    )
    # Create a workload with binary file (base64 encoded)
    workload_with_binary_file = (
        Workload.builder()
        .workload_name("nginx_with_binary_file")
        .agent_name("agent_Py_SDK")
        .runtime("podman")
        .restart_policy("NEVER")
        .runtime_config(
            'image: docker.io/library/nginx:latest\ncommandOptions: ["-p", "8082:80"]'
        )
        .add_file(
            File.from_binary_data(
                "/usr/share/nginx/html/favicon.ico",
                "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAABILAAASCwAAAAAAAAAAAAD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A",
            )
        )
        .build()
    )
    print("Testing workload files functionality...")
    try:
        # Send first workload with text files to Ankaios
        print("Applying workload with text files...")
        ank.apply_workload(workload_with_text_file)
        # Wait and check states
        time.sleep(5)
        # Send second workload with binary file to Ankaios
        print("Applying workload with binary file...")
        ank.apply_workload(workload_with_binary_file)
        # Wait and check states
        time.sleep(5)
        # Test file manipulation - create a workload and then update its files
        print("Creating workload with initial file...")
        dynamic_workload = (
            Workload.builder()
            .workload_name("dynamic_file_workload")
            .agent_name("agent_Py_SDK")
            .runtime("podman")
            .restart_policy("NEVER")
            .runtime_config(
                'image: docker.io/library/nginx:latest\ncommandOptions: ["-p", "8083:80"]'
            )
            .build()
        )
        # Add initial file
        dynamic_workload.add_file(
            File.from_data(
                "/usr/share/nginx/html/index.html",
                "<html><body><h1>Initial content</h1></body></html>",
            )
        )
        ank.apply_workload(dynamic_workload)
        time.sleep(5)
        # Update the workload with additional files
        print("Updating workload with additional files...")
        files = [
            File.from_data(
                "/usr/share/nginx/html/about.html",
                "<html><body><h1>About page</h1><p>This is a dynamically added file!</p></body></html>",
            ),
            File.from_data(
                "/usr/share/nginx/html/config.json",
                '{"version": "1.0", "environment": "test", "features": ["files", "dynamic_updates"]}',
            ),
        ]
        dynamic_workload.update_files(files)
        ank.apply_workload(dynamic_workload)
        time.sleep(5)
        # Test retrieving and displaying file information
        print("Retrieving file information from workloads...")
        try:
            complete_state = ank.get_state(
                field_masks=["desiredState.workloads"]
            )
            workloads = complete_state.get_workloads()
            for workload in workloads:
                print(
                    f"The following files are associated with workload {workload.name}:"
                )
                wl_files = workload.get_files()
                for file in wl_files:
                    match file.content:
                        case DataFileContent():
                            print(
                                f"  Text file: {file.mount_point} - Content: {file.content.value}"
                            )
                        case BinaryFileContent():
                            print(
                                f"  Binary file: {file.mount_point} - Content: {file.content.value}"
                            )
        except AnkaiosException as e:
            print(f"Error retrieving workload files: {e}")
        # Clean up - delete workloads
        print("\nCleaning up workloads...")
        try:
            ank.delete_workload("nginx_with_text_file")
            ank.delete_workload("nginx_with_binary_file")
            ank.delete_workload("dynamic_file_workload")
        except AnkaiosException as e:
            print(f"Error during cleanup: {e}")
        # Final state check
        time.sleep(5)
    except AnkaiosException as e:
        print(f"Ankaios Exception occurred: {e}")
