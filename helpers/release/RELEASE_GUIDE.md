# Pipulate Release Guide

This document outlines the comprehensive process for releasing new versions of Pipulate, including the enhanced 3-phase release pipeline with automatic version synchronization, documentation updates, and AI-assisted commits.

## 🚀 Quick Release (TL;DR)

For experienced users who just want to get things done:

```bash
# 1. Update version in pipulate/__init__.py
# 2. Run the enhanced release pipeline:
python helpers/release/publish.py --release --ai-commit

# That's it! The script handles version sync, docs, AI commit, and PyPI publishing.
```

## 📋 The Enhanced 3-Phase Release Pipeline

The new `publish.py` script provides a comprehensive release orchestrator with three phases:

### 🔧 Phase 1: Preparation
- **Version Synchronization**: Automatically syncs versions across all files
- **Documentation Sync**: Updates ASCII art and documentation across the ecosystem
- **Pre-flight Validation**: Ensures everything is ready for release

### 📝 Phase 2: Git Operations  
- **AI-Generated Commits**: Optional intelligent commit message generation via local LLM
- **Git Management**: Staging, committing, and pushing changes
- **Change Detection**: Smart handling of no-change scenarios

### 📦 Phase 3: PyPI Publishing
- **Package Building**: Clean builds with artifact cleanup
- **PyPI Upload**: Direct publishing to the Python Package Index
- **Verification**: Package URL output for immediate verification

## 🎯 Step-by-Step Release Process

### 1. Pre-Release Checks

- [ ] Ensure `main` branch is up-to-date: `git pull origin main`
- [ ] Run local tests to confirm stability
- [ ] Ensure all desired changes are committed and merged

### 2. Update Version Number

**Single Source of Truth**: All versions come from `pipulate/__init__.py`

```python
# Edit pipulate/__init__.py
__version__ = "1.2.0"  # Update according to Semantic Versioning
```

### 3. Choose Your Release Method

#### Option A: Full Automated Release (Recommended)
```bash
# AI analyzes your changes and creates intelligent commit message
python helpers/release/publish.py --release --ai-commit
```

#### Option B: Custom Commit Message
```bash
# Provide your own commit message
python helpers/release/publish.py --release -m "feat: Add revolutionary new feature"
```

#### Option C: Granular Control
```bash
# Skip individual steps if needed
python helpers/release/publish.py --release --skip-docs-sync -m "hotfix: Critical bug resolution"

# Force republish without changes (useful for metadata fixes)
python helpers/release/publish.py --release --force -m "chore: Update package metadata"
```

## 🔄 The Version Synchronization System

### Single Source of Truth Architecture

```
pipulate/__init__.py (__version__)
         │
         ├── version_sync.py (automatic)
         │
         ├─→ pyproject.toml
         ├─→ flake.nix  
         ├─→ ../Pipulate.com/assets/installer/install.sh
         └─→ Runtime displays
```

### What Gets Synchronized

1. **pyproject.toml**: Python package version
2. **flake.nix**: Nix environment version (preserves subtitle)
3. **assets/installer/install.sh**: Installer script version
4. **Runtime displays**: Server startup banners and UI

### Manual Version Sync

If you need to run version sync independently:

```bash
python helpers/release/version_sync.py
```

## 📚 Documentation Synchronization

The enhanced pipeline includes automatic ASCII art and documentation synchronization:

### What Gets Updated

- ASCII art blocks across all documentation files
- Cross-references and links
- Consistency checks and validation
- Strategic placement of unused content

### Manual Documentation Sync

```bash
python helpers/docs_sync/sync_ascii_art.py
```

## 🤖 AI-Assisted Commit Messages

The system can generate intelligent commit messages using your local LLM:

### Requirements
- Ollama running locally: `ollama serve`
- Model available: `ollama pull gemma:2b`

### How It Works
1. Analyzes `git diff --staged` 
2. Sends to local LLM for conventional commit generation
3. Returns properly formatted commit message
4. Follows conventional commit standards (feat, fix, docs, etc.)

### Manual AI Commit
```bash
# Generate AI commit without full release
python helpers/release/ai_commit.py
```

## 🛠️ Advanced Usage

### Available Flags

| Flag | Purpose |
|------|---------|
| `--release` | Perform PyPI publishing |
| `--ai-commit` | Use AI for commit message generation |
| `-m MESSAGE` | Custom commit message (overrides AI) |
| `--force` | Proceed even with no git changes |
| `--skip-version-sync` | Skip version synchronization step |
| `--skip-docs-sync` | Skip documentation synchronization |

### Example Workflows

```bash
# Documentation-only release
python helpers/release/publish.py --skip-version-sync --ai-commit

# Emergency hotfix release  
python helpers/release/publish.py --release --force -m "hotfix: Critical security patch"

# Test release pipeline without PyPI
python helpers/release/publish.py --ai-commit

# Full release with all features
python helpers/release/publish.py --release --ai-commit
```

## 🔍 Verification & Testing

### Post-Release Verification

1. **Check PyPI**: Visit `https://pypi.org/project/pipulate/{version}/`
2. **Test Installation**: 
   ```bash
   pipx install pipulate --force
   pipulate install
   ```
3. **Verify Versions**: All components should show consistent version numbers

### Troubleshooting

#### Build Errors
- Ensure you're in the pipulate root directory
- Check `pyproject.toml` validity
- Verify all dependencies are correctly listed

#### Upload Errors  
- Confirm PyPI credentials (use API tokens)
- Check version doesn't already exist
- Verify build artifacts in `dist/`

#### Version Sync Issues
- Run `python helpers/release/version_sync.py` manually
- Check file permissions
- Verify `__init__.py` version format

#### AI Commit Issues
- Ensure Ollama is running: `ollama serve`
- Check model availability: `ollama list`
- Verify staged changes exist: `git status`

## 📊 Before/After: Version Consistency

### Before (Inconsistent)
```
Install Script:  v1.1.2
Nix Flake:      v1.0.8 (JupyterLab Python Version Fix)  
PyPI Package:   v0.4.0
Server Display: v1.0.8 (JupyterLab Python Version Fix)
```

### After (Consistent)
```
Install Script:  v1.2.0
Nix Flake:      v1.2.0 (Enhanced Release Pipeline)
PyPI Package:   v1.2.0
Server Display: v1.2.0 (Nix Environment)
```

## 🏆 Release Best Practices

1. **Always use the enhanced pipeline** for consistency
2. **Test AI commits** before major releases
3. **Use semantic versioning** (MAJOR.MINOR.PATCH)
4. **Verify installations** on clean systems
5. **Keep release notes** updated
6. **Monitor PyPI downloads** for adoption tracking

## 🆘 Emergency Recovery

If something goes wrong during release:

```bash
# Check current state
git status
python -c "from pipulate import __version__; print(__version__)"

# Reset to last known good state
git reset --hard HEAD~1
git push --force-with-lease

# Verify all version references
grep -r "version.*=" --include="*.py" --include="*.toml" --include="*.sh" --include="*.nix" .
```

## 📝 Release Checklist

- [ ] Update `pipulate/__init__.py` version
- [ ] Run enhanced release pipeline
- [ ] Verify PyPI upload success
- [ ] Test installation on clean system
- [ ] Update release notes
- [ ] Announce release on relevant channels

**The enhanced release pipeline eliminates manual errors and ensures perfect consistency across the entire Pipulate ecosystem!** 