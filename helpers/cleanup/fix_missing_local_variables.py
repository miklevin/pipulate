#!/usr/bin/env python3
"""
Fix Missing Local Variables Tool

This tool addresses the common issue where methods reference variables (like TOKEN_FILE)
that are defined in other methods but not locally. This is particularly common after
code transplantation or refactoring operations.

Why This Tool Exists:
- AI edit tools struggle with precise insertion at method beginnings
- Simple variable definitions require exact positioning and indentation
- Token-efficient: Completes complex variable insertion in single operations
- Deterministic: Same input always produces same output

Usage Examples:
    # Fix specific variable in specific method
    python fix_missing_local_variables.py file.py --method check_if_project_has_collection --variable TOKEN_FILE --value "botify_token.txt"
    
    # Auto-detect missing TOKEN_FILE definitions
    python fix_missing_local_variables.py file.py --auto-fix-token-file
    
    # Show what would be fixed without making changes
    python fix_missing_local_variables.py file.py --auto-fix-token-file --dry-run

Real-World Example:
    The Parameter Buster workflow transplantation left several methods referencing TOKEN_FILE
    without local definitions, causing NameError at runtime. This tool fixes such issues
    by detecting usage patterns and inserting proper variable definitions.
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class MissingVariableFixer:
    """
    Tool for fixing missing local variable definitions in Python methods.
    
    Handles cases where methods use variables that are defined in other methods
    but not locally, causing NameError at runtime.
    """
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.content = ""
        self.lines = []
        self.changes_made = []
        
    def load_file(self) -> bool:
        """Load the target file content."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            self.lines = self.content.split('\n')
            return True
        except Exception as e:
            print(f"Error loading file {self.file_path}: {e}")
            return False
    
    def save_file(self) -> bool:
        """Save the modified content back to file."""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.lines))
            return True
        except Exception as e:
            print(f"Error saving file {self.file_path}: {e}")
            return False
    
    def find_method_boundaries(self, method_name: str) -> Optional[Tuple[int, int, int]]:
        """
        Find the boundaries of a specific method.
        
        Returns:
            Tuple[start_line, docstring_end_line, method_end_line] or None if not found
        """
        method_pattern = rf'^\s*(async\s+)?def\s+{re.escape(method_name)}\s*\('
        
        method_start = None
        docstring_end = None
        method_end = None
        base_indent = None
        in_docstring = False
        docstring_quote_type = None
        
        for i, line in enumerate(self.lines):
            # Find method start
            if method_start is None and re.match(method_pattern, line):
                method_start = i
                base_indent = len(line) - len(line.lstrip())
                continue
            
            if method_start is not None:
                # Track docstring
                if not in_docstring and not docstring_end:
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        in_docstring = True
                        docstring_quote_type = stripped[:3]
                        # Check if docstring ends on same line
                        if stripped.count(docstring_quote_type) >= 2:
                            in_docstring = False
                            docstring_end = i
                elif in_docstring:
                    if docstring_quote_type in line:
                        in_docstring = False
                        docstring_end = i
                
                # Find method end (next method or class definition at same or lower indent)
                if i > method_start and line.strip():
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= base_indent and (
                        line.strip().startswith('def ') or 
                        line.strip().startswith('async def ') or
                        line.strip().startswith('class ')
                    ):
                        method_end = i - 1
                        break
        
        # If we reached end of file, method ends there
        if method_start is not None and method_end is None:
            method_end = len(self.lines) - 1
        
        if method_start is not None:
            # If no docstring found, assume it ends right after method definition
            if docstring_end is None:
                docstring_end = method_start
            return (method_start, docstring_end, method_end)
        
        return None
    
    def detect_variable_usage(self, method_start: int, method_end: int, variable_name: str) -> List[int]:
        """
        Detect lines where a variable is used within a method.
        
        Returns:
            List of line numbers where the variable is referenced
        """
        usage_lines = []
        
        for i in range(method_start, method_end + 1):
            line = self.lines[i]
            # Look for variable usage (not in comments)
            if variable_name in line and not line.strip().startswith('#'):
                # Check if it's actually a usage (not a definition)
                if f'{variable_name}' in line and f'{variable_name} =' not in line:
                    usage_lines.append(i)
        
        return usage_lines
    
    def detect_variable_definition(self, method_start: int, method_end: int, variable_name: str) -> Optional[int]:
        """
        Detect if a variable is defined within a method.
        
        Returns:
            Line number where variable is defined, or None if not found
        """
        for i in range(method_start, method_end + 1):
            line = self.lines[i].strip()
            if line.startswith(f'{variable_name} ='):
                return i
        return None
    
    def get_method_body_start(self, method_start: int, docstring_end: int) -> int:
        """
        Find the first line where method body code should start.
        
        Returns:
            Line number where variable definition should be inserted
        """
        # Start looking after docstring
        for i in range(docstring_end + 1, len(self.lines)):
            line = self.lines[i].strip()
            if line and not line.startswith('#'):
                return i
        
        # Fallback: right after docstring
        return docstring_end + 1
    
    def get_method_indent(self, method_start: int) -> str:
        """Get the indentation string for method body."""
        method_line = self.lines[method_start]
        base_indent = len(method_line) - len(method_line.lstrip())
        return ' ' * (base_indent + 4)  # Method body is indented 4 more spaces
    
    def fix_missing_variable(self, method_name: str, variable_name: str, variable_value: str, dry_run: bool = False) -> bool:
        """
        Fix a missing variable definition in a specific method.
        
        Args:
            method_name: Name of the method to fix
            variable_name: Name of the variable to define
            variable_value: Value to assign to the variable (will be quoted if string)
            dry_run: If True, don't make changes, just report what would be done
            
        Returns:
            True if fix was applied (or would be applied), False otherwise
        """
        boundaries = self.find_method_boundaries(method_name)
        if not boundaries:
            print(f"Method '{method_name}' not found")
            return False
        
        method_start, docstring_end, method_end = boundaries
        
        # Check if variable is used but not defined
        usage_lines = self.detect_variable_usage(method_start, method_end, variable_name)
        definition_line = self.detect_variable_definition(method_start, method_end, variable_name)
        
        if not usage_lines:
            print(f"Variable '{variable_name}' not used in method '{method_name}'")
            return False
        
        if definition_line is not None:
            print(f"Variable '{variable_name}' already defined in method '{method_name}' at line {definition_line + 1}")
            return False
        
        # Determine insertion point
        insert_line = self.get_method_body_start(method_start, docstring_end)
        indent = self.get_method_indent(method_start)
        
        # Format the variable definition
        if variable_value.startswith('"') or variable_value.startswith("'"):
            definition = f"{indent}{variable_name} = {variable_value}"
        else:
            definition = f"{indent}{variable_name} = '{variable_value}'"
        
        change_description = f"Add {variable_name} definition in {method_name}() at line {insert_line + 1}"
        
        if dry_run:
            print(f"[DRY RUN] Would {change_description}")
            print(f"[DRY RUN] Would insert: {definition}")
            return True
        
        # Insert the definition
        self.lines.insert(insert_line, definition)
        self.changes_made.append(change_description)
        print(f"✓ {change_description}")
        
        return True
    
    def auto_fix_token_file(self, dry_run: bool = False) -> int:
        """
        Automatically detect and fix missing TOKEN_FILE definitions.
        
        Returns:
            Number of fixes applied
        """
        fixes_applied = 0
        
        # Find all methods that use TOKEN_FILE
        method_pattern = r'^\s*(async\s+)?def\s+(\w+)\s*\('
        
        for i, line in enumerate(self.lines):
            method_match = re.match(method_pattern, line)
            if method_match:
                method_name = method_match.group(2)
                
                # Skip if this is the method that defines TOKEN_FILE correctly
                if method_name == 'read_api_token':
                    continue
                
                boundaries = self.find_method_boundaries(method_name)
                if boundaries:
                    method_start, docstring_end, method_end = boundaries
                    usage_lines = self.detect_variable_usage(method_start, method_end, 'TOKEN_FILE')
                    definition_line = self.detect_variable_definition(method_start, method_end, 'TOKEN_FILE')
                    
                    if usage_lines and definition_line is None:
                        if self.fix_missing_variable(method_name, 'TOKEN_FILE', 'botify_token.txt', dry_run):
                            fixes_applied += 1
        
        return fixes_applied

def main():
    parser = argparse.ArgumentParser(
        description='Fix missing local variable definitions in Python methods',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('file', help='Python file to fix')
    parser.add_argument('--method', help='Specific method name to fix')
    parser.add_argument('--variable', help='Variable name to define')
    parser.add_argument('--value', help='Value to assign to the variable')
    parser.add_argument('--auto-fix-token-file', action='store_true', 
                       help='Automatically detect and fix missing TOKEN_FILE definitions')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be fixed without making changes')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"Error: File '{args.file}' not found")
        sys.exit(1)
    
    fixer = MissingVariableFixer(args.file)
    if not fixer.load_file():
        sys.exit(1)
    
    fixes_applied = 0
    
    if args.auto_fix_token_file:
        print(f"Auto-fixing TOKEN_FILE definitions in {args.file}...")
        fixes_applied = fixer.auto_fix_token_file(args.dry_run)
        
    elif args.method and args.variable and args.value:
        print(f"Fixing {args.variable} in method {args.method}...")
        if fixer.fix_missing_variable(args.method, args.variable, args.value, args.dry_run):
            fixes_applied = 1
    
    else:
        print("Error: Must specify either --auto-fix-token-file or --method/--variable/--value")
        parser.print_help()
        sys.exit(1)
    
    if fixes_applied > 0 and not args.dry_run:
        if fixer.save_file():
            print(f"\n✓ Successfully applied {fixes_applied} fixes to {args.file}")
            if fixer.changes_made:
                print("\nChanges made:")
                for change in fixer.changes_made:
                    print(f"  - {change}")
        else:
            print(f"\nError: Failed to save changes to {args.file}")
            sys.exit(1)
    elif args.dry_run:
        print(f"\n[DRY RUN] Would apply {fixes_applied} fixes to {args.file}")
    else:
        print(f"\nNo fixes needed for {args.file}")

if __name__ == '__main__':
    main() 