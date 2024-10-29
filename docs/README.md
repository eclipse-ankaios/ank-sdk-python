## Documentation

The documentation can be automatically generated using the script `generate_docs.sh`. This will create a virtual environment, install the
necesarry dependencies, generate the documentation and then delete that temporary environment.

All the steps can be done manually as well. The documentation dependencies can be installed by running the `pip install` with the `docs` extra, and the
documentation can be handled by the Makefile:

```sh
pip install -e ".[docs]"

# To install both the dev and docs dependencies
# pip install -e ".[dev, docs]"

cd docs

# This will generate the documentation
make html

# This will open the documentation on localhost:8001
make open

# This will delete the build of the documentation
make clean
```
