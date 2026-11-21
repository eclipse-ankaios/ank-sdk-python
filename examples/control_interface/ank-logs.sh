#!/bin/bash
set -e

podman logs -f $(podman ps -a | grep app | awk '{print $1}')
