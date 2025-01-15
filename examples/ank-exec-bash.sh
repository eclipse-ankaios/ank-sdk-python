#!/bin/bash
set -e

podman exec -it $(podman ps -a | grep $1 | awk '{print $1}') bash
