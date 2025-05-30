#!/usr/bin/env python3
"""
swap_workflow_step.py - Replace placeholder workflow steps with developed logic

This script replaces a placeholder step (created by splice_workflow_step.py) with 
developed step logic from a source workflow file. It maintains the deterministic,
marker-based approach of other Pipulate helper scripts.

Enhanced to handle both:
1. Step method bundles (GET/POST handlers)  
2. Step definitions (Step namedtuple in self.steps list)

Usage:
    python swap_workflow_step.py TARGET_FILE TARGET_STEP_ID SOURCE_FILE SOURCE_BUNDLE_ID [--force]

Example:
    python swap_workflow_step.py plugins/035_kungfu_workflow.py step_01 plugins/500_hello_workflow.py step_01

The script:
1. Extracts the source step bundle using START_STEP_BUNDLE/END_STEP_BUNDLE markers
2. Extracts the source Step definition from self.steps list
3. Renames all occurrences of source step ID to target step ID in both  
4. Replaces the target placeholder using START_SWAPPABLE_STEP/END_SWAPPABLE_STEP markers
5. Replaces the target Step definition in self.steps list
6. Reports potential global dependencies that may need manual attention
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


def extract_step_definition(content: str, step_id: str) -> Optional[str]:
    """Extract Step definition for given step_id from self.steps list"""
    
    lines = content.split('\n')
    
    # Pattern 1: Direct assignment `self.steps = [...]`
    steps_pattern = r'self\.steps\s*=\s*\['
    steps_start_line = None
    for i, line in enumerate(lines):
        if re.search(steps_pattern, line):
            steps_start_line = i
            break
    
    # Pattern 2: Indirect assignment via variable
    if steps_start_line is None:
        # Look for `self.steps = variable_name`
        indirect_pattern = r'^\s*self\.steps\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:[;#]|$)'
        variable_name = None
        for line in lines:
            match = re.search(indirect_pattern, line, re.MULTILINE)
            if match:
                variable_name = match.group(1)
                break
        
        if variable_name:
            # Find `variable_name = [...]`
            var_pattern = rf'^\s*{re.escape(variable_name)}\s*=\s*\['
            for i, line in enumerate(lines):
                if re.search(var_pattern, line):
                    steps_start_line = i
                    break
    
    if steps_start_line is None:
        return None
    
    # Find the Step definition with matching id starting from steps_start_line
    i = steps_start_line
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a Step definition
        if re.search(r'Step\s*\(', line):
            # This could be our target step, let's check
            step_start_line = i
            paren_count = 0
            found_target_id = False
            step_lines = []
            
            # Scan from this line until we find the matching closing parenthesis
            for j in range(i, len(lines)):
                current_line = lines[j]
                step_lines.append(current_line)
                
                # Count parentheses, but ignore ones inside strings
                in_string = False
                quote_char = None
                k = 0
                while k < len(current_line):
                    char = current_line[k]
                    
                    # Handle string literals
                    if not in_string and char in ['"', "'"]:
                        in_string = True
                        quote_char = char
                    elif in_string and char == quote_char:
                        # Check if it's escaped
                        if k == 0 or current_line[k-1] != '\\':
                            in_string = False
                            quote_char = None
                    
                    # Count parentheses only when not in strings
                    elif not in_string:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                    
                    k += 1
                
                # Check if this line contains our target step_id
                step_id_pattern = rf'id\s*=\s*[\'\"]{re.escape(step_id)}[\'\"]'
                if re.search(step_id_pattern, current_line):
                    found_target_id = True
                
                # If we've closed all parentheses for this Step definition
                if paren_count == 0:
                    # If this was our target step, return it
                    if found_target_id:
                        return '\n'.join(step_lines)
                    else:
                        # This wasn't our target step, continue searching
                        i = j + 1
                        break
            else:
                # Reached end of file without closing parentheses
                break
        else:
            i += 1
    
    return None


def replace_step_definition_in_target(content: str, target_step_id: str, new_step_definition: str) -> Tuple[str, bool]:
    """Replace Step definition in target content and return (new_content, success)"""
    
    lines = content.split('\n')
    
    # Find the Step definition with target_step_id using improved logic
    step_start_line = None
    step_end_line = None
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a Step definition
        if re.search(r'Step\s*\(', line):
            # This could be our target step, let's check
            step_start_line = i
            paren_count = 0
            found_target_id = False
            
            # Scan from this line until we find the matching closing parenthesis
            for j in range(i, len(lines)):
                current_line = lines[j]
                
                # Count parentheses, but ignore ones inside strings
                in_string = False
                quote_char = None
                k = 0
                while k < len(current_line):
                    char = current_line[k]
                    
                    # Handle string literals
                    if not in_string and char in ['"', "'"]:
                        in_string = True
                        quote_char = char
                    elif in_string and char == quote_char:
                        # Check if it's escaped
                        if k == 0 or current_line[k-1] != '\\':
                            in_string = False
                            quote_char = None
                    
                    # Count parentheses only when not in strings
                    elif not in_string:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                    
                    k += 1
                
                # Check if this line contains our target step_id
                step_id_pattern = rf'id\s*=\s*[\'\"]{re.escape(target_step_id)}[\'\"]'
                if re.search(step_id_pattern, current_line):
                    found_target_id = True
                
                # If we've closed all parentheses for this Step definition
                if paren_count == 0:
                    step_end_line = j
                    break
            
            # If this was our target step, we're done
            if found_target_id and step_end_line is not None:
                break
            else:
                # This wasn't our target step, continue searching
                step_start_line = None
                step_end_line = None
                i = step_end_line + 1 if step_end_line is not None else i + 1
        else:
            i += 1
    
    if step_start_line is None or step_end_line is None:
        return content, False
    
    # Replace the target Step definition with the new one
    new_lines = (
        lines[:step_start_line] + 
        new_step_definition.split('\n') + 
        lines[step_end_line + 1:]
    )
    
    return '\n'.join(new_lines), True


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
    """Transform bundle content by renaming step IDs and maintaining proper method structure"""
    
    lines = bundle_content.split('\n')
    transformed_lines = []
    
    for line in lines:
        transformed_line = line
        
        # CRITICAL: Transform method definitions first (most specific patterns)
        # 1. Transform async def step_XX_submit( patterns
        if re.search(rf'async\s+def\s+{re.escape(source_step_id)}_submit\s*\(', line):
            transformed_line = re.sub(rf'\b{re.escape(source_step_id)}_submit\b', f'{target_step_id}_submit', line)
        
        # 2. Transform async def step_XX( patterns  
        elif re.search(rf'async\s+def\s+{re.escape(source_step_id)}\s*\(', line):
            transformed_line = re.sub(rf'\b{re.escape(source_step_id)}\b', target_step_id, line)
        
        # 3. Transform step_id variable assignments
        elif re.search(rf"step_id\s*=\s*['\"]?{re.escape(source_step_id)}['\"]?", line):
            transformed_line = re.sub(rf"(['\"]?){re.escape(source_step_id)}(['\"]?)", rf"\1{target_step_id}\2", line)
        
        # 4. Transform URL/route references with _submit
        elif f'/{source_step_id}_submit' in line:
            transformed_line = line.replace(f'/{source_step_id}_submit', f'/{target_step_id}_submit')
        
        # 5. Transform URL/route references without _submit
        elif f'/{source_step_id}' in line and '_submit' not in line:
            transformed_line = line.replace(f'/{source_step_id}', f'/{target_step_id}')
        
        # 6. Transform step.id references
        elif f'{source_step_id}' in line and 'step.id' in line:
            transformed_line = re.sub(rf'\b{re.escape(source_step_id)}\b', target_step_id, line)
        
        # 7. Transform quoted step ID strings
        elif f'"{source_step_id}"' in line or f"'{source_step_id}'" in line:
            transformed_line = re.sub(rf"(['\"]){re.escape(source_step_id)}(['\"])", rf"\1{target_step_id}\2", line)
        
        # 8. Transform step data calls - be very careful with these
        elif 'set_step_data' in line and f'"{source_step_id}"' in line:
            transformed_line = re.sub(rf'"{re.escape(source_step_id)}"', f'"{target_step_id}"', line)
        elif 'set_step_data' in line and f"'{source_step_id}'" in line:
            transformed_line = re.sub(rf"'{re.escape(source_step_id)}'", f"'{target_step_id}'", line)
        
        # 9. Transform chain_reverter calls
        elif 'chain_reverter' in line and f'"{source_step_id}"' in line:
            transformed_line = re.sub(rf'"{re.escape(source_step_id)}"', f'"{target_step_id}"', line)
        elif 'chain_reverter' in line and f"'{source_step_id}'" in line:
            transformed_line = re.sub(rf"'{re.escape(source_step_id)}'", f"'{target_step_id}'", line)
        
        # 10. For any remaining lines with step references, be very conservative
        # Only transform if it's clearly a step reference and not an array index
        elif source_step_id in line:
            # Skip lines that contain array indexing like self.steps[0] 
            if not re.search(rf'self\.steps\[\s*\d+\s*\]', line):
                # Only transform whole-word boundaries to avoid partial matches
                if re.search(rf'\b{re.escape(source_step_id)}\b', line):
                    transformed_line = re.sub(rf'\b{re.escape(source_step_id)}\b', target_step_id, line)
        
        transformed_lines.append(transformed_line)
    
    transformed_content = '\n'.join(transformed_lines)
    
    # Wrap with new step bundle markers (preserving the swapped content as a bundle)
    wrapped = f"# --- START_STEP_BUNDLE: {target_step_id} ---\n{transformed_content}\n# --- END_STEP_BUNDLE: {target_step_id} ---"
    
    return wrapped


def transform_step_definition(step_definition: str, source_step_id: str, target_step_id: str) -> str:
    """Transform step definition by renaming step IDs and maintaining proper structure"""
    
    lines = step_definition.split('\n')
    transformed_lines = []
    
    for line in lines:
        transformed_line = line
        
        # Transform id='step_xx' or id="step_xx" assignments
        if re.search(rf"id\s*=\s*['\"]", line):
            pattern = rf"(id\s*=\s*['\"]){re.escape(source_step_id)}(['\"])"
            transformed_line = re.sub(pattern, rf"\1{target_step_id}\2", line)
        
        # Also handle any other references to the step ID in the definition
        # (like in comments or other string values)
        elif source_step_id in line:
            # Only transform whole-word references
            transformed_line = re.sub(rf'\b{re.escape(source_step_id)}\b', target_step_id, line)
        
        transformed_lines.append(transformed_line)
    
    return '\n'.join(transformed_lines)


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
    
    # Extract source Step definition
    source_step_definition = extract_step_definition(source_content, args.source_bundle_id)
    if source_step_definition is None:
        print(f"Warning: Could not find Step definition for '{args.source_bundle_id}' in source file")
        print("The method bundle will be swapped, but Step definition will need manual update.")
        step_definition_available = False
    else:
        print(f"✓ Extracted Step definition for '{args.source_bundle_id}'")
        step_definition_available = True
    
    # Identify potential dependencies
    dependencies = identify_potential_dependencies(bundle_content)
    if dependencies:
        print(f"⚠️  Potential dependencies detected: {', '.join(dependencies)}")
        print("   Make sure these are defined in the target workflow")
    
    # Transform bundle content
    transformed_bundle = transform_bundle_content(bundle_content, args.source_bundle_id, args.target_step_id)
    
    # Transform step definition if available
    if step_definition_available:
        transformed_step_definition = transform_step_definition(source_step_definition, args.source_bundle_id, args.target_step_id)
    
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
    
    # Replace Step definition if available
    step_definition_replaced = False
    if step_definition_available:
        new_content, step_definition_replaced = replace_step_definition_in_target(
            new_content, args.target_step_id, transformed_step_definition
        )
        
        if step_definition_replaced:
            print(f"✓ Found and replaced Step definition for '{args.target_step_id}'")
        else:
            print(f"Warning: Could not find Step definition for '{args.target_step_id}' in target file")
            print("The Step definition will need manual update.")
    
    # Write the modified content
    if not args.force:
        response = input(f"Replace step '{args.target_step_id}' in {target_path}? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled")
            sys.exit(0)
    
    target_path.write_text(new_content)
    
    # Success summary
    success_parts = [f"methods"]
    if step_definition_replaced:
        success_parts.append("Step definition")
    
    print(f"✅ Successfully swapped {' and '.join(success_parts)} for step '{args.target_step_id}' in {target_path}")
    
    if dependencies:
        print("\n🔍 Dependency Check:")
        print("   The following potential dependencies were detected in the swapped code:")
        for dep in dependencies:
            print(f"   • {dep}")
        print("   Please ensure these are defined in your target workflow class.")
    
    if not step_definition_available or not step_definition_replaced:
        print("\n⚠️  Manual Step Definition Update Needed:")
        print(f"   Please verify that the Step definition for '{args.target_step_id}' in self.steps")
        print("   matches the requirements of the swapped methods (done key, show name, etc.)")


if __name__ == '__main__':
    main() 