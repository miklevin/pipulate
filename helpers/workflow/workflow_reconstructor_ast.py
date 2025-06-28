#!/usr/bin/env python3
"""
AST-Based Workflow Reconstructor - Robust Python Code Manipulation

This module uses Python's Abstract Syntax Tree (AST) to properly parse, 
extract, and reconstruct workflow Python files. This replaces the fragile
string manipulation approach with proper syntactic understanding.

Key advantages of AST approach:
- Proper Python syntax understanding
- Reliable method extraction and insertion
- Consistent indentation generation
- Syntactically correct output guaranteed
"""

import ast
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set


class ASTWorkflowReconstructor:
    """AST-based workflow reconstruction with surgical precision."""
    
    def __init__(self, base_dir: str = "/home/mike/repos/pipulate"):
        self.base_dir = Path(base_dir)
        self.plugins_dir = self.base_dir / "plugins"
        
        # Define template methods that should NOT be extracted as Chunk 2
        self.template_methods = {
            'landing', 'init', 'finalize', 'unfinalize', 'get_suggestion',
            'handle_revert', 'step_project', 'step_project_submit', 
            'step_analysis', 'step_analysis_submit', 'step_analysis_process',
            'step_crawler', 'step_crawler_submit', 'step_crawler_complete',
            'step_webogs', 'step_webogs_submit', 'step_webogs_process',
            'step_webogs_complete', 'step_gsc', 'step_gsc_submit', 
            'step_gsc_process', 'step_gsc_complete', 'common_toggle',
            'update_button_text', 'validate_botify_url', 
            'check_if_project_has_collection', 'fetch_analyses', 'read_api_token',
            'build_exports', 'poll_job_status', '_execute_qualifier_logic',
            'get_deterministic_filepath', 'check_file_exists', 'ensure_directory_exists',
            'check_cached_file_for_button_text', '_generate_api_call_representations',
            'process_search_console_data', 'convert_jobs_to_query_payload',
            '_convert_bqlv2_to_query', '_convert_bqlv1_to_query', 'generate_query_api_call',
            '_generate_bqlv2_python_code', '_generate_bqlv1_python_code',
            '_get_step_name_from_payload', '_diagnose_query_endpoint_error',
            '_prepare_action_button_data', '_create_action_buttons',
            'discover_fields_endpoint', 'validate_template_fields'
        }
    
    def parse_file(self, file_path: Path) -> ast.AST:
        """Parse a Python file into an AST."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return ast.parse(content)
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
            raise
    
    def find_class_node(self, tree: ast.AST) -> Optional[ast.ClassDef]:
        """Find the main workflow class in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                return node
        return None
    
    def extract_chunk2_steps_and_methods(self, source_tree: ast.AST) -> tuple[List[str], List[ast.FunctionDef]]:
        """Extract workflow-specific steps and methods (Chunk 2) from source AST."""
        class_node = self.find_class_node(source_tree)
        if not class_node:
            return [], []
        
        # Extract Chunk 2 step definitions from steps list
        chunk2_step_definitions = []
        chunk2_methods = []
        
        # Find the steps list assignment (both class-level and inside __init__ method)
        print("🔍 DEBUG: Looking for step assignments...")
        
        # Check class-level assignments first
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    print(f"    Class-level assignment: {ast.unparse(target)}")
                    self._check_steps_assignment(node, target, chunk2_step_definitions)
        
        # Check inside __init__ method
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                print("  🔍 Looking inside __init__ method...")
                for init_node in node.body:
                    if isinstance(init_node, ast.Assign):
                        for target in init_node.targets:
                            print(f"    __init__ assignment: {ast.unparse(target)}")
                            self._check_steps_assignment(init_node, target, chunk2_step_definitions)
                break
        
        # Extract Chunk 2 methods
        chunk2_methods = self.extract_chunk2_methods(class_node)
        
        print(f"📋 Found {len(chunk2_step_definitions)} Chunk 2 step definitions")
        print(f"📦 Found {len(chunk2_methods)} Chunk 2 methods")
        return chunk2_step_definitions, chunk2_methods
    
    def _check_steps_assignment(self, assign_node: ast.Assign, target: ast.AST, chunk2_step_definitions: List[str]):
        """Check if an assignment node is a steps assignment and extract Chunk 2 steps."""
        # Check for both self.steps and local steps variable
        is_steps_assignment = (
            (isinstance(target, ast.Attribute) and target.attr == 'steps') or  # self.steps
            (isinstance(target, ast.Name) and target.id == 'steps')  # local steps variable
        )
        
        if is_steps_assignment:
            print(f"  🔍 Found steps assignment: {ast.unparse(target)}")
            print(f"      Value type: {type(assign_node.value)}")
            if isinstance(assign_node.value, ast.List):
                print(f"      List has {len(assign_node.value.elts)} elements")
                for i, element in enumerate(assign_node.value.elts):
                    step_def_str = ast.unparse(element)
                    print(f"        Element {i}: {step_def_str}")
                    # Check if this is a Chunk 2 step (parameter-specific)
                    if any(step_id in step_def_str for step_id in ['step_parameters', 'step_optimization', 'step_robots']):
                        chunk2_step_definitions.append(step_def_str)
                        print(f"  📋 Extracted Chunk 2 step definition: {step_def_str}")
            else:
                print(f"      Not a list - value: {ast.unparse(assign_node.value)}")
    
    def extract_chunk2_methods(self, class_node: ast.ClassDef) -> List[ast.FunctionDef]:
        """Extract Chunk 2 methods from the class node."""
        chunk2_methods = []
        
        print("🔍 DEBUG: All methods found in source:")
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_name = node.name
                print(f"    Method: {method_name}")
                
                # Identify workflow-specific methods (NOT template methods)
                # Debug each condition
                starts_with_params = method_name.startswith('step_parameters')
                starts_with_optim = method_name.startswith('step_optimization')
                starts_with_robots = method_name.startswith('step_robots')
                has_parameter = 'parameter' in method_name
                has_optimization = 'optimization' in method_name
                has_robots = 'robots' in method_name
                not_in_template = method_name not in self.template_methods
                not_private = not method_name.startswith('_')
                not_template_step = not any(method_name.startswith(prefix) for prefix in 
                    ['step_project', 'step_analysis', 'step_crawler', 'step_webogs', 'step_gsc'])
                
                is_workflow_specific = (
                    starts_with_params or starts_with_optim or starts_with_robots or
                    has_parameter or has_optimization or has_robots or
                    (not_in_template and not_private and not_template_step)
                )
                
                print(f"    📋 Debug for {method_name}:")
                print(f"      starts_with_params: {starts_with_params}")
                print(f"      starts_with_optim: {starts_with_optim}")
                print(f"      starts_with_robots: {starts_with_robots}")
                print(f"      has_parameter: {has_parameter}")
                print(f"      has_optimization: {has_optimization}")
                print(f"      has_robots: {has_robots}")
                print(f"      not_in_template: {not_in_template}")
                print(f"      not_private: {not_private}")
                print(f"      not_template_step: {not_template_step}")
                print(f"      => is_workflow_specific: {is_workflow_specific}")
                
                if is_workflow_specific:
                    chunk2_methods.append(node)
                    print(f"  📦 Extracted Chunk 2 method: {method_name}")
                else:
                    print(f"  ⏭️  Skipped (template method): {method_name}")
        
        return chunk2_methods
    
    def find_insertion_point(self, class_node: ast.ClassDef) -> int:
        """Find the best insertion point for Chunk 2 methods."""
        # Look for the insertion marker comment
        for i, node in enumerate(class_node.body):
            if (hasattr(node, 'lineno') and 
                hasattr(node, 'col_offset') and
                isinstance(node, ast.Expr) and
                isinstance(node.value, ast.Constant) and
                'STEP_METHODS_INSERTION_POINT' in str(node.value.value)):
                return i
        
        # Fallback: insert before the last few methods (usually utility methods)
        return max(0, len(class_node.body) - 3)
    
    def insert_chunk2_steps_and_methods(self, target_tree: ast.AST, chunk2_step_definitions: List[str], chunk2_methods: List[ast.FunctionDef]) -> ast.AST:
        """Insert Chunk 2 step definitions and methods into target AST."""
        class_node = self.find_class_node(target_tree)
        if not class_node:
            print("❌ Could not find target class")
            return target_tree
        
        # Insert step definitions into steps list
        if chunk2_step_definitions:
            print(f"📋 Inserting {len(chunk2_step_definitions)} step definitions...")
            self.insert_step_definitions(class_node, chunk2_step_definitions)
        
        # Insert methods
        if chunk2_methods:
            print(f"📦 Inserting {len(chunk2_methods)} methods...")
            insertion_point = self.find_insertion_point(class_node)
            
            # Create a comment marker for the inserted methods
            chunk2_comment = ast.Expr(
                value=ast.Constant(value="\n    # --- CHUNK 2: WORKFLOW-SPECIFIC METHODS (TRANSPLANTED FROM ORIGINAL) ---\n")
            )
            
            # Insert the comment and methods
            new_body = (
                class_node.body[:insertion_point] + 
                [chunk2_comment] + 
                chunk2_methods + 
                class_node.body[insertion_point:]
            )
            
            class_node.body = new_body
            
            for method in chunk2_methods:
                print(f"  ➕ Inserted method: {method.name}")
        
        return target_tree
    
    def insert_step_definitions(self, class_node: ast.ClassDef, chunk2_step_definitions: List[str]):
        """Insert Chunk 2 step definitions into the steps list before finalize."""
        # Look for both static assignments and dynamic step building methods
        inserted = False
        
        # First, try to find static step assignments
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    is_steps_assignment = (
                        (isinstance(target, ast.Attribute) and target.attr == 'steps') or
                        (isinstance(target, ast.Name) and target.id == 'steps')
                    )
                    
                    if is_steps_assignment and isinstance(node.value, ast.List):
                        print(f"  🔧 Inserting into static steps assignment: {ast.unparse(target)}")
                        inserted = self._insert_into_static_steps(node, chunk2_step_definitions)
                        if inserted:
                            break
        
        # If no static assignment found, look for dynamic step building method
        if not inserted:
            for node in class_node.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '_build_dynamic_steps':
                    print(f"  🔧 Inserting into dynamic step building method: {node.name}")
                    inserted = self._insert_into_dynamic_steps(node, chunk2_step_definitions)
                    break
        
        if not inserted:
            print("  ⚠️  Could not find suitable insertion point for step definitions")
    
    def _insert_into_static_steps(self, assign_node: ast.Assign, chunk2_step_definitions: List[str]) -> bool:
        """Insert steps into a static steps assignment."""
        # Find insertion point (before finalize step)
        finalize_index = -1
        for i, element in enumerate(assign_node.value.elts):
            element_str = ast.unparse(element)
            if 'finalize' in element_str:
                finalize_index = i
                break
        
        # Insert Chunk 2 steps before finalize
        if finalize_index >= 0:
            for j, step_def_str in enumerate(chunk2_step_definitions):
                step_ast = ast.parse(step_def_str, mode='eval').body
                assign_node.value.elts.insert(finalize_index + j, step_ast)
                print(f"  📋 Inserted step definition before finalize: {step_def_str}")
        else:
            # No finalize found, append at end
            for step_def_str in chunk2_step_definitions:
                step_ast = ast.parse(step_def_str, mode='eval').body
                assign_node.value.elts.append(step_ast)
                print(f"  📋 Appended step definition: {step_def_str}")
        
        return True
    
    def _insert_into_dynamic_steps(self, method_node: ast.FunctionDef, chunk2_step_definitions: List[str]) -> bool:
        """Insert steps into a dynamic step building method."""
        # Look for steps.extend([...]) calls or return statements with steps list
        for node in ast.walk(method_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'extend':
                # Found steps.extend([...]) - insert before finalize in the extend list
                if isinstance(node.args[0], ast.List):
                    finalize_index = -1
                    for i, element in enumerate(node.args[0].elts):
                        element_str = ast.unparse(element)
                        if 'finalize' in element_str:
                            finalize_index = i
                            break
                    
                    if finalize_index >= 0:
                        for j, step_def_str in enumerate(chunk2_step_definitions):
                            step_ast = ast.parse(step_def_str, mode='eval').body
                            node.args[0].elts.insert(finalize_index + j, step_ast)
                            print(f"  📋 Inserted step definition before finalize in extend: {step_def_str}")
                        return True
        
        # If no extend found, look for return statement with steps list
        for node in ast.walk(method_node):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == 'steps':
                # Found return steps - need to insert before this return
                # Look backwards for the steps list assignment
                for stmt in reversed(method_node.body):
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and target.id == 'steps':
                                if isinstance(stmt.value, ast.List):
                                    return self._insert_into_static_steps(stmt, chunk2_step_definitions)
        
        print("  ⚠️  Could not find insertion point in dynamic step building method")
        return False
    
    def update_class_attributes(self, target_tree: ast.AST, transformations: Dict[str, str]) -> ast.AST:
        """Update class attributes like APP_NAME, DISPLAY_NAME, etc."""
        class_node = self.find_class_node(target_tree)
        if not class_node:
            return target_tree
        
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in transformations:
                        # Update the value
                        new_value = transformations[target.id]
                        if isinstance(node.value, ast.Constant):
                            node.value.value = new_value
                        elif isinstance(node.value, ast.Str):  # Python < 3.8 compatibility
                            node.value.s = new_value
        
        return target_tree
    
    def update_class_name(self, target_tree: ast.AST, new_class_name: str) -> ast.AST:
        """Update the class name in the AST."""
        class_node = self.find_class_node(target_tree)
        if class_node:
            class_node.name = new_class_name
        return target_tree
    
    def extract_class_attributes(self, source_tree: ast.AST) -> Dict[str, str]:
        """Extract class attributes from source file."""
        class_node = self.find_class_node(source_tree)
        if not class_node:
            return {}
        
        attributes = {}
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        attr_name = target.id
                        if isinstance(node.value, ast.Constant):
                            attributes[attr_name] = node.value.value
                        elif isinstance(node.value, ast.Str):  # Python < 3.8 compatibility
                            attributes[attr_name] = node.value.s
        
        return attributes
    
    def generate_python_code(self, tree: ast.AST) -> str:
        """Convert AST back to properly formatted Python code."""
        try:
            # Use built-in ast.unparse (Python 3.9+)
            return ast.unparse(tree)
        except Exception as e:
            print(f"❌ Error generating Python code: {e}")
            raise Exception(f"Failed to generate Python code from AST: {e}")
    
    def reconstruct_workflow(self, template_name: str, source_name: str, target_name: str, 
                           transformations: Optional[Dict[str, str]] = None,
                           new_class_name: Optional[str] = None) -> bool:
        """Main reconstruction method using AST."""
        try:
            # Parse source and template files
            source_path = self.plugins_dir / source_name
            template_path = self.plugins_dir / template_name
            target_path = self.plugins_dir / target_name
            
            print(f"🔍 Parsing source: {source_path}")
            source_tree = self.parse_file(source_path)
            
            print(f"🔍 Parsing template: {template_path}")
            template_tree = self.parse_file(template_path)
            
            # Extract Chunk 2 steps and methods from source
            print(f"📦 Extracting Chunk 2 steps and methods from {source_name}...")
            chunk2_step_definitions, chunk2_methods = self.extract_chunk2_steps_and_methods(source_tree)
            print(f"✅ Found {len(chunk2_step_definitions)} Chunk 2 step definitions and {len(chunk2_methods)} methods")
            
            # Insert steps and methods into template
            print(f"🔧 Inserting steps and methods into template...")
            modified_tree = self.insert_chunk2_steps_and_methods(template_tree, chunk2_step_definitions, chunk2_methods)
            
            # Apply transformations if provided
            if transformations:
                print(f"🔄 Applying transformations...")
                modified_tree = self.update_class_attributes(modified_tree, transformations)
            
            # Update class name if provided
            if new_class_name:
                print(f"🏷️ Updating class name to: {new_class_name}")
                modified_tree = self.update_class_name(modified_tree, new_class_name)
            
            # Generate final Python code
            print(f"📝 Generating Python code...")
            final_code = self.generate_python_code(modified_tree)
            
            # Write to target file
            print(f"💾 Writing to {target_path}")
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(final_code)
            
            print(f"✅ Successfully created {target_name}")
            return True
            
        except Exception as e:
            print(f"❌ Reconstruction failed: {e}")
            return False
    
    def create_variant_from_existing(self, template_name: str, existing_name: str, 
                                   suffix: str) -> bool:
        """Create a variant workflow with suffix applied to names."""
        # Extract base names from existing file
        existing_path = self.plugins_dir / existing_name
        source_tree = self.parse_file(existing_path)
        source_attrs = self.extract_class_attributes(source_tree)
        
        # Generate new names with suffix
        base_name = existing_name.replace('.py', '')
        new_filename = f"{base_name}{suffix}.py"
        
        transformations = {}
        if 'APP_NAME' in source_attrs:
            transformations['APP_NAME'] = f"{source_attrs['APP_NAME']}{suffix}"
        if 'DISPLAY_NAME' in source_attrs:
            transformations['DISPLAY_NAME'] = f"{source_attrs['DISPLAY_NAME']} {suffix}"
        
        # Find class name and transform it
        new_class_name = None
        class_node = self.find_class_node(source_tree)
        if class_node:
            original_class_name = class_node.name
            new_class_name = f"{original_class_name}{suffix}"
        
        print(f"🔄 Creating variant: {existing_name} + {suffix} -> {new_filename}")
        print(f"📝 Transformations: {transformations}")
        if new_class_name:
            print(f"🏷️ Class name: {class_node.name} -> {new_class_name}")
        
        return self.reconstruct_workflow(
            template_name=template_name,
            source_name=existing_name,
            target_name=new_filename,
            transformations=transformations,
            new_class_name=new_class_name
        )


def main():
    """CLI interface for AST-based workflow reconstruction."""
    parser = argparse.ArgumentParser(
        description="AST-based workflow reconstructor with surgical precision"
    )
    parser.add_argument('--template', required=True, 
                       help='Template workflow name (e.g., "400_botify_trifecta.py")')
    parser.add_argument('--source', required=True,
                       help='Source workflow to extract Chunk 2 methods from')
    
    # Create mutually exclusive group for target vs suffix
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument('--target',
                       help='Target filename for the new workflow')
    target_group.add_argument('--suffix', 
                       help='Suffix to add to existing workflow (alternative to --target)')
    
    args = parser.parse_args()
    
    reconstructor = ASTWorkflowReconstructor()
    
    if args.suffix:
        success = reconstructor.create_variant_from_existing(
            template_name=args.template,
            existing_name=args.source,
            suffix=args.suffix
        )
    else:
        success = reconstructor.reconstruct_workflow(
            template_name=args.template,
            source_name=args.source,
            target_name=args.target
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 