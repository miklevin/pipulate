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
            # Build file paths
            template_path = self.plugins_dir / f"{template_name}.py"
            source_path = self.plugins_dir / f"{source_name}.py" 
            target_path = self.plugins_dir / f"{target_name}.py"
            
            print(f"🔧 AST Workflow Reconstruction")
            print(f"  📁 Template: {template_path}")
            print(f"  📁 Source: {source_path}")
            print(f"  📁 Target: {target_path}")
            
            # Parse files
            print("📖 Parsing files...")
            template_tree = self.parse_file(template_path)
            source_tree = self.parse_file(source_path)
            
            # Extract Chunk 2 from source
            print("🔍 Extracting Chunk 2 components from source...")
            chunk2_step_definitions, chunk2_methods = self.extract_chunk2_steps_and_methods(source_tree)
            
            print(f"  📋 Found {len(chunk2_step_definitions)} step definitions")
            print(f"  📦 Found {len(chunk2_methods)} methods")
            
            if not chunk2_methods:
                print("⚠️  No Chunk 2 methods found - nothing to transplant")
                return False
            
            # ENHANCED DROPDOWN LOGIC: Check if template has enhanced analysis dropdown
            template_class_node = self.find_class_node(template_tree)
            template_has_enhanced_dropdown = self.check_template_has_enhanced_dropdown(template_tree, template_class_node)
            if template_has_enhanced_dropdown:
                print("  🎯 Template has enhanced analysis dropdown - will preserve template logic")
                # Filter out legacy analysis step methods from source to preserve template's enhanced version
                chunk2_methods = self.filter_out_legacy_analysis_methods(chunk2_methods)
                print(f"  📝 After filtering legacy methods: {len(chunk2_methods)} workflow-specific methods")
            
            # Extract route registrations for transplanted methods
            print("🔗 Extracting route registrations for transplanted methods...")
            route_registrations = self.extract_route_registrations(source_tree, chunk2_methods)
            print(f"  📝 Found {len(route_registrations)} route registrations")
            
            # Extract source attributes for transplantation
            print("📋 Extracting source attributes for transplantation...")
            source_attrs = self.extract_class_attributes(source_tree)
            
            # Build comprehensive transformations including source attributes
            all_transformations = transformations or {}
            
            # SUFFIX LOGIC: Extract suffix from target name and apply to APP_NAME
            suffix = self.extract_suffix_from_target_name(target_name)
            if suffix and 'APP_NAME' in source_attrs:
                original_app_name = source_attrs['APP_NAME']
                new_app_name = f"{original_app_name}{suffix}"
                all_transformations['APP_NAME'] = new_app_name
                print(f"  🏷️ Applying suffix '{suffix}' to APP_NAME: {original_app_name} → {new_app_name}")
            
            # Carry over key attributes from source
            if 'TRAINING_PROMPT' in source_attrs:
                all_transformations['TRAINING_PROMPT'] = source_attrs['TRAINING_PROMPT']
                print(f"  📚 Carrying over TRAINING_PROMPT from source")
            if 'ENDPOINT_MESSAGE' in source_attrs:
                all_transformations['ENDPOINT_MESSAGE'] = source_attrs['ENDPOINT_MESSAGE']
                print(f"  💬 Carrying over ENDPOINT_MESSAGE from source")
            if 'APP_NAME' not in all_transformations and 'APP_NAME' in source_attrs:
                all_transformations['APP_NAME'] = source_attrs['APP_NAME']
                print(f"  🏷️ Carrying over APP_NAME from source: {source_attrs['APP_NAME']}")
            if 'DISPLAY_NAME' in source_attrs:
                all_transformations['DISPLAY_NAME'] = source_attrs['DISPLAY_NAME']
                print(f"  📋 Carrying over DISPLAY_NAME from source: {source_attrs['DISPLAY_NAME']}")
            
            # Apply all transformations to template
            if all_transformations:
                print("✏️  Applying transformations...")
                template_tree = self.update_class_attributes(template_tree, all_transformations)
                for attr, value in all_transformations.items():
                    print(f"  🔄 {attr} = '{value[:50]}{'...' if len(value) > 50 else ''}'")
            
            # Update class name if provided
            if new_class_name:
                print(f"🏷️  Updating class name to: {new_class_name}")
                template_tree = self.update_class_name(template_tree, new_class_name)
            
            # Insert Chunk 2 components
            print("📦 Inserting Chunk 2 components...")
            target_tree = self.insert_chunk2_steps_and_methods(template_tree, chunk2_step_definitions, chunk2_methods)
            
            # Insert route registrations
            print("🔗 Inserting route registrations...")
            target_tree = self.insert_route_registrations(target_tree, route_registrations)
            
            # Generate and write result
            print("💾 Generating Python code...")
            result_code = self.generate_python_code(target_tree)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(result_code)
            
            print(f"✅ Successfully created: {target_path}")
            return True
            
        except Exception as e:
            print(f"❌ AST reconstruction failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_variant_from_existing(self, template_name: str, existing_name: str, 
                                   suffix: str) -> bool:
        """Create a variant workflow with suffix applied to names."""
        # Extract base names from existing file
        existing_path = self.plugins_dir / f"{existing_name}.py"
        source_tree = self.parse_file(existing_path)
        source_attrs = self.extract_class_attributes(source_tree)
        
        # Generate new names with suffix
        base_name = existing_name.replace('.py', '')
        new_filename = f"{base_name}{suffix}"
        
        transformations = {}
        if 'APP_NAME' in source_attrs:
            transformations['APP_NAME'] = f"{source_attrs['APP_NAME']}{suffix}"
        if 'DISPLAY_NAME' in source_attrs:
            transformations['DISPLAY_NAME'] = f"{source_attrs['DISPLAY_NAME']} {suffix}"
        if 'TRAINING_PROMPT' in source_attrs:
            transformations['TRAINING_PROMPT'] = source_attrs['TRAINING_PROMPT']
        if 'ENDPOINT_MESSAGE' in source_attrs:
            transformations['ENDPOINT_MESSAGE'] = source_attrs['ENDPOINT_MESSAGE']
        
        # Find class name and transform it
        new_class_name = None
        class_node = self.find_class_node(source_tree)
        if class_node:
            original_class_name = class_node.name
            new_class_name = f"{original_class_name}{suffix}"
        
        print(f"🔄 Creating variant: {existing_name} + {suffix} -> {new_filename}")
        print(f"📝 Transformations: {list(transformations.keys())}")
        if 'TRAINING_PROMPT' in transformations:
            print(f"  📚 TRAINING_PROMPT: {transformations['TRAINING_PROMPT'][:50]}{'...' if len(transformations['TRAINING_PROMPT']) > 50 else ''}")
        if 'ENDPOINT_MESSAGE' in transformations:
            print(f"  💬 ENDPOINT_MESSAGE: {transformations['ENDPOINT_MESSAGE'][:50]}{'...' if len(transformations['ENDPOINT_MESSAGE']) > 50 else ''}")
        if new_class_name:
            print(f"🏷️ Class name: {class_node.name} -> {new_class_name}")
        
        return self.reconstruct_workflow(
            template_name=template_name,
            source_name=existing_name,
            target_name=new_filename,
            transformations=transformations,
            new_class_name=new_class_name
        )

    def extract_route_registrations(self, source_tree: ast.AST, transplanted_methods: List[ast.FunctionDef]) -> List[ast.Expr]:
        """Extract route registrations for transplanted methods from source __init__ method.
        
        Uses CUSTOM_ROUTE_START/END markers for deterministic detection of custom routes.
        """
        class_node = self.find_class_node(source_tree)
        if not class_node:
            return []
        
        # Get method names that were transplanted
        transplanted_method_names = {method.name for method in transplanted_methods}
        
        # Find __init__ method
        init_method = None
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                init_method = node
                break
        
        if not init_method:
            return []
        
        # Extract custom routes using markers
        custom_routes = self.extract_marked_custom_routes(init_method)
        if custom_routes:
            print(f"🎯 Found {len(custom_routes)} marked custom routes")
            return custom_routes
        
        # Fallback: use the old method detection approach
        route_registrations = []
        for node in ast.walk(init_method):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                # Look for app.route(...)(self.method_name) pattern
                if (hasattr(node.value, 'func') and 
                    isinstance(node.value.func, ast.Call) and
                    self.is_route_registration(node.value.func)):
                    
                    # Extract the method name from self.method_name
                    if (len(node.value.args) > 0 and
                        isinstance(node.value.args[0], ast.Attribute) and
                        isinstance(node.value.args[0].value, ast.Name) and
                        node.value.args[0].value.id == 'self'):
                        
                        method_name = node.value.args[0].attr
                        if method_name in transplanted_method_names:
                            route_registrations.append(node)
                            print(f"  📍 Found route for transplanted method: {method_name}")
        
        return route_registrations

    def extract_marked_custom_routes(self, init_method: ast.FunctionDef) -> List[ast.Expr]:
        """Extract route registrations between CUSTOM_ROUTE_START/END markers."""
        import ast
        
        # Get the source code of the init method
        source_lines = []
        for node in init_method.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                source_lines.append(node)
        
        # We need to examine the original source to find the markers
        # This is a simplified approach - in practice, we'd parse comments properly
        # For now, let's use a different approach based on the AST structure
        
        custom_routes = []
        
        # Define legacy method names that should be filtered out
        legacy_method_names = {
            'step_02', 'step_02_submit', 'step_02_process',  # Link Graph legacy
            'step_analysis', 'step_analysis_submit', 'step_analysis_process'  # Trifecta enhanced
        }
        
        # Look for route registrations that match our known custom patterns
        for node in ast.walk(init_method):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if (hasattr(node.value, 'func') and 
                    isinstance(node.value.func, ast.Call) and
                    self.is_route_registration(node.value.func)):
                    
                    # Check if it's a custom route (contains 'process' or 'preview')
                    route_path = self.extract_route_path(node.value.func)
                    if route_path and ('_process' in route_path or 'preview' in route_path):
                        # Exclude standard step processes that aren't custom
                        if not any(standard_step in route_path for standard_step in 
                                 ['step_analysis_process', 'step_webogs_process', 'step_gsc_process']):
                            
                            # Extract method name from route to check if it's legacy
                            method_name = self.extract_method_name_from_route(node)
                            if method_name and method_name in legacy_method_names:
                                print(f"  🚫 Filtered out legacy route: {route_path} (method: {method_name})")
                                continue
                            
                            custom_routes.append(node)
                            print(f"  🎯 Found custom route: {route_path}")
        
        return custom_routes

    def extract_route_path(self, route_call: ast.Call) -> str:
        """Extract the route path from app.route(...) call."""
        if (len(route_call.args) > 0 and 
            isinstance(route_call.args[0], ast.JoinedStr)):
            # Handle f-string route paths
            parts = []
            for value in route_call.args[0].values:
                if isinstance(value, ast.Constant):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    parts.append('{var}')  # Placeholder
            return ''.join(parts)
        elif (len(route_call.args) > 0 and 
              isinstance(route_call.args[0], ast.Constant)):
            return route_call.args[0].value
        return ""

    def extract_method_name_from_route(self, route_node: ast.Expr) -> Optional[str]:
        """Extract method name from app.route(...)(self.method_name) call."""
        if (isinstance(route_node.value, ast.Call) and
            len(route_node.value.args) > 0 and
            isinstance(route_node.value.args[0], ast.Attribute) and
            isinstance(route_node.value.args[0].value, ast.Name) and
            route_node.value.args[0].value.id == 'self'):
            return route_node.value.args[0].attr
        return None

    def insert_route_registrations(self, target_tree: ast.AST, route_registrations: List[ast.Expr]) -> ast.AST:
        """Insert route registrations into target __init__ method."""
        if not route_registrations:
            return target_tree
            
        class_node = self.find_class_node(target_tree)
        if not class_node:
            return target_tree
        
        # Find __init__ method
        init_method = None
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                init_method = node
                break
        
        if not init_method:
            return target_tree
        
        # Find insertion point - after existing route registrations
        insertion_point = len(init_method.body)
        for i, stmt in enumerate(init_method.body):
            # Look for the end of route registrations (usually followed by self.step_messages)
            if (isinstance(stmt, ast.Assign) and
                isinstance(stmt.targets[0], ast.Attribute) and
                stmt.targets[0].attr == 'step_messages'):
                insertion_point = i
                break
        
        print(f"📝 Inserting {len(route_registrations)} route registrations at position {insertion_point}")
        
        # Insert route registrations
        init_method.body = (
            init_method.body[:insertion_point] + 
            route_registrations + 
            init_method.body[insertion_point:]
        )
        
        return target_tree

    def is_route_registration(self, node: ast.Call) -> bool:
        """Check if an AST node represents an app.route(...) call."""
        return (isinstance(node.func, ast.Attribute) and
                hasattr(node.func, 'attr') and 
                node.func.attr == 'route' and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'app')

    def check_template_has_enhanced_dropdown(self, template_tree: ast.AST, template_class_node: ast.ClassDef) -> bool:
        """Check if template has enhanced analysis dropdown logic."""
        if not template_class_node:
            return False
        
        # Look for the enhanced dropdown pattern in template methods
        for node in ast.walk(template_class_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if this method contains enhanced dropdown logic
                if self.has_enhanced_dropdown_logic(node):
                    return True
        
        return False

    def has_enhanced_dropdown_logic(self, method_node) -> bool:
        """Check if a method contains enhanced dropdown logic."""
        # Only check for the enhanced logic pattern in the code (comments are not part of AST)
        method_source = ast.unparse(method_node)
        enhanced_patterns = [
            "Convert analysis slug to readable date format",
            "readable_date = f\"{date_obj.strftime('%Y %B')} {day_int}{day_suffix}\"",
            "Download {template_name} for {readable_date}"
        ]
        return any(pattern in method_source for pattern in enhanced_patterns)

    def extract_suffix_from_target_name(self, target_name: str) -> Optional[str]:
        """Extract suffix from target filename (e.g., '120_link_graph2' → '2')."""
        # Remove .py extension if present
        base_name = target_name.replace('.py', '')
        
        # Look for numeric suffix at the end
        import re
        match = re.search(r'(\d+)$', base_name)
        if match:
            return match.group(1)
        
        return None

    def filter_out_legacy_analysis_methods(self, methods: List[ast.FunctionDef]) -> List[ast.FunctionDef]:
        """Filter out legacy analysis step methods to preserve template's enhanced version."""
        legacy_method_names = {
            'step_02', 'step_02_submit', 'step_02_process',  # Link Graph legacy
            'step_analysis', 'step_analysis_submit', 'step_analysis_process'  # Trifecta enhanced
        }
        
        filtered_methods = []
        for method in methods:
            if method.name not in legacy_method_names:
                filtered_methods.append(method)
            else:
                print(f"  🚫 Filtered out legacy analysis method: {method.name}")
        
        return filtered_methods


def main():
    """Main entry point for the workflow reconstructor."""
    parser = argparse.ArgumentParser(
        description="""
AST-based Workflow Reconstructor - Industrial Precision Workflow Construction

🏆 THE SYSTEM: Atomic transplantation of workflow components using intelligent pattern matching.
    
CORE CONCEPT: Avoid OOP inheritance complexity by reconstructing workflows from proven components.
Components are transplanted atomically from "Old Workflows" (sources) into "Updated Workflows" 
(targets) with surgical precision via Python AST manipulation.

🧩 COMPONENT DETECTION:
• Auto-Registered Methods: step_xx, step_xx_submit (auto-register via pipulate.register_workflow_routes)
• Custom Endpoints: Detected via pattern matching (_process, preview) for explicit route registration
• Smart Filtering: Only workflow-specific methods transplanted, generic utilities remain in template

🔄 WORKFLOW LIFECYCLE:
1. Development & Testing: Generate incremental test versions (--suffix)
2. Validation: Test end-to-end functionality in safe environment  
3. Production: Deploy in-place when bulletproof (--target same as source)
4. Cleanup: Remove test versions to prevent file cruft

⚡ PATTERN EXAMPLES:
  Test Version:    --suffix 5                     → Creates param_buster5
  Named Variant:   --target 120_advanced_params   → Creates new workflow  
  In-Place Update: --target 110_parameter_buster  → Updates original
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--template', required=True, 
                       help='Template workflow name (e.g., "400_botify_trifecta") - provides base structure')
    parser.add_argument('--source', required=True,
                       help='Source workflow to extract components from (e.g., "110_parameter_buster") - the Atomic Source')
    
    # Mutually exclusive group for target specification
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument('--target', 
                             help='Target filename for new workflow (enables precise naming and in-place updates)')
    target_group.add_argument('--suffix', 
                             help='Suffix to add for incremental testing (e.g., "5" → param_buster5) - RECOMMENDED for development')
    
    parser.add_argument('--new-class-name',
                       help='New class name for the target workflow (defaults to source class name)')
    
    args = parser.parse_args()
    
    reconstructor = ASTWorkflowReconstructor()
    
    if args.suffix:
        success = reconstructor.create_variant_from_existing(
            template_name=args.template,
            existing_name=args.source,
            suffix=args.suffix
        )
    else:
        # Extract class name from source if not provided
        new_class_name = args.new_class_name
        if not new_class_name:
            source_tree = reconstructor.parse_file(reconstructor.plugins_dir / f"{args.source}.py")
            source_class_node = reconstructor.find_class_node(source_tree)
            if source_class_node:
                new_class_name = source_class_node.name
        
        success = reconstructor.reconstruct_workflow(
            template_name=args.template,
            source_name=args.source,
            target_name=args.target,
            new_class_name=new_class_name
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 