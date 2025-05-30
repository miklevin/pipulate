#!/usr/bin/env python3
"""
swap_workflow_step.py - Replace placeholder workflow steps with developed logic

This script replaces a placeholder step (created by splice_workflow_step.py) with 
developed step logic from a source workflow file. It maintains the deterministic,
marker-based approach of other Pipulate helper scripts.

Usage:
    python swap_workflow_step.py TARGET_FILE TARGET_STEP_ID SOURCE_FILE SOURCE_BUNDLE_ID [--force]

Example:
    python swap_workflow_step.py plugins/035_kungfu_workflow.py step_01 plugins/500_hello_workflow.py step_01

The script:
1. Extracts the source step bundle using START_STEP_BUNDLE/END_STEP_BUNDLE markers
2. Renames all occurrences of source step ID to target step ID  
3. Replaces the target placeholder using START_SWAPPABLE_STEP/END_SWAPPABLE_STEP markers
4. Reports potential global dependencies that may need manual attention
"""

import argparse
import sys
import re
from pathlib import Path
from typing import Optional, Tuple, List


def find_pipulate_root():
    """Find the Pipulate project root directory by looking for server.py"""
    current_path = Path.cwd()
    
    # First try current directory and parents
    for path in [current_path] + list(current_path.parents):
        if (path / "server.py").exists():
            return path
    
    # If not found, try common locations relative to script location
    script_dir = Path(__file__).parent
    for candidate in [script_dir.parent, script_dir.parent.parent]:
        if (candidate / "server.py").exists():
            return candidate
    
    raise FileNotFoundError("Could not find Pipulate root directory (looking for server.py)")


def extract_step_bundle(content: str, bundle_id: str) -> Optional[str]:
    """Extract step bundle content between START_STEP_BUNDLE and END_STEP_BUNDLE markers"""
    start_marker = f"# --- START_STEP_BUNDLE: {bundle_id} ---"
    end_marker = f"# --- END_STEP_BUNDLE: {bundle_id} ---"
    
    lines = content.split('\n')
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if line.strip() == start_marker:
            start_idx = i
        elif line.strip() == end_marker and start_idx is not None:
            end_idx = i
            break
    
    if start_idx is None or end_idx is None:
        return None
    
    # Extract the content between markers (excluding the markers themselves)
    bundle_lines = lines[start_idx + 1:end_idx]
    return '\n'.join(bundle_lines)


def find_swappable_step_boundaries(content: str, step_id: str) -> Optional[Tuple[int, int]]:
    """Find the line boundaries of a swappable step block"""
    start_marker = f"# --- START_SWAPPABLE_STEP: {step_id} ---"
    end_marker = f"# --- END_SWAPPABLE_STEP: {step_id} ---"
    
    lines = content.split('\n')
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if line.strip() == start_marker:
            start_idx = i
        elif line.strip() == end_marker and start_idx is not None:
            end_idx = i
            break
    
    if start_idx is None or end_idx is None:
        return None
    
    return start_idx, end_idx


def identify_potential_dependencies(bundle_content: str) -> List[str]:
    """Identify potential global dependencies in the bundle content"""
    dependencies = set()
    
    # Look for self.UPPER_CASE patterns (class constants)
    self_constants = re.findall(r'self\.([A-Z][A-Z_]*)', bundle_content)
    dependencies.update(f"self.{const}" for const in self_constants)
    
    # Look for standalone UPPER_CASE patterns that might be module-level constants
    # Exclude common builtins and avoid false positives in strings/comments
    module_constants = re.findall(r'\b([A-Z][A-Z_]{2,})\b', bundle_content)
    # Filter out common false positives
    excluded = {'GET', 'POST', 'PUT', 'DELETE', 'HTTP', 'HTML', 'CSS', 'JS', 'API', 'URL', 'ID', 'UUID'}
    dependencies.update(const for const in module_constants if const not in excluded)
    
    return sorted(list(dependencies))


def transform_bundle_content(bundle_content: str, source_step_id: str, target_step_id: str) -> str:
    """Transform bundle content by renaming step IDs and maintaining markers"""
    # Replace whole-word occurrences of the source step ID with target step ID
    # This will rename method definitions and references
    pattern = r'\b' + re.escape(source_step_id) + r'\b'
    transformed = re.sub(pattern, target_step_id, bundle_content)
    
    # Wrap with new step bundle markers (preserving the swapped content as a bundle)
    wrapped = f"# --- START_STEP_BUNDLE: {target_step_id} ---\n{transformed}\n# --- END_STEP_BUNDLE: {target_step_id} ---"
    
    return wrapped


def main():
    parser = argparse.ArgumentParser(description='Swap workflow step placeholder with developed logic')
    parser.add_argument('target_file', help='Target workflow file path')
    parser.add_argument('target_step_id', help='Target step ID to replace (e.g., step_01)')
    parser.add_argument('source_file', help='Source workflow file path')
    parser.add_argument('source_bundle_id', help='Source bundle ID to extract (e.g., step_01)')
    parser.add_argument('--force', action='store_true', help='Force overwrite without confirmation')
    
    args = parser.parse_args()
    
    try:
        pipulate_root = find_pipulate_root()
        print(f"Pipulate root: {pipulate_root}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Resolve file paths
    target_path = Path(args.target_file)
    source_path = Path(args.source_file)
    
    if not target_path.is_absolute():
        target_path = pipulate_root / target_path
    if not source_path.is_absolute():
        source_path = pipulate_root / source_path
    
    # Validate files exist
    if not target_path.exists():
        print(f"Error: Target file does not exist: {target_path}")
        sys.exit(1)
    
    if not source_path.exists():
        print(f"Error: Source file does not exist: {source_path}")
        sys.exit(1)
    
    # Read source file and extract bundle
    print(f"Reading source file: {source_path}")
    source_content = source_path.read_text()
    
    bundle_content = extract_step_bundle(source_content, args.source_bundle_id)
    if bundle_content is None:
        print(f"Error: Could not find step bundle '{args.source_bundle_id}' in source file")
        print(f"Looking for markers:")
        print(f"  # --- START_STEP_BUNDLE: {args.source_bundle_id} ---")
        print(f"  # --- END_STEP_BUNDLE: {args.source_bundle_id} ---")
        sys.exit(1)
    
    print(f"✓ Extracted step bundle '{args.source_bundle_id}' ({len(bundle_content.splitlines())} lines)")
    
    # Identify potential dependencies
    dependencies = identify_potential_dependencies(bundle_content)
    if dependencies:
        print(f"⚠️  Potential dependencies detected: {', '.join(dependencies)}")
        print("   Make sure these are defined in the target workflow")
    
    # Transform bundle content
    transformed_bundle = transform_bundle_content(bundle_content, args.source_bundle_id, args.target_step_id)
    
    # Read target file and find swappable step
    print(f"Reading target file: {target_path}")
    target_content = target_path.read_text()
    
    boundaries = find_swappable_step_boundaries(target_content, args.target_step_id)
    if boundaries is None:
        print(f"Error: Could not find swappable step '{args.target_step_id}' in target file")
        print(f"Looking for markers:")
        print(f"  # --- START_SWAPPABLE_STEP: {args.target_step_id} ---")
        print(f"  # --- END_SWAPPABLE_STEP: {args.target_step_id} ---")
        sys.exit(1)
    
    start_line, end_line = boundaries
    print(f"✓ Found swappable step '{args.target_step_id}' (lines {start_line + 1}-{end_line + 1})")
    
    # Replace the swappable step block
    target_lines = target_content.split('\n')
    
    # Replace entire block (including markers) with transformed bundle
    new_lines = (
        target_lines[:start_line] + 
        transformed_bundle.split('\n') + 
        target_lines[end_line + 1:]
    )
    
    new_content = '\n'.join(new_lines)
    
    # Write the modified content
    if not args.force:
        response = input(f"Replace step '{args.target_step_id}' in {target_path}? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled")
            sys.exit(0)
    
    target_path.write_text(new_content)
    print(f"✅ Successfully swapped step '{args.target_step_id}' in {target_path}")
    
    if dependencies:
        print("\n🔍 Dependency Check:")
        print("   The following potential dependencies were detected in the swapped code:")
        for dep in dependencies:
            print(f"   • {dep}")
        print("   Please ensure these are defined in your target workflow class.")


if __name__ == '__main__':
    main() 