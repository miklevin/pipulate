# Pipulate Publishing Guide

This document outlines the step-by-step process for publishing a new version of the `pipulate` package to PyPI.

## 1. Pre-flight Checks

- [ ] Ensure `main` branch is up-to-date (`git pull origin main`).
- [ ] Run local tests to confirm the application is stable (`pytest` or manual tests from `TESTING_PYPI.md`).
- [ ] Ensure all desired changes have been merged into `main`.

## 2. Update Version Number

This is the most critical step. The version number is managed from a single source of truth.

1. **Edit the source:** Open `pipulate/__init__.py`.
2. **Increment the version:** Change the `__version__` string according to [Semantic Versioning](https://semver.org/) (e.g., `1.1.3` -> `1.2.0`).

   ```python
   # in pipulate/__init__.py
   __version__ = "1.2.0"
   ```

## 3. Synchronize Versions

Run the synchronization script to propagate the new version number to all necessary files.

```bash
python version_sync.py
```

This will automatically update:
- `pyproject.toml`
- `flake.nix`
- `Pipulate.com/install.sh`

## 4. Commit Version Bump

Commit the version update to your git repository.

```bash
git add pipulate/__init__.py pyproject.toml flake.nix [Pipulate.com/install.sh]
git commit -m "chore(release): Bump version to 1.2.0"
git push origin main
```

## 5. Build the Package

Make sure your local repository is clean, then build the source distribution and wheel.

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Install/update build tools
python -m pip install --upgrade build twine

# Build the package
python -m build
```

This will create a `dist` directory containing the `.whl` and `.tar.gz` files for the new version.

## 6. Upload to TestPyPI (Recommended)

Always test the upload and installation process on TestPyPI first.

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*
```

You will be prompted for your TestPyPI username and password. Use an [API token](https://test.pypi.org/manage/account/token/) for better security.

### Verify on TestPyPI

In a new, clean environment, test the installation:

```bash
python -m venv testpypi_env
source testpypi_env/bin/activate
pip install --index-url https://test.pypi.org/simple/ --no-deps pipulate
pipulate --help
# If it works, you're ready for production
deactivate
rm -rf testpypi_env/
```

## 7. Upload to Production PyPI

Once verified, upload to the official PyPI repository.

```bash
# Upload to PyPI
python -m twine upload dist/*
```

Enter your production PyPI username and password (again, an API token is highly recommended).

---

**Congratulations, you've just released a new version of Pipulate!**

## Version Management System Summary

Our single source of truth system ensures consistency:

1. **Source**: `pipulate/__init__.py.__version__`
2. **Sync Script**: `python version_sync.py` 
3. **Files Updated**: pyproject.toml, flake.nix, install.sh
4. **Result**: Perfect version consistency across all components

This eliminates the confusion and bugs that come from scattered version numbers, ensuring users always see the correct, matching version during installation and runtime.

## Troubleshooting

### Build Errors
- Ensure you're in the correct directory (`pipulate/`)
- Check that `pyproject.toml` is valid
- Verify all dependencies are listed correctly

### Upload Errors
- Confirm you have valid PyPI credentials
- Check that the version number doesn't already exist on PyPI
- Ensure you're uploading the correct dist files

### Version Sync Issues
- Verify `version_sync.py` runs without errors
- Check that all target files exist and are writable
- Confirm the version format matches the expected pattern

Remember: The version synchronization system is designed to be foolproof. As long as you update `__init__.py` and run the sync script, everything should work perfectly! 