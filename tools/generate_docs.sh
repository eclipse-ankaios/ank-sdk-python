#!/bin/bash
set -e

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
base_dir="$script_dir/.."

usage() {
    echo "Usage: $0 [--help]"
    echo ""
    echo "Generate project documentation using Sphinx."
    echo "Creates a temporary virtual environment, installs documentation"
    echo "dependencies, builds the HTML docs, and cleans up."
    echo ""
    echo "Output is saved to docs/build."
    echo ""
    echo "  --help    Display this help message and exit."
    exit 0
}

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    usage
fi

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
