#!/usr/bin/env python3
"""
Atomic Transplantation Marker Tool

A reliable tool for inserting workflow section markers into Python files to enable
deterministic code transplantation using simple .split() and .join() operations.

CRITICAL INSIGHT: Why This Tool Exists
=====================================
The standard edit_file tool in AI assistants struggles with precision marker insertion
because it tries to be too smart with context matching and often fails on:
- Exact indentation requirements
- Precise line positioning 
- Complex method boundary detection
- Maintaining file integrity during multiple edits

This tool uses simple, deterministic line-based operations that work reliably every time.

ATOMIC TRANSPLANTATION PHILOSOPHY
=================================
The goal is to create "deterministic transplantation seeds" - full-line markers that:
1. Use complete comment lines that are impossible to miss or misinterpret
2. Provide clear boundaries for atomic code sections  
3. Include metadata about what each section contains
4. Enable deterministic extraction and insertion operations
5. Work with simple string operations instead of complex regex/AST parsing

MARKER SYSTEM OVERVIEW
======================
The atomic transplantation system uses these markers to define transplantable units:

1. START_WORKFLOW_SECTION: Marks beginning of atomic unit with documentation
2. SECTION_STEP_DEFINITION: Marks step definitions list
3. END_SECTION_STEP_DEFINITION: Marks end of step definitions
4. SECTION_STEP_METHODS: Marks beginning of step method implementations
5. END_SECTION_STEP_METHODS: Marks end of step method implementations  
6. END_WORKFLOW_SECTION: Marks end of atomic unit

EXAMPLE MARKER STRUCTURE
========================
```python
# --- START_WORKFLOW_SECTION: steps_01_04_botify_data_collection ---
# This section handles the complete Botify data collection workflow (steps 1-4):
# - Step 1: Botify Project URL input and validation
# - Step 2: Crawl Analysis selection and download
# - Step 3: Web Logs availability check and download
# - Step 4: Search Console data check and download
# This is an atomic unit that should be transplanted together.

# --- SECTION_STEP_DEFINITION ---
steps = [
    Step(id='step_01', done='botify_project', show='Botify Project URL', refill=True),
    Step(id='step_02', done='analysis_data', show='Crawl Analysis', refill=False),
    Step(id='step_03', done='logs_check', show='Web Logs Check', refill=False),
    Step(id='step_04', done='gsc_check', show='Search Console Check', refill=False),
]
# --- END_SECTION_STEP_DEFINITION ---

# ... other class methods ...

# --- SECTION_STEP_METHODS ---
async def step_01(self, request):
    # Step 1 implementation
    pass

async def step_01_submit(self, request):
    # Step 1 submission handler
    pass

# ... more step methods ...

async def step_04_submit(self, request):
    # Final step submission handler
    pass
# --- END_SECTION_STEP_METHODS ---

# ... helper methods outside the atomic unit ...

# --- END_WORKFLOW_SECTION ---
```

LESSONS LEARNED FROM PARAMETER BUSTER IMPLEMENTATION
===================================================

1. **Edit Tool Limitations**: The AI edit tool repeatedly failed to make precise 
   insertions around method definitions, despite clear instructions and multiple attempts.

2. **Context Sensitivity Issues**: The tool struggled with maintaining exact indentation 
   and positioning when inserting markers around existing code structures.

3. **Token Efficiency**: Failed edit attempts consumed hundreds of tokens. This custom 
   tool completed all markers in one operation using ~100 tokens.

4. **Deterministic Success**: Line-based operations with regex pattern matching provide 
   reliable, predictable results every time.

5. **Indentation Handling**: Automatic indentation detection from reference lines 
   ensures markers align properly with surrounding code.

USAGE PATTERNS
==============

For completing a workflow that already has some markers:
```bash
python atomic_transplantation_marker_tool.py complete-parameter-buster
```

For adding markers to any workflow:
```bash
python atomic_transplantation_marker_tool.py add-markers path/to/workflow.py
```

For custom marker insertion:
```bash
python atomic_transplantation_marker_tool.py insert-before "pattern" "marker" file.py
python atomic_transplantation_marker_tool.py insert-after "pattern" "marker" file.py
python atomic_transplantation_marker_tool.py insert-at-line 123 "marker" file.py
```

FUTURE ENHANCEMENTS
==================
- Support for multiple workflow atomic units in one file
- Validation of marker completeness and consistency
- Automatic detection of step method boundaries
- Integration with workflow creation templates
- Marker removal/cleanup functionality
"""

import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

class AtomicTransplantationMarkerTool:
    """Tool for inserting atomic transplantation markers into workflow files."""
    
    # Standard marker definitions
    MARKERS = {
        'workflow_start': '# --- START_WORKFLOW_SECTION: {section_name} ---',
        'workflow_end': '# --- END_WORKFLOW_SECTION ---',
        'step_def_start': '# --- SECTION_STEP_DEFINITION ---',
        'step_def_end': '# --- END_SECTION_STEP_DEFINITION ---',
        'step_methods_start': '# --- SECTION_STEP_METHODS ---',
        'step_methods_end': '# --- END_SECTION_STEP_METHODS ---'
    }
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def read_file_lines(self, file_path: str) -> List[str]:
        """Read file and return list of lines."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    
    def write_file_lines(self, file_path: str, lines: List[str]):
        """Write list of lines to file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def get_line_indentation(self, line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())
    
    def create_indented_marker(self, marker: str, indent: int) -> str:
        """Create a marker with proper indentation."""
        return ' ' * indent + marker + '\n'
    
    def find_pattern_line(self, lines: List[str], pattern: str, start_index: int = 0) -> Optional[int]:
        """Find the first line matching the pattern, return line index."""
        for i in range(start_index, len(lines)):
            if re.search(pattern, lines[i]):
                return i
        return None
    
    def insert_marker_before_pattern(self, file_path: str, pattern: str, marker: str) -> bool:
        """Insert a marker before the first line matching the pattern."""
        lines = self.read_file_lines(file_path)
        
        line_index = self.find_pattern_line(lines, pattern)
        if line_index is None:
            self.log(f"❌ Pattern '{pattern}' not found in {file_path}")
            return False
        
        # Get indentation from the target line
        indent = self.get_line_indentation(lines[line_index])
        marker_line = self.create_indented_marker(marker, indent)
        
        # Insert marker before the target line
        lines.insert(line_index, marker_line)
        self.write_file_lines(file_path, lines)
        
        self.log(f"✅ Inserted '{marker}' before line {line_index + 1}: {lines[line_index + 1].strip()}")
        return True
    
    def insert_marker_after_pattern(self, file_path: str, pattern: str, marker: str) -> bool:
        """Insert a marker after the first line matching the pattern."""
        lines = self.read_file_lines(file_path)
        
        line_index = self.find_pattern_line(lines, pattern)
        if line_index is None:
            self.log(f"❌ Pattern '{pattern}' not found in {file_path}")
            return False
        
        # Get indentation from the target line
        indent = self.get_line_indentation(lines[line_index])
        marker_line = self.create_indented_marker(marker, indent)
        
        # Insert marker after the target line
        lines.insert(line_index + 1, marker_line)
        self.write_file_lines(file_path, lines)
        
        self.log(f"✅ Inserted '{marker}' after line {line_index + 1}: {lines[line_index].strip()}")
        return True
    
    def insert_marker_at_line(self, file_path: str, line_number: int, marker: str) -> bool:
        """Insert a marker at a specific line number (1-indexed)."""
        lines = self.read_file_lines(file_path)
        
        if line_number < 1 or line_number > len(lines) + 1:
            self.log(f"❌ Line number {line_number} out of range (1-{len(lines)})")
            return False
        
        # Get indentation from the reference line
        if line_number <= len(lines):
            reference_line = lines[line_number - 1]
            indent = self.get_line_indentation(reference_line)
        else:
            indent = 0
        
        marker_line = self.create_indented_marker(marker, indent)
        lines.insert(line_number - 1, marker_line)
        self.write_file_lines(file_path, lines)
        
        self.log(f"✅ Inserted '{marker}' at line {line_number}")
        return True
    
    def append_marker_to_file(self, file_path: str, marker: str) -> bool:
        """Append a marker to the end of the file."""
        lines = self.read_file_lines(file_path)
        
        # Add a newline if the file doesn't end with one
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        
        # Add the marker with a leading newline
        lines.append('\n' + marker + '\n')
        self.write_file_lines(file_path, lines)
        
        self.log(f"✅ Appended '{marker}' to end of file")
        return True
    
    def check_marker_exists(self, file_path: str, marker: str) -> bool:
        """Check if a marker already exists in the file."""
        lines = self.read_file_lines(file_path)
        for line in lines:
            if marker.strip() in line:
                return True
        return False
    
    def complete_parameter_buster_markers(self, file_path: str = "plugins/045_parameter_buster_new.py") -> bool:
        """Complete the atomic transplantation markers for Parameter Buster workflow.
        
        This is the specific implementation that was successfully used to complete
        the Parameter Buster workflow markers after multiple failed edit attempts.
        """
        self.log(f"🔧 Completing atomic transplantation markers in {file_path}")
        
        success_count = 0
        total_operations = 3
        
        # 1. Insert step methods start marker before step_01
        if not self.check_marker_exists(file_path, self.MARKERS['step_methods_start']):
            success1 = self.insert_marker_before_pattern(
                file_path, 
                r'async def step_01\(self, request\):',
                self.MARKERS['step_methods_start']
            )
            if success1:
                success_count += 1
        else:
            self.log("ℹ️ Step methods start marker already exists")
            success_count += 1
        
        # 2. Insert step methods end marker before analyze_parameters
        if not self.check_marker_exists(file_path, self.MARKERS['step_methods_end']):
            success2 = self.insert_marker_before_pattern(
                file_path,
                r'async def analyze_parameters\(self, username, project_name, analysis_slug\):',
                self.MARKERS['step_methods_end']
            )
            if success2:
                success_count += 1
        else:
            self.log("ℹ️ Step methods end marker already exists")
            success_count += 1
        
        # 3. Insert workflow end marker at the end of the file
        if not self.check_marker_exists(file_path, self.MARKERS['workflow_end']):
            success3 = self.append_marker_to_file(file_path, self.MARKERS['workflow_end'])
            if success3:
                success_count += 1
        else:
            self.log("ℹ️ Workflow end marker already exists")
            success_count += 1
        
        if success_count == total_operations:
            self.log("🎉 All atomic transplantation markers successfully completed!")
            return True
        else:
            self.log(f"⚠️ {total_operations - success_count} operations failed")
            return False
    
    def add_complete_marker_set(self, file_path: str, section_name: str = "workflow_section") -> bool:
        """Add a complete set of atomic transplantation markers to a workflow file.
        
        This method attempts to automatically detect and mark:
        - Workflow section boundaries
        - Step definitions
        - Step methods
        
        Args:
            file_path: Path to the workflow file
            section_name: Name for the workflow section
        """
        self.log(f"🔧 Adding complete marker set to {file_path}")
        
        success_count = 0
        
        # 1. Add workflow start marker (look for class definition or steps definition)
        workflow_start = self.MARKERS['workflow_start'].format(section_name=section_name)
        if not self.check_marker_exists(file_path, workflow_start):
            # Try to find steps definition first
            if self.insert_marker_before_pattern(file_path, r'steps\s*=\s*\[', workflow_start):
                success_count += 1
            # Fallback to class definition
            elif self.insert_marker_before_pattern(file_path, r'class\s+\w+.*:', workflow_start):
                success_count += 1
        else:
            success_count += 1
        
        # 2. Add step definition markers
        if not self.check_marker_exists(file_path, self.MARKERS['step_def_start']):
            if self.insert_marker_before_pattern(file_path, r'steps\s*=\s*\[', self.MARKERS['step_def_start']):
                success_count += 1
        else:
            success_count += 1
        
        if not self.check_marker_exists(file_path, self.MARKERS['step_def_end']):
            if self.insert_marker_after_pattern(file_path, r'\]\s*$', self.MARKERS['step_def_end']):
                success_count += 1
        else:
            success_count += 1
        
        # 3. Add step methods markers
        if not self.check_marker_exists(file_path, self.MARKERS['step_methods_start']):
            if self.insert_marker_before_pattern(file_path, r'async def step_\d+\(', self.MARKERS['step_methods_start']):
                success_count += 1
        else:
            success_count += 1
        
        # 4. Add workflow end marker
        if not self.check_marker_exists(file_path, self.MARKERS['workflow_end']):
            if self.append_marker_to_file(file_path, self.MARKERS['workflow_end']):
                success_count += 1
        else:
            success_count += 1
        
        self.log(f"✅ Added {success_count} markers to {file_path}")
        return success_count > 0

def main():
    """Main entry point with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Atomic Transplantation Marker Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Complete Parameter Buster command
    complete_pb = subparsers.add_parser(
        'complete-parameter-buster',
        help='Complete markers for Parameter Buster workflow (specific implementation)'
    )
    complete_pb.add_argument(
        '--file', 
        default='plugins/045_parameter_buster_new.py',
        help='Path to Parameter Buster workflow file'
    )
    
    # Add markers command
    add_markers = subparsers.add_parser(
        'add-markers',
        help='Add complete marker set to any workflow file'
    )
    add_markers.add_argument('file', help='Path to workflow file')
    add_markers.add_argument(
        '--section-name', 
        default='workflow_section',
        help='Name for the workflow section'
    )
    
    # Insert before pattern command
    insert_before = subparsers.add_parser(
        'insert-before',
        help='Insert marker before first line matching pattern'
    )
    insert_before.add_argument('pattern', help='Regex pattern to match')
    insert_before.add_argument('marker', help='Marker text to insert')
    insert_before.add_argument('file', help='Path to file')
    
    # Insert after pattern command
    insert_after = subparsers.add_parser(
        'insert-after',
        help='Insert marker after first line matching pattern'
    )
    insert_after.add_argument('pattern', help='Regex pattern to match')
    insert_after.add_argument('marker', help='Marker text to insert')
    insert_after.add_argument('file', help='Path to file')
    
    # Insert at line command
    insert_at = subparsers.add_parser(
        'insert-at-line',
        help='Insert marker at specific line number'
    )
    insert_at.add_argument('line', type=int, help='Line number (1-indexed)')
    insert_at.add_argument('marker', help='Marker text to insert')
    insert_at.add_argument('file', help='Path to file')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create tool instance
    tool = AtomicTransplantationMarkerTool()
    
    # Execute command
    try:
        if args.command == 'complete-parameter-buster':
            success = tool.complete_parameter_buster_markers(args.file)
            sys.exit(0 if success else 1)
        
        elif args.command == 'add-markers':
            success = tool.add_complete_marker_set(args.file, args.section_name)
            sys.exit(0 if success else 1)
        
        elif args.command == 'insert-before':
            success = tool.insert_marker_before_pattern(args.file, args.pattern, args.marker)
            sys.exit(0 if success else 1)
        
        elif args.command == 'insert-after':
            success = tool.insert_marker_after_pattern(args.file, args.pattern, args.marker)
            sys.exit(0 if success else 1)
        
        elif args.command == 'insert-at-line':
            success = tool.insert_marker_at_line(args.file, args.line, args.marker)
            sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Legacy support for simple "complete" command
    if len(sys.argv) == 2 and sys.argv[1] == "complete":
        tool = AtomicTransplantationMarkerTool()
        success = tool.complete_parameter_buster_markers()
        sys.exit(0 if success else 1)
    else:
        main() 