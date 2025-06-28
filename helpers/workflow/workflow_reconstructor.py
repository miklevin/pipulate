#!/usr/bin/env python3
"""
Pipulate Workflow Reconstructor - Python-based Template System
=============================================================

Replaces shell scripts with a sophisticated Python system that supports:
- Dry-run mode: Shows what would change without making changes
- In-place mode: Updates existing files to maintain git history
- New-file mode: Creates new files with versioned names
- Reconstruction tracking: Adds counters to show template evolution

Usage:
    python workflow_reconstructor.py --template trifecta --target parameter_buster --mode dry-run
    python workflow_reconstructor.py --template trifecta --target parameter_buster --mode in-place
    python workflow_reconstructor.py --template trifecta --target link_graph --mode new-file
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
        
        # NEW: Target definitions for completely new workflows
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


def main():
    parser = argparse.ArgumentParser(description='Pipulate Workflow Creator - Create NEW workflows from templates')
    parser.add_argument('--template', required=True, 
                       choices=['trifecta'],
                       help='Template to use as source (currently only trifecta supported)')
    parser.add_argument('--target', required=True,
                       choices=['parameter_analyzer', 'link_visualizer'], 
                       help='Target workflow to create (completely new, non-colliding workflows)')
    parser.add_argument('--mode', default='dry-run',
                       choices=['dry-run', 'create'],
                       help='Creation mode: dry-run (preview) or create (actually generate files)')
    parser.add_argument('--base-dir', default='/home/mike/repos/pipulate',
                       help='Base directory for pipulate project')
    
    args = parser.parse_args()
    
    reconstructor = WorkflowReconstructor(args.base_dir)
    
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


if __name__ == '__main__':
    main() 