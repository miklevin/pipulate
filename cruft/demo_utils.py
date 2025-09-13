"""
demo_utils.py - Shared utility functions for demo scripts

This module contains common utility functions used across multiple 
demo scripts to eliminate code duplication.
"""

from pathlib import Path


def get_file_size(filename):
    """Get file size in characters"""
    try:
        return Path(filename).stat().st_size
    except FileNotFoundError:
        return 0


def estimate_tokens(char_count):
    """Rough estimate: 1 token ≈ 4 characters for code"""
    return char_count // 4 