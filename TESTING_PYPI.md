# PyPI Local Testing Guide

## Simple Testing Workflow

This guide helps you test the PyPI installation locally before pushing to production.

### Prerequisites

1. **Your dev environment**: `~/repos/pipulate` (working development)
2. **Nix already installed**: Will be reused for PyPI testing
3. **No port conflicts**: Stop dev version before testing

## Quick Test Cycle

### 1. Prepare for Testing
```bash
# Stop your dev version first (if running)
cd ~/repos/pipulate
# Press Ctrl+C in your dev terminal to stop server

# Verify it's stopped
curl -s http://localhost:5001 || echo "✅ Port 5001 free for testing"
```

### 2. Install PyPI Package (Local)
```bash
# Build and install locally
cd ~/repos/pipulate
pip install -e .

# Test installation
pipulate install testpipe
```

### 3. Run Test Installation
```bash
# This should work without conflicts
pipulate run testpipe

# Verify it starts at http://localhost:5001
# JupyterLab should auto-open at http://localhost:8888
```

### 4. Clean Up for Next Test
```bash
# Stop the test version (Ctrl+C)

# Uninstall everything
pipulate uninstall testpipe
pip uninstall pipulate

# Ready for next test cycle
```

## Test Scenarios

### Test 1: Fresh Install
```bash
pip install -e .
pipulate install fresh1
pipulate run fresh1
# Verify: Both ports work, servers start
pipulate uninstall fresh1
pip uninstall pipulate
```

### Test 2: Custom Name
```bash
pip install -e .
pipulate install mybotify
pipulate run mybotify
# Verify: Creates ~/mybotify directory
pipulate uninstall mybotify  
pip uninstall pipulate
```

### Test 3: Nix Reuse
```bash
# Nix should already be installed
pip install -e .
pipulate install nixtest
# Should skip Nix installation
pipulate run nixtest
pipulate uninstall nixtest
pip uninstall pipulate
```

## Important Notes

### Port Management
- **Simple approach**: Stop dev version manually before testing
- **No code changes**: Ports remain 5001 (server) and 8888 (JupyterLab)
- **Manual verification**: Check ports are free before starting test

### Directory Structure
```
~/repos/pipulate/          # Your development environment (don't touch)
~/testpipe/                 # PyPI test installation (disposable)
~/mybotify/                 # Custom name test (disposable)
~/.nix-profile/             # Nix (reused, never touched)
```

### What Gets Cleaned Up
✅ **Uninstalled**: PyPI package (`pip uninstall pipulate`)  
✅ **Removed**: Test directories (`pipulate uninstall testname`)  
✅ **Preserved**: Nix installation (reused for future tests)  
✅ **Untouched**: Your dev environment (`~/repos/pipulate`)

### Troubleshooting

**Port conflicts:**
```bash
# Check what's using ports
lsof -i :5001
lsof -i :8888

# Stop dev server if still running
cd ~/repos/pipulate
# Ctrl+C in dev terminal
```

**Nix issues:**
```bash
# Verify Nix works
nix --version

# If broken, reinstall
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

**Clean slate:**
```bash
# Nuclear option: Remove all test directories
rm -rf ~/testpipe ~/mybotify ~/fresh1
pip uninstall pipulate
```

## Ready for PyPI

Once this local testing works reliably:

1. **Version bump**: Update `__version__` in `__init__.py`
2. **Sync versions**: Run `python version_sync.py`  
3. **Build package**: `python -m build`
4. **Upload to PyPI**: `twine upload dist/*`

**The goal**: `pip install pipulate` works exactly like your local testing. 