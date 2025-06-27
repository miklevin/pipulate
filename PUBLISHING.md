# Pipulate PyPI Publishing Guide

## Overview

This guide covers publishing the lightweight `pipulate` PyPI package that serves as the discovery gateway for the full Pipulate installation.

## Prerequisites

Install the required build and publishing tools:

```bash
pip install build twine
```

## Publishing Workflow

### Step 1: Build the Package

```bash
# From the pipulate repository root
python -m build
```

This creates:
- `dist/pipulate-0.4.0.tar.gz` (source distribution)
- `dist/pipulate-0.4.0-py3-none-any.whl` (wheel distribution)

### Step 2: Test on TestPyPI (Recommended)

First, create an account on [TestPyPI](https://test.pypi.org/).

Upload to TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
```

Test the installation:
```bash
# In a clean environment
python -m venv test_env
source test_env/bin/activate  # or `test_env\Scripts\activate` on Windows
pip install --index-url https://test.pypi.org/simple/ --no-deps pipulate
pipulate --help
```

### Step 3: Publish to Production PyPI

Create an account on [PyPI.org](https://pypi.org/).

Upload to production PyPI:
```bash
python -m twine upload dist/*
```

## Post-Publication

After publishing, users can discover and install Pipulate via:

```bash
pip install pipulate
pipulate
```

## Version Management

- Update version in `pyproject.toml` and `__init__.py`
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Create git tags for releases: `git tag v0.4.0`

## Security Notes

- Use PyPI API tokens instead of passwords when possible
- Store credentials securely (consider `twine` keyring integration)
- Never commit API tokens to version control

## Package Structure

The published package contains only:
- `pipulate/cli.py` - The installation gateway
- `pipulate/__init__.py` - Package metadata  
- `pyproject.toml` - Build and dependency configuration

The actual Pipulate application is downloaded separately via the existing `install.sh` script. 