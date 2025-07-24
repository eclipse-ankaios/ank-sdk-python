#!/bin/bash

# Cleanup Ankaios ....
echo "Cleaning up Ankaios..."
pkill ank-agent
pkill ank-server
echo "OK."

# Cleanup podman
echo "Cleaning up podman..."
podman ps -q --filter ancestor="localhost/app:0.1" | xargs -r podman stop >/dev/null 2>&1
podman ps -q --filter ancestor="localhost/app:0.1" | xargs -r podman rm >/dev/null 2>&1
echo "OK."
