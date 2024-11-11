# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BUILD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'build'))

# -- Read the setup.cfg file -------------------------------------------------
import configparser

config = configparser.ConfigParser()
config.read(os.path.join(ROOT_DIR, 'setup.cfg'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = config['metadata']['name']
author = config['metadata']['author']
copyright = f'2024, {author}'
version = config['metadata']['version']
license = config['metadata']['license']
language = 'en'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',          # Automatically documents your Python code
    'sphinx.ext.napoleon',         # Supports NumPy and Google-style docstrings
    'sphinx_autodoc_typehints',    # Handles type hints
    'sphinx.ext.viewcode',         # Adds links to the source code in the documentation
    'sphinx_mdinclude',            # For reading md files
]

templates_path = ['_templates']
exclude_patterns = []
autodoc_member_order = 'bysource'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Ensure that the build dir exists -----------------------------------------
if not os.path.exists(BUILD_DIR):
    os.makedirs(BUILD_DIR)

# -- Prepare the Contributing file - coc link -----------------------------------------
contrib_in = os.path.abspath(os.path.join(ROOT_DIR, 'CONTRIBUTING.md'))
contrib_out = os.path.abspath(os.path.join(BUILD_DIR, 'CONTRIBUTING.md'))
with open(contrib_in, 'r') as f:
    contrib = f.readlines()

for i, line in enumerate(contrib):
    if "./CODE_OF_CONDUCT.md" in line:
        contrib[i] = line.replace("./CODE_OF_CONDUCT.md", "./code_of_conduct.html")
        break
with open(contrib_out, 'w') as f:
    f.writelines(contrib)


# -- Prepare the Code of Conduct file - foot note warning -----------------------------------------
coc_in = os.path.abspath(os.path.join(ROOT_DIR, 'CODE_OF_CONDUCT.md'))
coc_out = os.path.abspath(os.path.join(BUILD_DIR, 'CODE_OF_CONDUCT.md'))
with open(coc_in, 'r') as f:
    coc = f.readlines()
for i, line in enumerate(coc):
    if "Committers[^1]" in line:
        coc[i] = line.replace("Committers[^1]", "Committers")
with open(coc_out, 'w') as f:
    f.writelines(coc[:-2])

# -- Prepare the ReadMe file - skip the image and the contributing + license -------------
read_me_in = os.path.abspath(os.path.join(ROOT_DIR, 'README.md'))
read_me_out = os.path.abspath(os.path.join(BUILD_DIR, 'README.md'))
with open(read_me_in, 'r') as f:
    readme = f.readlines()

start = stop = 0
for i, line in enumerate(readme):
    if "</picture>" in line:
        start = i+1
    if r"https://eclipse-ankaios.github.io/ank-sdk-python/" in line:
        stop = i
        break
with open(read_me_out, 'w') as f:
    f.writelines(readme[start:stop])
