#!/usr/bin/env python3
"""
Execute Surgery - Direct Surgical Extraction Tool

This script performs the actual surgical extraction of server.py
based on the analysis from the surgical planning tools.
"""

import os
import sys
import ast
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Import our surgical analysis tools
from ast_analyzer import ASTAnalyzer
from surgical_execution_engine import SurgicalExecutionEngine

def backup_server_file(backup_dir: Path) -> None:
    """Create a backup of the original server.py"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2("server.py", backup_dir / "server.py.backup")
    print(f"📄 Backed up server.py to {backup_dir / 'server.py.backup'}")

def extract_code_blocks(server_file: str, block_ids: List[str]) -> Dict[str, str]:
    """Extract code blocks from server.py by their block IDs"""
    analyzer = ASTAnalyzer()
    analysis = analyzer.analyze_file(server_file)
    
    extracted_blocks = {}
    
    for block in analysis.blocks:
        if block.block_id in block_ids:
            extracted_blocks[block.block_id] = block.source_code
    
    return extracted_blocks

def create_target_file(filename: str, blocks: Dict[str, str], imports: List[str] = None) -> None:
    """Create a target file with the extracted blocks"""
    print(f"📝 Creating {filename}")
    
    with open(filename, 'w') as f:
        # Write header
        f.write(f'#!/usr/bin/env python3\n')
        f.write(f'"""\n')
        f.write(f'{filename} - Extracted from server.py\n')
        f.write(f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'"""\n\n')
        
        # Write imports if provided
        if imports:
            for import_line in imports:
                f.write(f'{import_line}\n')
            f.write('\n')
        
        # Write the extracted blocks
        for block_id, block_code in blocks.items():
            f.write(f'# Extracted block: {block_id}\n')
            f.write(block_code)
            f.write('\n\n')

def remove_blocks_from_server(server_file: str, block_ids: List[str]) -> None:
    """Remove extracted blocks from server.py"""
    analyzer = ASTAnalyzer()
    analysis = analyzer.analyze_file(server_file)
    
    # Read original file
    with open(server_file, 'r') as f:
        lines = f.readlines()
    
    # Mark lines to remove
    lines_to_remove = set()
    for block in analysis.blocks:
        if block.block_id in block_ids:
            # Remove lines from start_line to end_line (1-indexed)
            for line_num in range(block.start_line, block.end_line + 1):
                lines_to_remove.add(line_num - 1)  # Convert to 0-indexed
    
    # Create new content without removed lines
    new_lines = []
    for i, line in enumerate(lines):
        if i not in lines_to_remove:
            new_lines.append(line)
    
    # Write back to server.py
    with open(server_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"🔪 Removed {len(lines_to_remove)} lines from {server_file}")

def perform_surgery() -> None:
    """Perform the actual surgical extraction"""
    
    print("🏥 PERFORMING SURGICAL EXTRACTION")
    print("=" * 50)
    
    # Create backup
    backup_dir = Path(f"/tmp/surgery_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_server_file(backup_dir)
    
    # Define extraction plan based on surgical analysis
    extraction_plan = {
        'database.py': {
            'blocks': ['function_get_db_filename_0484', 'function_db_operation_3798', 'class_dictlikedb_3821'],
            'imports': [
                'import sqlite3',
                'import functools',
                'from typing import Any, Dict, Optional'
            ]
        },
        'logging_utils.py': {
            'blocks': ['class_debugconsole_0111', 'function_rich_json_display_0126', 'function_setup_logging_0225'],
            'imports': [
                'import logging',
                'from rich.console import Console',
                'from rich.table import Table',
                'from rich.json import JSON',
                'from pathlib import Path'
            ]
        },
        'plugin_system.py': {
            'blocks': ['function_discover_plugin_files_4054', 'function_find_plugin_classes_4102'],
            'imports': [
                'import os',
                'import sys',
                'import importlib.util',
                'from pathlib import Path',
                'from typing import List, Dict, Any'
            ]
        },
        'pipeline.py': {
            'blocks': ['class_pipulate_1675', 'assignment_pipulate_3718'],
            'imports': [
                'import asyncio',
                'import functools',
                'from typing import Optional, Dict, Any, List',
                'from dataclasses import dataclass',
                'from datetime import datetime'
            ]
        }
    }
    
    # Extract all blocks that will be moved
    all_block_ids = []
    for file_info in extraction_plan.values():
        all_block_ids.extend(file_info['blocks'])
    
    print(f"🔍 Extracting {len(all_block_ids)} blocks from server.py")
    extracted_blocks = extract_code_blocks("server.py", all_block_ids)
    
    # Create target files
    for target_file, file_info in extraction_plan.items():
        file_blocks = {block_id: extracted_blocks[block_id] 
                      for block_id in file_info['blocks'] 
                      if block_id in extracted_blocks}
        
        if file_blocks:
            create_target_file(target_file, file_blocks, file_info['imports'])
    
    # Remove extracted blocks from server.py
    successfully_extracted = [block_id for block_id in all_block_ids if block_id in extracted_blocks]
    if successfully_extracted:
        remove_blocks_from_server("server.py", successfully_extracted)
    
    print(f"✅ SURGICAL EXTRACTION COMPLETE")
    print(f"   Backup location: {backup_dir}")
    print(f"   Files created: {len(extraction_plan)}")
    print(f"   Blocks extracted: {len(successfully_extracted)}")

def main():
    """Main execution function"""
    if not Path("server.py").exists():
        print("❌ ERROR: server.py not found. Must run from pipulate directory.")
        sys.exit(1)
    
    try:
        perform_surgery()
    except Exception as e:
        print(f"🚨 SURGICAL EXTRACTION FAILED: {e}")
        raise

if __name__ == "__main__":
    main() 