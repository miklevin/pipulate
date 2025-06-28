#!/usr/bin/env python3
"""
Pipulate Workflow Reconstructor - Python-based Template System
=============================================================

Replaces shell scripts with a sophisticated Python system that supports:
- Dry-run mode: Shows what would change without making changes
- In-place mode: Updates existing files to maintain git history
- New-file mode: Creates new files with versioned names
- Generic patterns: Support for filename patterns like adding "2" to existing workflows
- Reconstruction tracking: Adds counters to show template evolution

Usage:
    # Create new workflows from target definitions (original functionality)
    python workflow_reconstructor.py --template trifecta --target parameter_analyzer --mode dry-run
    python workflow_reconstructor.py --template trifecta --target parameter_analyzer --mode create
    
    # Create variants of existing workflows (NEW: generic pattern support)
    python workflow_reconstructor.py --template trifecta --existing 110_parameter_buster.py --suffix 2 --mode dry-run
    python workflow_reconstructor.py --template trifecta --existing 120_link_graph.py --suffix 2 --mode create
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class WorkflowReconstructor:
    """Manages workflow reconstruction with multiple modes and tracking."""
    
    def __init__(self, base_dir: str = "/home/mike/repos/pipulate"):
        self.base_dir = Path(base_dir)
        self.plugins_dir = self.base_dir / "plugins"
        self.helpers_dir = self.base_dir / "helpers" / "workflow"
        
        # Template mapping
        self.templates = {
            "trifecta": "400_botify_trifecta.py"
        }
        
        # Existing target definitions for completely new workflows (preserved for backward compatibility)
        self.target_definitions = {
            "parameter_analyzer": {
                "filename": "130_parameter_analyzer.py",
                "APP_NAME": "parameter_analyzer",
                "DISPLAY_NAME": "Parameter Analyzer 🔍",
                "class_name": "ParameterAnalyzer",
                "endpoint_message": "Deep dive into URL parameter analysis. Downloads Botify data and analyzes parameter patterns, wasteful tracking codes, and crawl budget optimization opportunities with detailed reports and robots.txt recommendations.",
                "steps": [
                    # === CHUNK 1: Common Trifecta Steps (standardized semantic naming) ===
                    "Step(id='step_project', done='botify_project', show='Botify Project URL', refill=True)",
                    "Step(id='step_analysis', done='analysis_selection', show='Download Non-Compliant Analysis', refill=False)",
                    "Step(id='step_webogs', done='weblogs_check', show='Download Web Logs', refill=False)",
                    "Step(id='step_gsc', done='search_console_check', show='Download Search Console', refill=False)",
                    # === CHUNK 2: Parameter-Specific Steps (target workflow functionality) ===
                    "Step(id='step_parameters', done='parameter_counting', show='Count Parameters by Source & Impact', refill=False)",
                    "Step(id='step_analysis_report', done='parameter_analysis', show='Analyze Parameter Value & Generate Report', refill=False)",
                    "Step(id='step_optimization', done='optimization_plan', show='Generate Optimization Instructions', refill=False)"
                ],
                "template_config": {
                    "analysis": "Not Compliant",
                    "crawler": "Crawl Basic", 
                    "gsc": "GSC Performance"
                }
            },
            "link_visualizer": {
                "filename": "140_link_visualizer.py",
                "APP_NAME": "link_visualizer",
                "DISPLAY_NAME": "Link Visualizer 📊",
                "class_name": "LinkVisualizer", 
                "endpoint_message": "Create interactive link graph visualizations from Botify data. Downloads link graph edges, node metadata, web logs for coloring, and Search Console data for sizing, then generates Cosmograph visualization URLs for immediate network analysis.",
                "steps": [
                    # === CHUNK 1: Common Trifecta Steps (standardized semantic naming) ===
                    "Step(id='step_project', done='botify_project', show='Botify Project URL', refill=True)",
                    "Step(id='step_analysis', done='analysis_selection', show='Download Link Graph Edges', refill=False)",
                    "Step(id='step_crawler', done='crawler_data', show='Download Node Metadata for Visualization', refill=False)",
                    "Step(id='step_webogs', done='weblogs_check', show='Download Web Logs for Node Coloring', refill=False)",
                    "Step(id='step_gsc', done='search_console_check', show='Download Search Console for Node Sizing', refill=False)",
                    # === CHUNK 2: Visualization-Specific Steps (target workflow functionality) ===
                    "Step(id='step_visualization', done='visualization_generation', show='Generate Interactive Visualization', refill=False)"
                ],
                "template_config": {
                    "analysis": "Link Graph Edges",
                    "crawler": "Crawl Basic",
                    "gsc": "GSC Performance"
                }
            }
        }
        
        # Reconstruction tracking patterns
        self.reconstruction_patterns = {
            'display_name': r'DISPLAY_NAME = [\'"]([^\'"]*)[\'"]',
            'app_name': r'APP_NAME = [\'"]([^\'"]*)[\'"]',
            'class_name': r'class (\w+):',
            'reconstruction_count': r'# RECONSTRUCTION_COUNT: (\d+)',
            'last_reconstructed': r'# LAST_RECONSTRUCTED: ([^\n]+)',
            'source_template': r'# SOURCE_TEMPLATE: ([^\n]+)'
        }

    def get_reconstruction_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract reconstruction metadata from a file."""
        metadata = {
            'reconstruction_count': '0',
            'last_reconstructed': 'Never',
            'source_template': 'Original'
        }
        
        if not file_path.exists():
            return metadata
            
        content = file_path.read_text()
        
        for key, pattern in self.reconstruction_patterns.items():
            if key == 'display_name':
                continue
            match = re.search(pattern, content)
            if match:
                metadata[key] = match.group(1)
                
        return metadata

    def update_reconstruction_metadata(self, content: str, template_name: str, existing_metadata: Optional[Dict[str, str]] = None) -> str:
        """Add or update reconstruction metadata in file content."""
        if existing_metadata is None:
            existing_metadata = {}
        
        # Increment reconstruction count from existing file
        current_count = existing_metadata.get('reconstruction_count', '0')
        count = int(current_count) + 1
        
        # Create metadata block
        metadata_block = f"""# RECONSTRUCTION METADATA
# ======================
# RECONSTRUCTION_COUNT: {count}
# LAST_RECONSTRUCTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# SOURCE_TEMPLATE: {template_name}
# Generated by workflow_reconstructor.py
"""
        
        # Find insertion point (after imports, before class definition)
        lines = content.split('\n')
        insert_index = 0
        
        # Find the best insertion point
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                insert_index = i
                break
            elif line.strip().startswith('ROLES = '):
                insert_index = i
                break
                
        # Remove any existing metadata block
        filtered_lines = []
        skip_next = False
        in_metadata_block = False
        
        for line in lines:
            if line.strip() == '# RECONSTRUCTION METADATA':
                in_metadata_block = True
                continue
            elif in_metadata_block and line.strip() == '':
                in_metadata_block = False
                continue
            elif in_metadata_block:
                continue
            else:
                filtered_lines.append(line)
        
        # Insert new metadata block
        filtered_lines.insert(insert_index, metadata_block)
        
        return '\n'.join(filtered_lines)

    def extract_metadata_from_content(self, content: str) -> Dict[str, str]:
        """Extract metadata from file content."""
        metadata = {
            'reconstruction_count': '0',
            'last_reconstructed': 'Never',
            'source_template': 'Original'
        }
        for key, pattern in self.reconstruction_patterns.items():
            if key == 'display_name':
                continue
            match = re.search(pattern, content)
            if match:
                metadata[key] = match.group(1)
        return metadata

    def add_reconstruction_indicator_to_display_name(self, content: str) -> str:
        """Add reconstruction count to DISPLAY_NAME for UI visibility."""
        # Extract current reconstruction count
        count_match = re.search(self.reconstruction_patterns['reconstruction_count'], content)
        count = int(count_match.group(1)) if count_match else 1
        
        # Find and modify DISPLAY_NAME
        display_pattern = self.reconstruction_patterns['display_name']
        
        def replace_display_name(match):
            current_name = match.group(1)
            # Remove any existing reconstruction indicator
            base_name = re.sub(r' \(R\d+\)$', '', current_name)
            # Add new reconstruction indicator
            return f"DISPLAY_NAME = '{base_name} (R{count})'"
        
        return re.sub(display_pattern, replace_display_name, content)

    def reconstruct_workflow(self, template_name: str, target_name: str, mode: str = 'dry-run') -> bool:
        """Reconstruct a workflow from template with specified mode."""
        
        # Validate inputs
        if template_name not in self.templates:
            print(f"❌ Unknown template: {template_name}")
            return False
            
        if target_name not in self.target_definitions:
            print(f"❌ Unknown target: {target_name}")
            print(f"Available targets: {list(self.target_definitions.keys())}")
            return False
            
        template_file = self.plugins_dir / self.templates[template_name]
        target_def = self.target_definitions[target_name]
        target_file = self.plugins_dir / target_def['filename']
        
        if not template_file.exists():
            print(f"❌ Template file not found: {template_file}")
            return False
            
        print(f"🔄 Creating NEW workflow: {target_name} from {template_name} template...")
        print(f"📁 Template: {template_file}")
        print(f"🎯 New Target: {target_file}")
        print(f"🆔 APP_NAME: {target_def['APP_NAME']}")
        print(f"🔧 Mode: {mode}")
        
        # Load template content
        template_content = template_file.read_text()
        
        # CRITICAL FIX: Remove the problematic API logging call that has pip.db.get bug
        # This mirrors how the working 120_link_graph.py has this call removed
        # Remove the entire log_api_call_details call that contains pip.db.get (including all parameters)
        problematic_pattern = r'await pip\.log_api_call_details\(\s*pipeline_id=pip\.db\.get.*?\n\s*\)'
        content = re.sub(problematic_pattern, '', template_content, flags=re.MULTILINE | re.DOTALL)
        
        # Apply transformations based on target definition
        transformed_content = self.apply_target_transformations(
            content, template_name, target_name
        )
        
        # Add creation metadata (not reconstruction since it's a new file)
        creation_metadata = f"""# NEW WORKFLOW CREATION METADATA
# ===============================
# CREATED_FROM_TEMPLATE: {template_name}
# CREATED_ON: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# TARGET_APP_NAME: {target_def['APP_NAME']}
# Generated by workflow_reconstructor.py as NEW workflow
"""
        
        # Find insertion point and add metadata
        lines = transformed_content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                insert_index = i
                break
        
        lines.insert(insert_index, creation_metadata)
        transformed_content = '\n'.join(lines)
        
        # Execute based on mode
        if mode == 'dry-run':
            return self.dry_run_preview_new_workflow(target_file, transformed_content, target_def)
        elif mode == 'create':
            return self.create_new_workflow(target_file, transformed_content, target_def)
        else:
            print(f"❌ Unknown mode for new workflow creation: {mode}")
            print(f"Available modes: dry-run, create")
            return False
    
    def reconstruct_from_existing(self, template_name: str, existing_filename: str, suffix: str, mode: str = 'dry-run') -> bool:
        """Reconstruct a workflow from an existing file with generic pattern support."""
        
        # Validate template
        if template_name not in self.templates:
            print(f"❌ Unknown template: {template_name}")
            return False
        
        # Resolve existing file path
        existing_file = self.plugins_dir / existing_filename
        if not existing_file.exists():
            print(f"❌ Existing workflow file not found: {existing_file}")
            return False
        
        # Generate new filename and paths
        new_filename = self.generate_filename_with_suffix(existing_filename, suffix)
        new_file = self.plugins_dir / new_filename
        template_file = self.plugins_dir / self.templates[template_name]
        
        if not template_file.exists():
            print(f"❌ Template file not found: {template_file}")
            return False
        
        # Extract information from existing workflow
        existing_info = self.extract_workflow_info(existing_file)
        
        print(f"🔄 Creating VARIANT workflow: {new_filename} from {existing_filename}...")
        print(f"📁 Template: {template_file}")
        print(f"📂 Existing: {existing_file}")
        print(f"🎯 New Target: {new_file}")
        print(f"🔧 Mode: {mode}")
        
        # Generate new identifiers with suffix
        if 'app_name' in existing_info:
            new_app_name = self.generate_app_name_with_suffix(existing_info['app_name'], suffix)
        else:
            # Fallback: derive from filename
            base_name = existing_filename.replace('.py', '').replace('_', '').replace(existing_filename.split('_')[0] + '_', '') if '_' in existing_filename else existing_filename.replace('.py', '')
            new_app_name = f"{base_name}{suffix}"
        
        if 'display_name' in existing_info:
            new_display_name = self.generate_display_name_with_suffix(existing_info['display_name'], suffix)
        else:
            new_display_name = f"Generated Workflow {suffix}"
        
        if 'class_name' in existing_info:
            new_class_name = self.generate_class_name_with_suffix(existing_info['class_name'], suffix)
        else:
            new_class_name = f"GeneratedWorkflow{suffix}"
        
        print(f"🆔 Original APP_NAME: {existing_info.get('app_name', 'Unknown')}")
        print(f"🆔 New APP_NAME: {new_app_name}")
        print(f"🏷️  Original DISPLAY_NAME: {existing_info.get('display_name', 'Unknown')}")
        print(f"🏷️  New DISPLAY_NAME: {new_display_name}")
        print(f"🏗️  Original Class: {existing_info.get('class_name', 'Unknown')}")
        print(f"🏗️  New Class: {new_class_name}")
        
        # Load template content
        template_content = template_file.read_text()
        
        # CRITICAL FIX: Remove the problematic API logging call that has pip.db.get bug
        problematic_pattern = r'await pip\.log_api_call_details\(\s*pipeline_id=pip\.db\.get.*?\n\s*\)'
        content = re.sub(problematic_pattern, '', template_content, flags=re.MULTILINE | re.DOTALL)
        
        # Create dynamic target definition from existing workflow info
        dynamic_target_def = {
            'filename': new_filename,
            'APP_NAME': new_app_name,
            'DISPLAY_NAME': new_display_name,
            'class_name': new_class_name,
            'endpoint_message': f"Variant workflow generated from {existing_filename} with template-compatible 2-chunk architecture.",
            'original_filename': existing_filename,
            'original_file_path': str(existing_file),  # CRITICAL: Enable 2-chunk architecture
            'suffix': suffix
        }
        
        # Apply transformations using the dynamic target definition
        transformed_content = self.apply_generic_transformations(
            content, template_name, dynamic_target_def
        )
        
        # Add variant creation metadata
        variant_metadata = f"""# VARIANT WORKFLOW CREATION METADATA
# ====================================
# CREATED_FROM_TEMPLATE: {template_name}
# ORIGINAL_WORKFLOW: {existing_filename}
# SUFFIX_APPLIED: {suffix}
# CREATED_ON: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# VARIANT_APP_NAME: {new_app_name}
# Generated by workflow_reconstructor.py as VARIANT workflow
"""
        
        # Find insertion point and add metadata
        lines = transformed_content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                insert_index = i
                break
        
        lines.insert(insert_index, variant_metadata)
        transformed_content = '\n'.join(lines)
        
        # Execute based on mode
        if mode == 'dry-run':
            return self.dry_run_preview_variant_workflow(new_file, transformed_content, dynamic_target_def)
        elif mode == 'create':
            return self.create_variant_workflow(new_file, transformed_content, dynamic_target_def)
        else:
            print(f"❌ Unknown mode for variant workflow creation: {mode}")
            print(f"Available modes: dry-run, create")
            return False

    def apply_target_transformations(self, content: str, template_name: str, target_name: str) -> str:
        """Apply target-specific transformations to template content."""
        
        if target_name not in self.target_definitions:
            print(f"⚠️  No target definition found for {target_name}, using template as-is")
            return content
            
        target_def = self.target_definitions[target_name]
        
        # Apply basic string replacements
        transformations = {
            'APP_NAME': target_def['APP_NAME'],
            'DISPLAY_NAME': target_def['DISPLAY_NAME'],
            'ENDPOINT_MESSAGE': target_def['endpoint_message'],
            'class_name': target_def['class_name']
        }
        
        for key, value in transformations.items():
            if key == 'class_name':
                # Replace class definition
                content = re.sub(
                    r'class \w+:',
                    f'class {value}:',
                    content
                )
            else:
                # Replace constant definitions - use double quotes to handle apostrophes
                pattern = f"{key.upper()} = ['\"][^'\"]*['\"]"
                replacement = f'{key.upper()} = "{value}"'
                content = re.sub(pattern, replacement, content)
        
        # Apply template config changes
        if 'template_config' in target_def:
            config_str = str(target_def['template_config']).replace("'", '"')
            content = re.sub(
                r'TEMPLATE_CONFIG = \{[^}]*\}',
                f'TEMPLATE_CONFIG = {config_str}',
                content,
                flags=re.MULTILINE | re.DOTALL
            )
        
        # COMPLETE replacement of _build_dynamic_steps method
        if 'steps' in target_def:
            steps_list = target_def['steps']
            
            # Build the new method content
            new_method = f'''    def _build_dynamic_steps(self):
        """Build the steps list for {target_def['DISPLAY_NAME']}.
        
        Returns:
            list: List of Step namedtuples for the workflow
            
        PURPOSE-SPECIFIC STEPS: This workflow is focused on {target_name.replace('_', ' ')} 
        and uses static, purpose-driven steps rather than dynamic template-based steps.
        """
        # Purpose-specific steps for {target_def['DISPLAY_NAME']}
        steps = [
'''
            
            for step in steps_list:
                new_method += f"            {step},\n"
            
            new_method += f'''        ]
        
        # Add finalize step
        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))
        
        # --- STEPS_LIST_INSERTION_POINT ---
        # CRITICAL: This static insertion point maintains compatibility with helper scripts
        
        return steps'''
            
            # Replace the entire _build_dynamic_steps method
            content = re.sub(
                r'    def _build_dynamic_steps\(self\):.*?return steps',
                new_method,
                content,
                flags=re.MULTILINE | re.DOTALL
            )
        
        return content
    
    def apply_generic_transformations(self, content: str, template_name: str, target_def: Dict) -> str:
        """Apply generic transformations and implement 2-chunk architecture atomic transplant."""
        
        print(f"🔄 Starting 2-chunk architecture reconstruction...")
        
        # Apply basic string replacements first
        transformations = {
            'APP_NAME': target_def['APP_NAME'],
            'DISPLAY_NAME': target_def['DISPLAY_NAME'],
            'ENDPOINT_MESSAGE': target_def['endpoint_message'],
            'class_name': target_def['class_name']
        }
        
        for key, value in transformations.items():
            if key == 'class_name':
                # CRITICAL FIX: Only replace the MAIN class definition (first one), not inner classes
                lines = content.split('\n')
                main_class_replaced = False
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('class ') and ':' in line and not main_class_replaced:
                        class_match = re.match(r'^(\s*class\s+)\w+(\s*:.*)$', line)
                        if class_match:
                            lines[i] = f'{class_match.group(1)}{value}{class_match.group(2)}'
                            main_class_replaced = True
                            break
                
                content = '\n'.join(lines)
            else:
                # Replace constant definitions - use double quotes to handle apostrophes
                pattern = f"{key.upper()} = ['\"][^'\"]*['\"]"
                replacement = f'{key.upper()} = "{value}"'
                content = re.sub(pattern, replacement, content)
        
        # NOW IMPLEMENT THE 2-CHUNK ARCHITECTURE ATOMIC TRANSPLANT
        if 'original_file_path' in target_def:
            content = self.implement_2_chunk_architecture(content, target_def)
        else:
            print(f"⚠️  No original file path provided - using template-only approach")
        
        print(f"✅ 2-chunk architecture reconstruction completed")
        return content

    def implement_2_chunk_architecture(self, template_content: str, target_def: Dict) -> str:
        """Implement the complete 2-chunk architecture by transplanting Chunk 2 from original workflow."""
        
        original_file_path = Path(target_def['original_file_path'])
        if not original_file_path.exists():
            print(f"❌ Original file not found: {original_file_path}")
            return template_content
            
        original_content = original_file_path.read_text()
        print(f"📖 Reading original workflow: {original_file_path}")
        
        # Extract Chunk 2 steps and methods from original workflow
        chunk2_steps, chunk2_methods = self.extract_chunk2_from_original(original_content)
        
        if not chunk2_steps and not chunk2_methods:
            print(f"ℹ️  No Chunk 2 found in original workflow - using template as-is")
            return template_content
            
        print(f"🧩 Found Chunk 2: {len(chunk2_steps)} steps, {len(chunk2_methods)} methods")
        
        # Insert Chunk 2 steps into template's step list 
        enhanced_content = self.insert_chunk2_steps(template_content, chunk2_steps)
        
        # Insert Chunk 2 methods into template's class
        enhanced_content = self.insert_chunk2_methods(enhanced_content, chunk2_methods)
        
        print(f"✅ 2-chunk architecture successfully implemented")
        return enhanced_content

    def extract_chunk2_from_original(self, original_content: str) -> tuple[list, list]:
        """Extract Chunk 2 steps and methods from original workflow."""
        
        # STEP 1: Find workflow-specific steps (exclude common trifecta steps)
        # Define patterns for common Chunk 1 steps (template steps that should be excluded)
        common_step_ids = {
            'step_project', 'step_analysis', 'step_crawler', 'step_webogs', 'step_gsc', 'finalize',
            # Also exclude numbered legacy steps
            'step_01', 'step_02', 'step_03', 'step_04', 'step_05'
        }
        
        chunk2_steps = []
        seen_steps = set()  # Prevent duplicates
        
        # Find all Step() definitions
        step_pattern = r"Step\(id='([^']+)'[^)]*\)"
        for match in re.finditer(step_pattern, original_content):
            step_line = match.group(0)
            step_id = match.group(1)
            
            # Skip if this is a common step or already seen
            if step_id not in common_step_ids and step_id not in seen_steps:
                chunk2_steps.append({
                    'step_id': step_id,
                    'step_definition': step_line,
                    'full_line': step_line
                })
                seen_steps.add(step_id)
                print(f"  📋 Found Chunk 2 step: {step_id}")
        
        # STEP 2: Find corresponding step methods  
        chunk2_methods = []
        seen_methods = set()  # Prevent duplicates
        
        for step_info in chunk2_steps:
            step_id = step_info['step_id']
            
            # Find all method variants for this step
            method_patterns = [
                f"async def {step_id}\\(",
                f"async def {step_id}_submit\\(",
                f"async def {step_id}_process\\(",
                f"async def {step_id}_complete\\("
            ]
            
            for pattern in method_patterns:
                method_match = re.search(pattern, original_content)
                if method_match:
                    method_name = method_match.group(0).split('(')[0].replace('async def ', '')
                    
                    # Skip if already seen
                    if method_name not in seen_methods:
                        # Extract the full method
                        method_content = self.extract_method_content(original_content, method_match.start())
                        if method_content:
                            chunk2_methods.append({
                                'method_name': method_name,
                                'method_content': method_content
                            })
                            seen_methods.add(method_name)
                            print(f"  🔧 Found Chunk 2 method: {method_name}")
        
        return chunk2_steps, chunk2_methods

    def extract_method_content(self, content: str, start_pos: int) -> str:
        """Extract complete method content including docstring and body."""
        
        lines = content[start_pos:].split('\n')
        method_lines = []
        indent_level = None
        in_method = False
        
        for line in lines:
            # First line is the method definition
            if not in_method:
                method_lines.append(line)
                in_method = True
                # Determine base indentation level
                stripped = line.lstrip()
                if stripped:
                    indent_level = len(line) - len(stripped)
                continue
            
            # Empty lines are always included
            if not line.strip():
                method_lines.append(line)
                continue
                
            # Check if we've hit the next method/class definition
            current_indent = len(line) - len(line.lstrip())
            
            # Method ends when we find a line at the same or lesser indentation that starts a new definition
            if (current_indent <= indent_level and 
                (line.strip().startswith('async def ') or 
                 line.strip().startswith('def ') or
                 line.strip().startswith('class '))):
                break
                
            method_lines.append(line)
        
        return '\n'.join(method_lines)

    def insert_chunk2_steps(self, template_content: str, chunk2_steps: list) -> str:
        """Insert Chunk 2 steps into template's step list."""
        
        if not chunk2_steps:
            return template_content
            
        print(f"🔗 Inserting {len(chunk2_steps)} Chunk 2 steps into template...")
        
        # Find the finalize step in template and insert Chunk 2 steps before it
        lines = template_content.split('\n')
        modified_lines = []
        inserted = False
        
        for line in lines:
            # Look for the finalize step insertion point
            if "Step(id='finalize'" in line and not inserted:
                # Insert Chunk 2 steps before finalize
                for step_info in chunk2_steps:
                    # Match the indentation of the current line
                    indent = len(line) - len(line.lstrip())
                    step_line = ' ' * indent + step_info['step_definition'] + ','
                    modified_lines.append(step_line)
                    print(f"  ➕ Inserted: {step_info['step_id']}")
                inserted = True
            
            modified_lines.append(line)
        
        return '\n'.join(modified_lines)

    def insert_chunk2_methods(self, template_content: str, chunk2_methods: list) -> str:
        """Insert Chunk 2 methods into template's class."""
        
        if not chunk2_methods:
            return template_content
            
        print(f"🔧 Inserting {len(chunk2_methods)} Chunk 2 methods into template...")
        
        # Find a good insertion point - typically before the last few utility methods
        insertion_point = self.find_method_insertion_point(template_content)
        
        if insertion_point == -1:
            print(f"⚠️  Could not find method insertion point - appending to end of class")
            # Fallback: append before the last closing brace/bracket
            lines = template_content.split('\n')
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() and not lines[i].strip().startswith('#'):
                    insertion_point = i
                    break
        
        # Insert the methods
        lines = template_content.split('\n')
        
        # Build method insertion block
        method_block = []
        method_block.append('')  # Empty line before methods
        method_block.append('    # --- CHUNK 2: WORKFLOW-SPECIFIC METHODS (TRANSPLANTED FROM ORIGINAL) ---')
        
        for method_info in chunk2_methods:
            method_block.append('')  # Empty line before each method
            method_content = method_info['method_content']
            method_block.extend(method_content.split('\n'))
            print(f"  ➕ Inserted method: {method_info['method_name']}")
        
        method_block.append('')  # Empty line after methods
        method_block.append('    # --- END CHUNK 2 ---')
        
        # Insert at the calculated point
        result_lines = lines[:insertion_point] + method_block + lines[insertion_point:]
        
        return '\n'.join(result_lines)

    def find_method_insertion_point(self, content: str) -> int:
        """Find the best place to insert Chunk 2 methods."""
        
        lines = content.split('\n')
        
        # Look for the designated insertion point marker
        for i, line in enumerate(lines):
            if '# --- STEP_METHODS_INSERTION_POINT ---' in line:
                return i
        
        # Fallback: look for the end of the class
        # Find the last line that starts with 'def ' or 'async def '
        last_method_line = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') or line.strip().startswith('async def '):
                last_method_line = i
        
        if last_method_line != -1:
            # Find the end of the last method by looking for the next non-indented line
            for i in range(last_method_line + 1, len(lines)):
                line = lines[i]
                if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                    return i
        
        # Ultimate fallback: insert near the end
        return len(lines) - 5 if len(lines) > 5 else max(0, len(lines) - 1)

    def dry_run_preview(self, target_file: Path, content: str) -> bool:
        """Show what would change in dry-run mode."""
        print(f"\n🔍 DRY RUN MODE - Preview of changes:")
        print(f"{'='*50}")
        
        if target_file.exists():
            current_metadata = self.get_reconstruction_metadata(target_file)
            print(f"📊 Current reconstruction count: {current_metadata['reconstruction_count']}")
            print(f"📅 Last reconstructed: {current_metadata['last_reconstructed']}")
            print(f"📋 Source template: {current_metadata['source_template']}")
        else:
            print(f"📁 Target file does not exist - would be created")
            
        # Extract new metadata
        new_metadata = self.extract_metadata_from_content(content)
        print(f"\n🔄 After reconstruction:")
        print(f"📊 New reconstruction count: {new_metadata.get('reconstruction_count', '1')}")
        print(f"📋 Source template: {new_metadata.get('source_template', 'Unknown')}")
        
        # Show display name change
        display_match = re.search(self.reconstruction_patterns['display_name'], content)
        if display_match:
            print(f"🏷️  New display name: {display_match.group(1)}")
            
        print(f"\n✅ Dry run completed - no files were modified")
        return True

    def in_place_update(self, target_file: Path, content: str) -> bool:
        """Update existing file in place to maintain git history."""
        print(f"\n🔄 IN-PLACE MODE - Updating existing file...")
        
        # Backup existing file if it exists
        if target_file.exists():
            backup_file = target_file.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(target_file, backup_file)
            print(f"💾 Backup created: {backup_file}")
        
        # Write new content
        target_file.write_text(content)
        print(f"✅ File updated in-place: {target_file}")
        
        # Show git status
        try:
            result = subprocess.run(['git', 'status', '--porcelain', str(target_file)], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            if result.stdout.strip():
                print(f"📝 Git status: {result.stdout.strip()}")
        except Exception as e:
            print(f"⚠️  Could not check git status: {e}")
            
        return True

    def new_file_creation(self, target_file: Path, content: str) -> bool:
        """Create new file with versioned name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_file = target_file.with_stem(f"{target_file.stem}_reconstructed_{timestamp}")
        
        print(f"\n📄 NEW-FILE MODE - Creating versioned file...")
        print(f"📁 New file: {new_file}")
        
        new_file.write_text(content)
        print(f"✅ New file created: {new_file}")
        
        return True

    def dry_run_preview_new_workflow(self, target_file: Path, content: str, target_def: dict) -> bool:
        """Show what would be created in dry-run mode for new workflow."""
        print(f"\n🔍 DRY RUN MODE - Preview of NEW workflow creation:")
        print(f"{'='*50}")
        
        if target_file.exists():
            print(f"⚠️  Target file already exists: {target_file}")
            print(f"❌ Would overwrite existing file!")
        else:
            print(f"✅ Target file does not exist - safe to create")
            
        print(f"\n🎯 New workflow details:")
        print(f"📁 Filename: {target_def['filename']}")
        print(f"🆔 APP_NAME: {target_def['APP_NAME']}")
        print(f"🏷️  DISPLAY_NAME: {target_def['DISPLAY_NAME']}")
        print(f"🏗️  Class: {target_def['class_name']}")
        print(f"📝 Steps count: {len(target_def['steps'])}")
        
        print(f"\n📋 Purpose-specific steps:")
        for i, step in enumerate(target_def['steps'], 1):
            # Extract the show value for display
            show_match = re.search(r"show='([^']*)'", step)
            show_text = show_match.group(1) if show_match else "Unknown"
            print(f"   {i:2d}. {show_text}")
            
        print(f"\n✅ Dry run completed - no files were created")
        return True

    def create_new_workflow(self, target_file: Path, content: str, target_def: dict) -> bool:
        """Create new workflow file."""
        print(f"\n🔄 CREATE MODE - Creating new workflow file...")
        
        if target_file.exists():
            print(f"⚠️  Target file already exists: {target_file}")
            response = input("Overwrite existing file? (y/N): ").lower().strip()
            if response != 'y':
                print(f"❌ Creation cancelled by user")
                return False
            
            # Backup existing file
            backup_file = target_file.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(target_file, backup_file)
            print(f"💾 Backup created: {backup_file}")
        
        # Write new content
        target_file.write_text(content)
        print(f"✅ New workflow created: {target_file}")
        print(f"🆔 APP_NAME: {target_def['APP_NAME']}")
        print(f"🏷️  DISPLAY_NAME: {target_def['DISPLAY_NAME']}")
        
        # Show git status
        try:
            result = subprocess.run(['git', 'status', '--porcelain', str(target_file)], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            if result.stdout.strip():
                print(f"📝 Git status: {result.stdout.strip()}")
        except Exception as e:
            print(f"⚠️  Could not check git status: {e}")
            
        return True

    def extract_workflow_info(self, file_path: Path) -> Dict[str, str]:
        """Extract workflow information from an existing file."""
        if not file_path.exists():
            return {}
            
        content = file_path.read_text()
        info = {}
        
        # Extract key information using patterns
        for key, pattern in self.reconstruction_patterns.items():
            match = re.search(pattern, content)
            if match:
                info[key] = match.group(1)
        
        return info
    
    def generate_filename_with_suffix(self, original_filename: str, suffix: str) -> str:
        """Generate a new filename with the specified suffix."""
        # Handle files like "110_parameter_buster.py" -> "110_parameter_buster2.py"
        if original_filename.endswith('.py'):
            base = original_filename[:-3]  # Remove .py
            return f"{base}{suffix}.py"
        return f"{original_filename}{suffix}"
    
    def generate_app_name_with_suffix(self, original_app_name: str, suffix: str) -> str:
        """Generate a new APP_NAME with the specified suffix."""
        return f"{original_app_name}{suffix}"
    
    def generate_display_name_with_suffix(self, original_display_name: str, suffix: str) -> str:
        """Generate a new DISPLAY_NAME with the specified suffix."""
        # Handle display names like "Parameter Buster 🔨" -> "Parameter Buster 2 🔨"
        # Split on emoji or special characters if present
        parts = original_display_name.split()
        if len(parts) > 1 and any(ord(char) > 127 for char in parts[-1]):  # Last part contains emoji
            emoji_part = parts[-1]
            name_parts = parts[:-1]
            return f"{' '.join(name_parts)} {suffix} {emoji_part}"
        else:
            return f"{original_display_name} {suffix}"
    
    def generate_class_name_with_suffix(self, original_class_name: str, suffix: str) -> str:
        """Generate a new class name with the specified suffix."""
        return f"{original_class_name}{suffix}"

    def dry_run_preview_variant_workflow(self, target_file: Path, content: str, target_def: dict) -> bool:
        """Show what would be created in dry-run mode for variant workflow."""
        print(f"\n🔍 DRY RUN MODE - Preview of VARIANT workflow creation:")
        print(f"{'='*50}")
        
        if target_file.exists():
            print(f"⚠️  Target file already exists: {target_file}")
            print(f"❌ Would overwrite existing file!")
        else:
            print(f"✅ Target file does not exist - safe to create")
            
        print(f"\n🎯 Variant workflow details:")
        print(f"📁 Filename: {target_def['filename']}")
        print(f"📂 Original: {target_def['original_filename']}")
        print(f"🔤 Suffix: {target_def['suffix']}")
        print(f"🆔 APP_NAME: {target_def['APP_NAME']}")
        print(f"🏷️  DISPLAY_NAME: {target_def['DISPLAY_NAME']}")
        print(f"🏗️  Class: {target_def['class_name']}")
        
        print(f"\n📋 Template-based 2-chunk architecture:")
        print(f"   ✅ CHUNK 1: Common Trifecta Steps (template-compatible)")
        print(f"   ✅ CHUNK 2: Workflow-specific functionality (preserved from original)")
        
        print(f"\n✅ Dry run completed - no files were created")
        return True

    def create_variant_workflow(self, target_file: Path, content: str, target_def: dict) -> bool:
        """Create variant workflow file."""
        print(f"\n🔄 CREATE MODE - Creating variant workflow file...")
        
        if target_file.exists():
            print(f"⚠️  Target file already exists: {target_file}")
            response = input("Overwrite existing file? (y/N): ").lower().strip()
            if response != 'y':
                print(f"❌ Creation cancelled by user")
                return False
            
            # Backup existing file
            backup_file = target_file.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(target_file, backup_file)
            print(f"💾 Backup created: {backup_file}")
        
        # Write new content
        target_file.write_text(content)
        print(f"✅ Variant workflow created: {target_file}")
        print(f"📂 Original: {target_def['original_filename']}")
        print(f"🔤 Suffix: {target_def['suffix']}")
        print(f"🆔 APP_NAME: {target_def['APP_NAME']}")
        print(f"🏷️  DISPLAY_NAME: {target_def['DISPLAY_NAME']}")
        
        # Show git status
        try:
            result = subprocess.run(['git', 'status', '--porcelain', str(target_file)], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            if result.stdout.strip():
                print(f"📝 Git status: {result.stdout.strip()}")
        except Exception as e:
            print(f"⚠️  Could not check git status: {e}")
            
        return True


def main():
    parser = argparse.ArgumentParser(description='Pipulate Workflow Reconstructor - Create workflows from templates')
    parser.add_argument('--template', required=True, 
                       choices=['trifecta'],
                       help='Template to use as source (currently only trifecta supported)')
    
    # Support two modes: new workflows from target definitions OR variants from existing files
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--target',
                       choices=['parameter_analyzer', 'link_visualizer'], 
                       help='Target workflow to create (completely new, non-colliding workflows)')
    group.add_argument('--existing',
                       help='Existing workflow file to create a variant from (e.g., 110_parameter_buster.py)')
    
    parser.add_argument('--suffix', 
                       help='Suffix to append to existing workflow (required with --existing, e.g., "2")')
    parser.add_argument('--mode', default='dry-run',
                       choices=['dry-run', 'create'],
                       help='Creation mode: dry-run (preview) or create (actually generate files)')
    parser.add_argument('--base-dir', default='/home/mike/repos/pipulate',
                       help='Base directory for pipulate project')
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.existing and not args.suffix:
        parser.error("--suffix is required when using --existing")
    if args.target and args.suffix:
        parser.error("--suffix cannot be used with --target (predefined workflows)")
    
    reconstructor = WorkflowReconstructor(args.base_dir)
    
    if args.target:
        # Original functionality: create new workflow from target definition
        print(f"🏗️  WORKFLOW CREATOR - Creating {args.target} from {args.template}")
        print(f"🎯 This creates a NEW workflow with different APP_NAME to avoid collisions")
        print(f"🔧 Mode: {args.mode}")
        print(f"{'='*70}")
        
        success = reconstructor.reconstruct_workflow(args.template, args.target, args.mode)
        
        if success:
            if args.mode == 'dry-run':
                print(f"\n🎉 Dry run completed successfully!")
                print(f"💡 To actually create the workflow, run with --mode create")
            else:
                print(f"\n🎉 New workflow creation completed successfully!")
                print(f"🚀 You can now test the new {args.target} workflow")
        else:
            print(f"\n❌ Workflow creation failed!")
            sys.exit(1)
    
    elif args.existing:
        # New functionality: create variant from existing workflow
        print(f"🔄 VARIANT CREATOR - Creating {args.existing}{args.suffix} from {args.existing}")
        print(f"🎯 This creates a VARIANT workflow with template-compatible 2-chunk architecture")
        print(f"📂 Original: {args.existing}")
        print(f"🔤 Suffix: {args.suffix}")
        print(f"🔧 Mode: {args.mode}")
        print(f"{'='*70}")
        
        success = reconstructor.reconstruct_from_existing(args.template, args.existing, args.suffix, args.mode)
        
        if success:
            if args.mode == 'dry-run':
                print(f"\n🎉 Dry run completed successfully!")
                print(f"💡 To actually create the variant, run with --mode create")
            else:
                print(f"\n🎉 Variant workflow creation completed successfully!")
                print(f"🚀 You can now test the new {args.existing}{args.suffix} workflow")
        else:
            print(f"\n❌ Variant creation failed!")
            sys.exit(1)


if __name__ == '__main__':
    main() 