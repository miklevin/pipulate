"""
Pipulate: Local-First AI SEO Software & Digital Workshop

Your data. Your AI. Your machine. Your control.

This package provides the `pipulate` command for discovering and installing
the full Pipulate environment via PyPI, while the actual application runs
in a Nix-managed environment for complete reproducibility.

Usage:
    pip install pipulate
    pipulate
"""

# Pipulate - Local-First AI SEO Software
# Copyright (C) 2025 Mike Levin
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# SINGLE SOURCE OF TRUTH FOR VERSION
# This version number is used across all components:
# - pyproject.toml
# - flake.nix 
# - install.sh
# - server.py startup banners
# Update this version and run: python -c "from pipulate.version_sync import sync_all_versions; sync_all_versions()"
__version__ = "1.0.0"
__author__ = "Mike Levin"
__email__ = "pipulate@gmail.com"
__description__ = "Local First AI SEO Software" 
