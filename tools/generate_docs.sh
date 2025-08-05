#!/bin/bash
set -e

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
base_dir="$script_dir/.."

python3 -m venv docs_env
source docs_env/bin/activate

pip install ".[docs]"

cd "$base_dir/docs"

# make html
sphinx-build -b html source build -W --keep-going

cd "$base_dir"

deactivate
rm -rf docs_env

echo "Documentation generated successfully in docs/build"
