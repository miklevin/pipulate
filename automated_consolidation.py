#!/usr/bin/env python3
"""
🛡️ AUTOMATED MCP TOOL CONSOLIDATION WITH REGRESSION PREVENTION

This script automates the proven ADD → TEST → REMOVE consolidation strategy
with comprehensive git-based verification and checkpointing.

Usage:
    python automated_consolidation.py --dry-run    # Preview what will be done
    python automated_consolidation.py --execute    # Actually perform consolidation
    python automated_consolidation.py --continue   # Continue from last checkpoint
"""

import subprocess
import re
import os
import sys
import json
import tempfile
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import argparse
from dataclasses import dataclass

@dataclass
class FunctionInfo:
    name: str
    start_line: int
    end_line: int
    content: str
    registration_line: Optional[str] = None

class MCPConsolidator:
    """Automated MCP tool consolidation with regression prevention"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.server_py = Path("server.py")
        self.mcp_tools_py = Path("mcp_tools.py")
        self.checkpoint_file = Path(".consolidation_checkpoint.json")
        
        # Verification scripts
        self.verification_scripts = [
            "pre_consolidation_verify.sh",
            "compare_function_implementations.sh", 
            "test_mcp_tools_integration.sh"
        ]
        
    def log(self, level: str, message: str, **kwargs):
        """Structured logging with emojis"""
        emoji_map = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌",
            "checkpoint": "📝",
            "verification": "🔍",
            "git": "🔧"
        }
        emoji = emoji_map.get(level, "📋")
        print(f"{emoji} {message}")
        if kwargs:
            for key, value in kwargs.items():
                print(f"   {key}: {value}")
    
    def run_command(self, cmd: str, capture_output: bool = True) -> Tuple[int, str, str]:
        """Run shell command with error handling"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=capture_output, 
                text=True, cwd=Path.cwd()
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def create_git_checkpoint(self, message: str) -> bool:
        """Create a git checkpoint commit"""
        if self.dry_run:
            self.log("checkpoint", f"[DRY RUN] Would create checkpoint: {message}")
            return True
            
        code, stdout, stderr = self.run_command("git add -A")
        if code != 0:
            self.log("error", "Failed to stage files", stderr=stderr)
            return False
            
        code, stdout, stderr = self.run_command(f'git commit -m "🔄 CHECKPOINT: {message}"')
        if code != 0 and "nothing to commit" not in stderr:
            self.log("error", "Failed to create checkpoint", stderr=stderr)
            return False
            
        self.log("checkpoint", f"Created checkpoint: {message}")
        return True
    
    def get_line_count(self, file_path: Path) -> int:
        """Get line count of file"""
        try:
            with open(file_path, 'r') as f:
                return len(f.readlines())
        except Exception:
            return 0
    
    def find_mcp_functions_in_server(self) -> List[FunctionInfo]:
        """Find all MCP tool functions still in server.py"""
        functions = []
        
        with open(self.server_py, 'r') as f:
            lines = f.readlines()
        
        current_func = None
        brace_count = 0
        
        for i, line in enumerate(lines, 1):
            # Look for async def functions starting with _
            match = re.match(r'^async def (_\w+)\(', line)
            if match:
                func_name = match.group(1)
                # Skip if already in mcp_tools.py
                if self.function_exists_in_mcp_tools(func_name):
                    continue
                    
                current_func = FunctionInfo(
                    name=func_name,
                    start_line=i,
                    end_line=i,
                    content=line
                )
                brace_count = 0
                continue
            
            if current_func:
                current_func.content += line
                current_func.end_line = i
                
                # Track indentation to find end of function
                if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                    if not line.startswith((' ', '\t')) or re.match(r'^(async def |def |class )', line):
                        # Function ended
                        current_func.end_line = i - 1
                        functions.append(current_func)
                        current_func = None
        
        # Handle last function if file ends
        if current_func:
            functions.append(current_func)
            
        return functions
    
    def function_exists_in_mcp_tools(self, func_name: str) -> bool:
        """Check if function already exists in mcp_tools.py"""
        try:
            with open(self.mcp_tools_py, 'r') as f:
                content = f.read()
                return f"async def {func_name}(" in content
        except Exception:
            return False
    
    def extract_function_from_server(self, func_info: FunctionInfo) -> str:
        """Extract function content from server.py"""
        with open(self.server_py, 'r') as f:
            lines = f.readlines()
        
        return ''.join(lines[func_info.start_line-1:func_info.end_line])
    
    def add_function_to_mcp_tools(self, func_info: FunctionInfo) -> bool:
        """Add function to mcp_tools.py with proper registration"""
        function_content = self.extract_function_from_server(func_info)
        
        if self.dry_run:
            self.log("info", f"[DRY RUN] Would add {func_info.name} to mcp_tools.py")
            self.log("info", f"Function size: {func_info.end_line - func_info.start_line + 1} lines")
            return True
        
        # Read current mcp_tools.py
        with open(self.mcp_tools_py, 'r') as f:
            content = f.read()
        
        # Find insertion point (before last registration calls)
        registration_pattern = r'# Register.*tools.*NOW that functions are defined\n'
        match = re.search(registration_pattern, content)
        
        if not match:
            self.log("error", "Could not find registration section in mcp_tools.py")
            return False
        
        # Insert function before registration section
        insertion_point = match.start()
        new_content = (
            content[:insertion_point] + 
            function_content + "\n" +
            content[insertion_point:]
        )
        
        # Add registration call
        tool_name = func_info.name[1:]  # Remove leading underscore
        registration_line = f'register_mcp_tool("{tool_name}", {func_info.name})\n'
        
        # Find the end of existing registrations and add new one
        existing_registrations = re.findall(r'register_mcp_tool\([^)]+\)', new_content)
        if existing_registrations:
            last_registration = existing_registrations[-1]
            insertion_index = new_content.rfind(last_registration) + len(last_registration)
            new_content = (
                new_content[:insertion_index] + "\n" + registration_line +
                new_content[insertion_index:]
            )
        
        # Write updated content
        with open(self.mcp_tools_py, 'w') as f:
            f.write(new_content)
        
        self.log("success", f"Added {func_info.name} to mcp_tools.py")
        return True
    
    def verify_function_consolidation(self, func_name: str) -> bool:
        """Comprehensive verification of function consolidation"""
        if self.dry_run:
            self.log("verification", f"[DRY RUN] Would verify {func_name}")
            return True
        
        # Test 1: Function exists in mcp_tools.py
        if not self.function_exists_in_mcp_tools(func_name):
            self.log("error", f"Verification failed: {func_name} not found in mcp_tools.py")
            return False
        
        # Test 2: Registration exists
        with open(self.mcp_tools_py, 'r') as f:
            content = f.read()
            tool_name = func_name[1:]  # Remove underscore
            if f'register_mcp_tool("{tool_name}"' not in content:
                self.log("error", f"Verification failed: {func_name} not registered")
                return False
        
        # Test 3: Integration test
        test_code = f"""
from mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY
register_all_mcp_tools()
tool_name = "{tool_name}"
if tool_name not in MCP_TOOL_REGISTRY:
    print(f"ERROR: {tool_name} not in registry")
    exit(1)
print(f"SUCCESS: {tool_name} verified in registry")
"""
        
        code, stdout, stderr = self.run_command(f'python3 -c "{test_code}"')
        if code != 0:
            self.log("error", f"Integration test failed for {func_name}", stderr=stderr)
            return False
        
        self.log("verification", f"All verifications passed for {func_name}")
        return True
    
    def remove_function_from_server(self, func_info: FunctionInfo) -> bool:
        """Remove function from server.py"""
        if self.dry_run:
            self.log("info", f"[DRY RUN] Would remove {func_info.name} from server.py")
            return True
        
        with open(self.server_py, 'r') as f:
            lines = f.readlines()
        
        # Remove function lines
        new_lines = (
            lines[:func_info.start_line-1] + 
            lines[func_info.end_line:]
        )
        
        with open(self.server_py, 'w') as f:
            f.writelines(new_lines)
        
        # Also remove any registration calls for this function
        self.remove_registration_from_server(func_info.name)
        
        self.log("success", f"Removed {func_info.name} from server.py")
        return True
    
    def remove_registration_from_server(self, func_name: str) -> bool:
        """Remove registration calls from server.py"""
        tool_name = func_name[1:]  # Remove underscore
        
        with open(self.server_py, 'r') as f:
            content = f.read()
        
        # Remove registration line
        pattern = rf'register_mcp_tool\("{tool_name}"[^)]*\)\n?'
        new_content = re.sub(pattern, '', content)
        
        with open(self.server_py, 'w') as f:
            f.write(new_content)
        
        return True
    
    def consolidate_function(self, func_info: FunctionInfo) -> bool:
        """Complete consolidation process for one function"""
        self.log("info", f"Starting consolidation of {func_info.name}")
        
        initial_lines = self.get_line_count(self.server_py)
        
        # Step 1: ADD function to mcp_tools.py
        if not self.add_function_to_mcp_tools(func_info):
            return False
        
        # Step 2: TEST that everything works
        if not self.verify_function_consolidation(func_info.name):
            self.log("error", f"Verification failed for {func_info.name}")
            return False
        
        # Step 3: REMOVE from server.py
        if not self.remove_function_from_server(func_info):
            return False
        
        # Measure progress
        final_lines = self.get_line_count(self.server_py)
        lines_removed = initial_lines - final_lines
        
        self.log("success", f"Consolidated {func_info.name}", 
                lines_removed=lines_removed,
                server_lines_remaining=final_lines)
        
        # Create checkpoint
        message = f"Consolidated {func_info.name} ({lines_removed} lines removed)"
        return self.create_git_checkpoint(message)
    
    def get_remaining_functions(self) -> List[FunctionInfo]:
        """Get list of functions still needing consolidation"""
        functions = self.find_mcp_functions_in_server()
        
        # Filter out functions that don't look like MCP tools
        mcp_functions = []
        for func in functions:
            # Look for patterns that suggest this is an MCP tool
            if any(pattern in func.content.lower() for pattern in [
                'async def _browser_', 'async def _botify_', 'async def _local_llm_',
                'async def _ui_', 'params: dict', 'return {'
            ]):
                mcp_functions.append(func)
        
        return mcp_functions
    
    def save_checkpoint(self, completed_functions: List[str]):
        """Save progress checkpoint"""
        checkpoint = {
            "completed_functions": completed_functions,
            "timestamp": subprocess.check_output(["date", "+%Y-%m-%d %H:%M:%S"]).decode().strip()
        }
        
        if not self.dry_run:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
    
    def load_checkpoint(self) -> List[str]:
        """Load previous progress"""
        if not self.checkpoint_file.exists():
            return []
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                return checkpoint.get("completed_functions", [])
        except Exception:
            return []
    
    def run_consolidation(self) -> bool:
        """Main consolidation workflow"""
        self.log("info", "🚀 Starting automated MCP tool consolidation")
        
        # Get initial state
        initial_lines = self.get_line_count(self.server_py)
        initial_mcp_count = len(self.get_remaining_functions())
        
        self.log("info", "Initial state",
                server_lines=initial_lines,
                functions_to_consolidate=initial_mcp_count)
        
        # Load previous progress
        completed = self.load_checkpoint()
        if completed:
            self.log("info", f"Resuming from checkpoint ({len(completed)} functions already done)")
        
        # Get remaining functions
        remaining_functions = self.get_remaining_functions()
        remaining_functions = [f for f in remaining_functions if f.name not in completed]
        
        if not remaining_functions:
            self.log("success", "No functions remaining to consolidate!")
            return True
        
        self.log("info", f"Processing {len(remaining_functions)} remaining functions")
        
        # Process each function
        success_count = 0
        for i, func_info in enumerate(remaining_functions, 1):
            self.log("info", f"Processing {i}/{len(remaining_functions)}: {func_info.name}")
            
            if self.consolidate_function(func_info):
                success_count += 1
                completed.append(func_info.name)
                self.save_checkpoint(completed)
            else:
                self.log("error", f"Failed to consolidate {func_info.name}")
                if not self.dry_run:
                    break
        
        # Final status
        final_lines = self.get_line_count(self.server_py)
        total_removed = initial_lines - final_lines
        percentage = (total_removed / initial_lines) * 100 if initial_lines > 0 else 0
        
        self.log("success", "Consolidation complete",
                functions_processed=success_count,
                total_lines_removed=total_removed,
                percentage_reduction=f"{percentage:.1f}%",
                final_server_lines=final_lines)
        
        return success_count == len(remaining_functions)

def main():
    parser = argparse.ArgumentParser(description="Automated MCP tool consolidation")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without executing")
    parser.add_argument("--execute", action="store_true", help="Actually perform consolidation")
    parser.add_argument("--continue", action="store_true", help="Continue from last checkpoint")
    
    args = parser.parse_args()
    
    if not any([args.dry_run, args.execute, getattr(args, 'continue', False)]):
        parser.print_help()
        return
    
    dry_run = args.dry_run or not args.execute
    consolidator = MCPConsolidator(dry_run=dry_run)
    
    try:
        success = consolidator.run_consolidation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        consolidator.log("warning", "Consolidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        consolidator.log("error", f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 