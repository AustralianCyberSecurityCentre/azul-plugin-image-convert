# Azul Plugin Image Convert

This plugin takes potentially malicious images and converts them to a format that is safe to display.

## Development Installation

To install azul-plugin-image-convert for development run the command
(from the root directory of this project):

```bash
pip install -e .
```

## Usage

Usage on local files:

```
azul-plugin-image-convert malware.file
```

Example Output:

```
----- ImageConvert results -----
OK

events (1)

event for binary:cmdline_entity:None
  {}
  output data streams (1):
    5455 bytes - EventData(hash='b4bdcf6ae3c8a94f0d9339366c9fc692860cbe8b4d7ea940ddc846f2ca3cffd8', label='safe_png')
```

Automated usage in system:

```
azul-plugin-image-convert --server http://azul-dispatcher.localnet/
```

## Python Package management

This python package is managed using a `setup.py` and `pyproject.toml` file.

Standardisation of installing and testing the python package is handled through tox.
Tox commands include:

```bash
# Run all standard tox actions
tox
# Run linting only
tox -e style
# Run tests only
tox -e test
```

## Dependency management

Dependencies are managed in the requirements.txt, requirements_test.txt and debian.txt file.

The requirements files are the python package dependencies for normal use and specific ones for tests
(e.g pytest, black, flake8 are test only dependencies).

The debian.txt file manages the debian dependencies that need to be installed on development systems and docker images.

Sometimes the debian.txt file is insufficient and in this case the Dockerfile may need to be modified directly to
install complex dependencies.
