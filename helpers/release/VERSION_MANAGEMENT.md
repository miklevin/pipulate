# Pipulate Version Management System

## Single Source of Truth

**All version numbers in Pipulate come from one source: `pipulate/__init__.py`**

```python
__version__ = "1.1.3"
```

## Problem Solved

Previously, version numbers were scattered across multiple files:
- ❌ `pyproject.toml`: version = "0.4.0"
- ❌ `flake.nix`: version = "1.0.8 (JupyterLab Python Version Fix)"
- ❌ `install.sh`: VERSION="1.1.2"
- ❌ Multiple inconsistent versions displayed during installation

This caused confusion and inconsistent version reporting during installation and startup.

## Solution

### 1. Single Source of Truth
- **Source**: `pipulate/__init__.py` → `__version__ = "1.1.3"`
- **Files Updated**: All version references now sync from this source

### 2. Automatic Synchronization
Run the sync script to update all files:

```bash
# From pipulate directory
python version_sync.py

# Or programmatically  
python -c "from pipulate.version_sync import sync_all_versions; sync_all_versions()"
```

### 3. Files Automatically Updated
- `pyproject.toml` → Python package version
- `flake.nix` → Nix environment version (preserves subtitle)
- `Pipulate.com/install.sh` → Installer version
- Server startup banners → Runtime version display

## When to Update Version

1. **Edit the source**: Update `__version__` in `pipulate/__init__.py`
2. **Run the sync**: Execute `python version_sync.py`
3. **Commit changes**: All files will be consistently updated

## Version Display

During installation and startup, users will see consistent version numbers:

- **Install script**: `Pipulate Installer v1.1.3`
- **Nix environment**: `Version 1.1.3 (Nix Environment)`
- **Server startup**: ASCII art with unified version number
- **Package info**: All Python package metadata matches

## Developer Notes

- The `get_nix_version()` function now reads from `__version__` instead of parsing `flake.nix`
- Environment context (Nix/non-Nix) is preserved in the version display
- Flake version subtitle is preserved during sync (e.g., "Single Source Version Fix")
- Version sync script is idempotent - safe to run multiple times

## Before/After

### Before (Inconsistent)
```
Install:     v1.1.2
Flake:       v1.0.8 (JupyterLab Python Version Fix)  
PyPI:        v0.4.0
Server:      v1.0.8 (JupyterLab Python Version Fix)
```

### After (Consistent)
```
Install:     v1.1.3
Flake:       v1.1.3 (Single Source Version Fix)
PyPI:        v1.1.3  
Server:      v1.1.3 (Nix Environment)
```

## Emergency Recovery

If the sync script fails or you need to manually verify versions:

```bash
# Check current version source
grep "__version__" pipulate/__init__.py

# Check all version references
grep -r "version.*=" --include="*.py" --include="*.toml" --include="*.sh" --include="*.nix" .
```

This ensures **no more version confusion** during installation or development! 