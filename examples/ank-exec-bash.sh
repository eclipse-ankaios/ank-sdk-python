#!/bin/bash
set -e

podman exec -it $(podman ps -a | grep app | awk '{print $1}') bash
