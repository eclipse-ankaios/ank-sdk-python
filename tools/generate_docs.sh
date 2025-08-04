#!/bin/bash

python3 -m venv docs_env
source docs_env/bin/activate

pip install ".[docs]"

cd ../docs

# make html
sphinx-build -b html source build -W --keep-going

cd ..

deactivate
rm -rf docs_env

echo "Documentation generated successfully in docs/build"
