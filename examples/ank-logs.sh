#!/bin/bash
set -e

podman logs -f $(podman ps -a | grep $1 | awk '{print $1}')