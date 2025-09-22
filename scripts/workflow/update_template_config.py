#!/usr/bin/env python3
"""
Template Configuration Updater

This script updates the TEMPLATE_CONFIG dictionary in a Python workflow file
using AST manipulation for surgical precision.

USAGE:
    python update_template_config.py <target_file> <config_json>

EXAMPLE:
    python update_template_config.py 110_parameter_buster.py '{"analysis": "Not Compliant", "crawler": "Crawl Basic", "gsc": "GSC Performance"}'
"""

import ast
import json
import sys
from pathlib import Path
from typing import Dict, Any

class TemplateConfigUpdater:
    """Updates TEMPLATE_CONFIG in Python files using AST manipulation."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"ℹ️  {message}")
    
    def update_template_config(self, file_path: str, new_config: str) -> bool:
        """Update TEMPLATE_CONFIG in the Python file using AST manipulation.
        
        Args:
            file_path: Path to the Python file to update
            new_config: JSON string representing the new configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(file_path)
            
            # Validate file exists
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            self.log(f"Reading file: {file_path}")
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the JSON configuration
            try:
                config_dict = json.loads(new_config)
                self.log(f"Parsed config: {config_dict}")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON configuration: {e}")
                return False
            
            # Parse the AST
            try:
                tree = ast.parse(content)
                self.log("Successfully parsed AST")
            except SyntaxError as e:
                print(f"❌ Syntax error in file: {e}")
                return False
            
            # Find the class
            class_node = self._find_class_node(tree)
            if not class_node:
                print("❌ Could not find class in file")
                return False
            
            self.log(f"Found class: {class_node.name}")
            
            # Find and update TEMPLATE_CONFIG
            config_updated = self._update_template_config_in_class(class_node, config_dict)
            
            if not config_updated:
                print("❌ Could not find TEMPLATE_CONFIG assignment")
                return False
            
            # Generate the updated code
            try:
                updated_code = ast.unparse(tree)
                self.log("Successfully generated updated code")
            except Exception as e:
                print(f"❌ Error generating code: {e}")
                return False
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_code)
            
            print(f"✅ Successfully updated TEMPLATE_CONFIG in {file_path}")
            self.log(f"New configuration: {config_dict}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating template config: {e}")
            return False
    
    def _find_class_node(self, tree: ast.AST) -> ast.ClassDef:
        """Find the main class node in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                return node
        return None
    
    def _update_template_config_in_class(self, class_node: ast.ClassDef, config_dict: Dict[str, Any]) -> bool:
        """Update TEMPLATE_CONFIG assignment in the class."""
        for node in class_node.body:
            if self._is_template_config_assignment(node):
                self.log("Found TEMPLATE_CONFIG assignment")
                
                # Create new AST node for the dictionary
                new_value = self._create_dict_ast_node(config_dict)
                
                # Replace the value
                node.value = new_value
                self.log(f"Updated TEMPLATE_CONFIG: {config_dict}")
                return True
        
        return False
    
    def _is_template_config_assignment(self, node: ast.AST) -> bool:
        """Check if the node is a TEMPLATE_CONFIG assignment."""
        return (isinstance(node, ast.Assign) and 
                len(node.targets) == 1 and
                isinstance(node.targets[0], ast.Name) and
                node.targets[0].id == 'TEMPLATE_CONFIG')
    
    def _create_dict_ast_node(self, config_dict: Dict[str, Any]) -> ast.Dict:
        """Create an AST Dict node from a Python dictionary."""
        return ast.Dict(
            keys=[ast.Constant(value=k) for k in config_dict.keys()],
            values=[ast.Constant(value=v) for v in config_dict.values()]
        )
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that the file is syntactically correct Python."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            # Try to compile the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, str(file_path), 'exec')
            self.log(f"✅ File {file_path} is syntactically valid")
            return True
            
        except SyntaxError as e:
            print(f"❌ Syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error validating {file_path}: {e}")
            return False
    
    def show_current_config(self, file_path: str) -> bool:
        """Show the current TEMPLATE_CONFIG in the file."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            class_node = self._find_class_node(tree)
            
            if not class_node:
                print("❌ Could not find class in file")
                return False
            
            # Find TEMPLATE_CONFIG
            for node in class_node.body:
                if self._is_template_config_assignment(node):
                    config_value = ast.unparse(node.value)
                    print(f"📋 Current TEMPLATE_CONFIG: {config_value}")
                    return True
            
            print("❌ TEMPLATE_CONFIG not found in file")
            return False
            
        except Exception as e:
            print(f"❌ Error reading current config: {e}")
            return False

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python update_template_config.py <target_file> [<config_json>]")
        print("   Or: python update_template_config.py <target_file> --show")
        print("   Or: python update_template_config.py <target_file> --validate")
        sys.exit(1)
    
    target_file = sys.argv[1]
    updater = TemplateConfigUpdater(verbose=True)
    
    if len(sys.argv) == 2:
        # Just show current config
        success = updater.show_current_config(target_file)
    elif len(sys.argv) == 3:
        if sys.argv[2] == "--show":
            success = updater.show_current_config(target_file)
        elif sys.argv[2] == "--validate":
            success = updater.validate_file(target_file)
        else:
            # Update config
            config_json = sys.argv[2]
            success = updater.update_template_config(target_file, config_json)
    else:
        print("❌ Too many arguments")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 