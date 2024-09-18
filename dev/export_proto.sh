#!/bin/sh

# Set the ANKAIOS project root directory
ANKAIOS_ROOT="/workspace/ankaios"

cp $ANKAIOS_ROOT/api/proto/ank_base.proto $ANKAIOS_ROOT/python_sdk/ankaios_sdk/protos
cp $ANKAIOS_ROOT/api/proto/control_api.proto $ANKAIOS_ROOT/python_sdk/ankaios_sdk/protos

protoc --python_out=$ANKAIOS_ROOT/python_sdk/ankaios_sdk --proto_path=$ANKAIOS_ROOT/python_sdk/ankaios_sdk/protos ank_base.proto control_api.proto
