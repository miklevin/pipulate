#!/usr/bin/env python3
"""
manage_class_attributes.py - Merge class-level attributes between workflow files

This script intelligently merges/replaces class-level constant dictionaries 
(e.g., UI_CONSTANTS, QUERY_TEMPLATES) from a source workflow file to a target 
workflow file using marker-based precision.

Usage:
    python manage_class_attributes.py TARGET_FILE SOURCE_FILE --attributes-to-merge ATTR1 ATTR2 [--force]

Example:
    python manage_class_attributes.py plugins/035_kungfu_workflow.py plugins/500_hello_workflow.py --attributes-to-merge UI_CONSTANTS

The script:
1. Extracts class attributes from source file using CLASS_ATTRIBUTES_BUNDLE markers
2. Merges/replaces specified attributes in target file's bundle section
3. Preserves protected attributes (APP_NAME, DISPLAY_NAME, etc.) outside markers
4. Maintains proper indentation and formatting
"""

import argparse
import sys
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple


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


def extract_class_attributes_bundle(content: str) -> Optional[str]:
    """Extract content between START_CLASS_ATTRIBUTES_BUNDLE and END_CLASS_ATTRIBUTES_BUNDLE markers"""
    start_marker = "# --- START_CLASS_ATTRIBUTES_BUNDLE ---"
    end_marker = "# --- END_CLASS_ATTRIBUTES_BUNDLE ---"
    
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


def find_class_attributes_bundle_boundaries(content: str) -> Optional[Tuple[int, int]]:
    """Find the line boundaries of the class attributes bundle block"""
    start_marker = "# --- START_CLASS_ATTRIBUTES_BUNDLE ---"
    end_marker = "# --- END_CLASS_ATTRIBUTES_BUNDLE ---"
    
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


def extract_attribute_definition(content: str, attribute_name: str) -> Optional[str]:
    """
    Extract a specific attribute definition from content.
    
    Handles multi-line dictionary definitions like:
    UI_CONSTANTS = {
        'key': 'value',
        'nested': {
            'inner': 'value'
        }
    }
    """
    # Pattern to match attribute assignment with proper boundary detection
    pattern = rf"^(\s*{re.escape(attribute_name)}\s*=\s*{{\s*)$"
    lines = content.split('\n')
    
    start_line = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start_line = i
            break
    
    if start_line is None:
        return None
    
    # Find the matching closing brace
    brace_count = 0
    end_line = None
    
    for i in range(start_line, len(lines)):
        line = lines[i]
        
        # Count opening and closing braces
        for char in line:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                
                # When we reach 0, we've found the end
                if brace_count == 0:
                    end_line = i
                    break
        
        if end_line is not None:
            break
    
    if end_line is None:
        # Fallback: look for a line that starts with } and has the right indentation
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip() == '}' or re.match(r'^\s*}\s*$', lines[i]):
                end_line = i
                break
    
    if end_line is None:
        return None
    
    # Extract the complete attribute definition
    attribute_lines = lines[start_line:end_line + 1]
    return '\n'.join(attribute_lines)


def merge_attributes_into_bundle(target_bundle: str, source_bundle: str, attributes_to_merge: List[str]) -> str:
    """
    Merge specified attributes from source bundle into target bundle.
    
    For each attribute:
    - If it exists in target: replace it entirely
    - If it doesn't exist in target: append it
    """
    if not source_bundle.strip():
        return target_bundle
    
    # Start with target bundle content
    result_lines = target_bundle.split('\n') if target_bundle else []
    
    for attr_name in attributes_to_merge:
        source_attr = extract_attribute_definition(source_bundle, attr_name)
        
        if not source_attr:
            print(f"Warning: Attribute '{attr_name}' not found in source bundle")
            continue
        
        # Check if attribute exists in target
        target_attr = extract_attribute_definition(target_bundle, attr_name)
        
        if target_attr:
            # Replace existing attribute
            target_lines = target_bundle.split('\n')
            
            # Find the attribute in target lines and replace it
            pattern = rf"^(\s*{re.escape(attr_name)}\s*=\s*{{\s*)$"
            start_idx = None
            end_idx = None
            
            for i, line in enumerate(target_lines):
                if re.match(pattern, line):
                    start_idx = i
                    break
            
            if start_idx is not None:
                # Find the end of this attribute definition
                brace_count = 0
                for i in range(start_idx, len(target_lines)):
                    line = target_lines[i]
                    for char in line:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break
                    if end_idx is not None:
                        break
                
                if end_idx is not None:
                    # Replace the target attribute with source attribute
                    result_lines = (
                        target_lines[:start_idx] + 
                        source_attr.split('\n') + 
                        target_lines[end_idx + 1:]
                    )
                    target_bundle = '\n'.join(result_lines)
                    print(f"✓ Replaced attribute '{attr_name}' in target")
                else:
                    print(f"Warning: Could not find end of attribute '{attr_name}' in target")
            else:
                print(f"Warning: Could not find attribute '{attr_name}' in target for replacement")
        else:
            # Append new attribute to target
            if target_bundle.strip():
                result_lines.append('')  # Add blank line before new attribute
            result_lines.extend(source_attr.split('\n'))
            print(f"✓ Added new attribute '{attr_name}' to target")
    
    return '\n'.join(result_lines)


def detect_bundle_indentation(content: str) -> str:
    """Detect the indentation level used within the class attributes bundle"""
    lines = content.split('\n')
    
    for line in lines:
        stripped = line.lstrip()
        if stripped and not stripped.startswith('#'):
            # Found a non-comment line, calculate indentation
            return line[:len(line) - len(stripped)]
    
    # Default to standard class member indentation
    return "    "


def main():
    parser = argparse.ArgumentParser(description='Merge class-level attributes between workflow files')
    parser.add_argument('target_file', help='Target workflow file path')
    parser.add_argument('source_file', help='Source workflow file path') 
    parser.add_argument('--attributes-to-merge', nargs='+', required=True,
                       help='Space-separated list of attribute names to merge (e.g., UI_CONSTANTS QUERY_TEMPLATES)')
    parser.add_argument('--force', action='store_true', help='Force changes without confirmation')
    
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
    
    # Read files
    print(f"Reading source file: {source_path}")
    source_content = source_path.read_text()
    
    print(f"Reading target file: {target_path}")
    target_content = target_path.read_text()
    
    # Extract source bundle
    source_bundle = extract_class_attributes_bundle(source_content)
    if source_bundle is None:
        print(f"Error: Could not find CLASS_ATTRIBUTES_BUNDLE markers in source file")
        print(f"Looking for markers:")
        print(f"  # --- START_CLASS_ATTRIBUTES_BUNDLE ---")
        print(f"  # --- END_CLASS_ATTRIBUTES_BUNDLE ---")
        sys.exit(1)
    
    print(f"✓ Extracted class attributes bundle from source ({len(source_bundle.splitlines())} lines)")
    
    # Find target bundle boundaries
    target_boundaries = find_class_attributes_bundle_boundaries(target_content)
    if target_boundaries is None:
        print(f"Error: Could not find CLASS_ATTRIBUTES_BUNDLE markers in target file")
        print(f"Looking for markers:")
        print(f"  # --- START_CLASS_ATTRIBUTES_BUNDLE ---")
        print(f"  # --- END_CLASS_ATTRIBUTES_BUNDLE ---")
        sys.exit(1)
    
    start_line, end_line = target_boundaries
    print(f"✓ Found target bundle markers (lines {start_line + 1}-{end_line + 1})")
    
    # Extract target bundle content
    target_bundle = extract_class_attributes_bundle(target_content)
    if target_bundle is None:
        target_bundle = ""
    
    # Merge attributes
    print(f"Merging attributes: {', '.join(args.attributes_to_merge)}")
    merged_bundle = merge_attributes_into_bundle(target_bundle, source_bundle, args.attributes_to_merge)
    
    # Replace target bundle content
    target_lines = target_content.split('\n')
    new_lines = (
        target_lines[:start_line + 1] +  # Include start marker
        merged_bundle.split('\n') +     # New bundle content
        target_lines[end_line:]         # Include end marker and rest
    )
    
    new_content = '\n'.join(new_lines)
    
    # Show summary of changes
    if merged_bundle != target_bundle:
        print(f"\n📋 Summary of Changes:")
        print(f"   Target file: {target_path}")
        for attr_name in args.attributes_to_merge:
            if extract_attribute_definition(source_bundle, attr_name):
                action = "Replaced" if extract_attribute_definition(target_bundle, attr_name) else "Added"
                print(f"   • {action} attribute: {attr_name}")
    else:
        print("No changes needed - target already has current attributes")
        sys.exit(0)
    
    # Write changes
    if not args.force:
        response = input(f"\nApply changes to {target_path}? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled")
            sys.exit(0)
    
    target_path.write_text(new_content)
    print(f"✅ Successfully updated class attributes in {target_path}")


if __name__ == '__main__':
    main() 