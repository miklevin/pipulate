#!/usr/bin/env python3
"""
Server Refactor Demo - Practical Example of Code Surgery

This script demonstrates how to use the code surgery tools to refactor
server.py into smaller, more manageable files as discussed.

Target structure:
- server.py (~17K tokens) - Core app setup and initialization
- pipeline.py (~20K tokens) - Pipulate class and workflow coordination
- routes.py (~20K tokens) - HTTP endpoint handlers
- plugin_system.py (~8K tokens) - Plugin discovery and management
- logging_utils.py (~5K tokens) - Logging and display utilities
- database.py (~3K tokens) - Database operations
- common.py (~4K tokens) - CRUD base class (existing)
- mcp_tools.py (~52K tokens) - AI assistant interface (existing)

Total: ~129K tokens (perfect for the 130K target)
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# Add the code_surgery directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from ast_analyzer import ASTAnalyzer
from code_slicer import CodeSlicer, RefactoringPlan
from dependency_tracker import DependencyTracker

class ServerRefactorPlanner:
    """Plans the refactoring of server.py into multiple focused files."""
    
    def __init__(self, server_file: str = "server.py"):
        self.server_file = server_file
        self.analyzer = ASTAnalyzer()
        self.slicer = CodeSlicer()
        self.dependency_tracker = DependencyTracker()
        
    def analyze_server_structure(self):
        """Analyze server.py to understand its current structure."""
        print("🔍 Analyzing server.py structure...")
        
        analysis = self.analyzer.analyze_file(self.server_file)
        
        print(f"Found {len(analysis.blocks)} code blocks:")
        
        # Categorize blocks by type and purpose
        categories = {
            'imports': [],
            'utilities': [],
            'classes': [],
            'endpoints': [],
            'setup': []
        }
        
        for block in analysis.blocks:
            if block.block_type == 'import':
                categories['imports'].append(block)
            elif block.block_type == 'function':
                if any(decorator.startswith('rt(') or decorator.startswith('@app.') for decorator in block.decorators):
                    categories['endpoints'].append(block)
                elif block.name in ['setup_logging', 'print_and_log_table', 'rich_json_display']:
                    categories['utilities'].append(block)
                else:
                    categories['setup'].append(block)
            elif block.block_type == 'class':
                categories['classes'].append(block)
            else:
                categories['setup'].append(block)
        
        # Print categorization
        for category, blocks in categories.items():
            print(f"\n{category.upper()} ({len(blocks)} blocks):")
            for block in blocks[:5]:  # Show first 5
                print(f"  - {block.name} (lines {block.start_line}-{block.end_line})")
            if len(blocks) > 5:
                print(f"  ... and {len(blocks) - 5} more")
        
        return analysis, categories
    
    def create_refactoring_map(self, categories: Dict[str, List]) -> Dict[str, str]:
        """Create a mapping of blocks to target files."""
        
        refactor_map = {}
        
        # Define target files and their purposes
        target_files = {
            'pipeline.py': ['Pipulate', 'OrderedMessageQueue'],
            'routes.py': [],  # Will contain endpoint functions
            'plugin_system.py': ['discover_plugin_files', 'find_plugin_classes', 'register_plugin_endpoint'],
            'logging_utils.py': ['setup_logging', 'print_and_log_table', 'rich_json_display', 'rich_dict_display'],
            'database.py': ['DictLikeDB', 'db_operation', 'populate_initial_data'],
            'server.py': []  # Core server setup will remain
        }
        
        # Map blocks to files based on names and types
        for category, blocks in categories.items():
            for block in blocks:
                target_file = self._determine_target_file(block, target_files)
                refactor_map[block.block_id] = target_file
        
        return refactor_map
    
    def _determine_target_file(self, block, target_files) -> str:
        """Determine which file a block should go to."""
        
        # Check for specific class/function names
        for target_file, names in target_files.items():
            if block.name in names:
                return target_file
        
        # Route endpoints go to routes.py
        if any(decorator.startswith('rt(') or decorator.startswith('@app.') for decorator in block.decorators):
            return 'routes.py'
        
        # Plugin-related functions
        if 'plugin' in block.name.lower() or 'menu' in block.name.lower():
            return 'plugin_system.py'
        
        # Logging and display functions
        if any(word in block.name.lower() for word in ['log', 'print', 'rich', 'display']):
            return 'logging_utils.py'
        
        # Database operations
        if any(word in block.name.lower() for word in ['db', 'database', 'store', 'populate']):
            return 'database.py'
        
        # Large classes go to their own files
        if block.block_type == 'class':
            if block.name == 'Pipulate':
                return 'pipeline.py'
            elif 'DB' in block.name or 'Database' in block.name:
                return 'database.py'
        
        # Everything else stays in server.py
        return 'server.py'
    
    def create_detailed_plan(self) -> RefactoringPlan:
        """Create a detailed refactoring plan."""
        
        # Analyze current structure
        analysis, categories = self.analyze_server_structure()
        
        # Create block mapping
        refactor_map = self.create_refactoring_map(categories)
        
        # Print the plan
        print("\n📋 REFACTORING PLAN")
        print("=" * 50)
        
        target_files = set(refactor_map.values())
        for target_file in sorted(target_files):
            blocks_for_file = [bid for bid, tfile in refactor_map.items() if tfile == target_file]
            print(f"\n{target_file}: {len(blocks_for_file)} blocks")
            
            # Show some examples
            for block_id in blocks_for_file[:3]:
                block = next(b for b in analysis.blocks if b.block_id == block_id)
                print(f"  - {block.name} ({block.block_type})")
            
            if len(blocks_for_file) > 3:
                print(f"  ... and {len(blocks_for_file) - 3} more")
        
        # Create the actual refactoring plan
        target_file_list = [f for f in target_files if f != 'server.py']
        
        plan = self.slicer.create_refactoring_plan(
            self.server_file,
            target_file_list,
            refactor_map
        )
        
        return plan
    
    def validate_plan(self, plan: RefactoringPlan) -> List[str]:
        """Validate the refactoring plan for safety."""
        print("\n🔍 VALIDATING REFACTORING PLAN")
        print("=" * 40)
        
        # Analyze all files that will be involved
        all_files = list(set(plan.source_files + plan.target_files))
        existing_files = [f for f in all_files if Path(f).exists()]
        
        if existing_files:
            self.dependency_tracker.analyze_project(existing_files)
        
        # Check for issues
        warnings = self.dependency_tracker.validate_refactoring_safety(plan.operations)
        
        if warnings:
            print("⚠️  WARNINGS FOUND:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("✅ No validation warnings found")
        
        # Check import requirements
        import_updates = self.dependency_tracker.calculate_import_updates(plan.operations)
        
        if import_updates:
            print("\n📦 IMPORT UPDATES NEEDED:")
            for file_path, updates in import_updates.items():
                print(f"  {file_path}:")
                for update in updates[:3]:  # Show first 3
                    print(f"    - {update}")
                if len(updates) > 3:
                    print(f"    ... and {len(updates) - 3} more")
        
        return warnings

def main():
    """Demonstrate the server refactoring process."""
    
    print("🚀 SERVER.PY REFACTORING DEMONSTRATION")
    print("=" * 60)
    
    # Check if server.py exists
    server_file = "server.py"
    if not Path(server_file).exists():
        # Try relative to script location
        script_dir = Path(__file__).parent.parent.parent
        server_file = script_dir / "server.py"
        
        if not server_file.exists():
            print(f"❌ Could not find server.py")
            print(f"Looked in: {Path.cwd()} and {script_dir}")
            return
    
    # Create the planner
    planner = ServerRefactorPlanner(str(server_file))
    
    try:
        # Step 1: Analyze current structure
        analysis, categories = planner.analyze_server_structure()
        
        # Step 2: Create refactoring plan
        plan = planner.create_detailed_plan()
        
        # Step 3: Validate the plan
        warnings = planner.validate_plan(plan)
        
        # Step 4: Save the plan
        plan_file = Path("/tmp/code_surgery/plans") / f"{plan.plan_id}.json"
        plan_file.parent.mkdir(parents=True, exist_ok=True)
        plan.save_to_file(str(plan_file))
        
        print(f"\n💾 Plan saved to: {plan_file}")
        
        # Step 5: Show next steps
        print("\n🎯 NEXT STEPS:")
        print("1. Review the plan file and adjust block mappings if needed")
        print("2. Run: python code_slicer.py execute <plan_file>")
        print("3. Test the refactored code")
        print("4. If issues occur: python code_slicer.py rollback <plan_file>")
        
        if warnings:
            print("\n⚠️  Address the validation warnings before executing!")
        else:
            print("\n✅ Plan looks good - ready for execution!")
            
    except Exception as e:
        print(f"❌ Error during planning: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 