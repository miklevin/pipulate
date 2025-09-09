#!/usr/bin/env python3
"""
🛡️ BULLETPROOF LARGE FUNCTION CONSOLIDATION

This script provides maximum regression prevention for consolidating large functions
with comprehensive before/after verification, diffs, and rollback capabilities.

Usage:
    python bulletproof_consolidation.py --function _browser_interact_with_current_page --verify-only
    python bulletproof_consolidation.py --function _browser_interact_with_current_page --execute
"""

import subprocess
import re
import os
import sys
import json
import hashlib
import tempfile
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import argparse
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FunctionMetrics:
    name: str
    start_line: int
    end_line: int
    line_count: int
    char_count: int
    content_hash: str
    content: str

class BulletproofConsolidator:
    """Maximum regression prevention for large function consolidation"""
    
    def __init__(self, function_name: str, verify_only: bool = True):
        self.function_name = function_name
        self.verify_only = verify_only
        self.server_py = Path("server.py")
        self.mcp_tools_py = Path("mcp_tools.py")
        self.verification_log = []
        
    def log(self, level: str, message: str, **kwargs):
        """Enhanced logging with verification tracking"""
        emoji_map = {
            "info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌",
            "checkpoint": "📝", "verification": "🔍", "metrics": "📊", "diff": "🔄"
        }
        emoji = emoji_map.get(level, "📋")
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {emoji} {message}"
        
        print(log_entry)
        self.verification_log.append({
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "details": kwargs
        })
        
        if kwargs:
            for key, value in kwargs.items():
                print(f"   {key}: {value}")
    
    def run_command(self, cmd: str) -> Tuple[int, str, str]:
        """Run command with error handling"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def extract_function_metrics(self, file_path: Path, func_name: str) -> Optional[FunctionMetrics]:
        """Extract comprehensive function metrics with bulletproof parsing"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Find function start
            start_line = None
            for i, line in enumerate(lines):
                if re.match(rf'^async def {re.escape(func_name)}\(', line):
                    start_line = i + 1  # 1-indexed
                    break
            
            if start_line is None:
                return None
            
            # Find function end by tracking indentation
            end_line = len(lines)  # Default to end of file
            base_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
            
            for i in range(start_line, len(lines)):
                line = lines[i]
                if line.strip():  # Non-empty line
                    current_indent = len(line) - len(line.lstrip())
                    # If we find a line at same or lower indentation that's a def/class/async def
                    if (current_indent <= base_indent and 
                        re.match(r'^\s*(async def |def |class )', line)):
                        end_line = i + 1  # 1-indexed, exclusive
                        break
            
            # Extract function content
            function_lines = lines[start_line - 1:end_line - 1]
            content = ''.join(function_lines)
            
            return FunctionMetrics(
                name=func_name,
                start_line=start_line,
                end_line=end_line - 1,  # Inclusive end line
                line_count=len(function_lines),
                char_count=len(content),
                content_hash=hashlib.sha256(content.encode()).hexdigest()[:16],
                content=content
            )
            
        except Exception as e:
            self.log("error", f"Failed to extract function metrics: {e}")
            return None
    
    def verify_function_integrity(self, original: FunctionMetrics, copied: FunctionMetrics) -> bool:
        """Comprehensive function integrity verification"""
        self.log("verification", f"🔍 INTEGRITY CHECK: {original.name}")
        
        # Check 1: Line count match
        if original.line_count != copied.line_count:
            self.log("error", "Line count mismatch", 
                    original=original.line_count, 
                    copied=copied.line_count)
            return False
        
        # Check 2: Character count match  
        if original.char_count != copied.char_count:
            self.log("error", "Character count mismatch",
                    original=original.char_count,
                    copied=copied.char_count)
            return False
        
        # Check 3: Content hash match
        if original.content_hash != copied.content_hash:
            self.log("error", "Content hash mismatch",
                    original=original.content_hash,
                    copied=copied.content_hash)
            return False
        
        # Check 4: Exact content match
        if original.content != copied.content:
            self.log("error", "Content mismatch detected")
            # Save diff for analysis
            self.save_diff_analysis(original.content, copied.content)
            return False
        
        self.log("success", "Function integrity verified",
                lines=original.line_count,
                chars=original.char_count,
                hash=original.content_hash)
        return True
    
    def save_diff_analysis(self, original: str, copied: str):
        """Save detailed diff analysis for debugging"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='_original.py', delete=False) as f:
            f.write(original)
            original_file = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='_copied.py', delete=False) as f:
            f.write(copied)
            copied_file = f.name
        
        # Generate diff
        code, diff_output, _ = self.run_command(f"diff -u {original_file} {copied_file}")
        
        diff_report = f"""
FUNCTION INTEGRITY FAILURE - DIFF ANALYSIS
==========================================
Function: {self.function_name}
Timestamp: {datetime.now().isoformat()}

DIFF OUTPUT:
{diff_output}

Original file: {original_file}
Copied file: {copied_file}
"""
        
        diff_file = f"diff_analysis_{self.function_name}_{datetime.now().strftime('%H%M%S')}.txt"
        with open(diff_file, 'w') as f:
            f.write(diff_report)
        
        self.log("diff", f"Diff analysis saved to {diff_file}")
        
        # Cleanup temp files
        try:
            os.unlink(original_file)
            os.unlink(copied_file)
        except:
            pass
    
    def verify_registration_exists(self, func_name: str) -> bool:
        """Verify function is properly registered in mcp_tools.py"""
        tool_name = func_name[1:]  # Remove underscore
        try:
            with open(self.mcp_tools_py, 'r') as f:
                content = f.read()
                return f'register_mcp_tool("{tool_name}"' in content
        except Exception:
            return False
    
    def test_mcp_integration(self, func_name: str) -> bool:
        """Test that MCP tool is actually accessible"""
        tool_name = func_name[1:]  # Remove underscore
        test_script = f"""
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from mcp_tools import register_all_mcp_tools, MCP_TOOL_REGISTRY
    register_all_mcp_tools()
    
    if "{tool_name}" not in MCP_TOOL_REGISTRY:
        print("ERROR: Tool not in registry")
        exit(1)
    
    # Test the function can be called
    func = MCP_TOOL_REGISTRY["{tool_name}"]
    print(f"SUCCESS: {tool_name} accessible in registry")
    print(f"Function: {{func}}")
    exit(0)
    
except Exception as e:
    print(f"ERROR: {{e}}")
    exit(1)
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            test_file = f.name
        
        try:
            code, stdout, stderr = self.run_command(f"python {test_file}")
            success = code == 0 and "SUCCESS" in stdout
            
            if success:
                self.log("success", f"MCP integration test passed for {func_name}")
            else:
                self.log("error", f"MCP integration test failed for {func_name}",
                        stdout=stdout, stderr=stderr)
            
            return success
        finally:
            try:
                os.unlink(test_file)
            except:
                pass
    
    def create_safety_checkpoint(self, message: str) -> bool:
        """Create git checkpoint with verification"""
        if self.verify_only:
            self.log("checkpoint", f"[VERIFY-ONLY] Would create checkpoint: {message}")
            return True
        
        # Check git status first
        code, status_output, _ = self.run_command("git status --porcelain")
        if not status_output.strip():
            self.log("info", "No changes to commit")
            return True
        
        # Stage and commit
        code, _, stderr = self.run_command("git add -A")
        if code != 0:
            self.log("error", "Failed to stage changes", stderr=stderr)
            return False
        
        commit_msg = f"🛡️ BULLETPROOF: {message}\n\nVerification log:\n" + "\n".join([
            f"- {entry['message']}" for entry in self.verification_log[-5:]
        ])
        
        code, _, stderr = self.run_command(f'git commit -m "{commit_msg}"')
        if code != 0 and "nothing to commit" not in stderr:
            self.log("error", "Failed to create checkpoint", stderr=stderr)
            return False
        
        self.log("checkpoint", f"Safety checkpoint created: {message}")
        return True
    
    def consolidate_function_safely(self) -> bool:
        """Main bulletproof consolidation workflow"""
        self.log("info", f"🛡️ BULLETPROOF CONSOLIDATION: {self.function_name}")
        self.log("info", f"Mode: {'VERIFY-ONLY' if self.verify_only else 'EXECUTE'}")
        
        # Step 1: Extract original function metrics
        self.log("metrics", "📊 PHASE 1: Extracting original function metrics")
        original_metrics = self.extract_function_metrics(self.server_py, self.function_name)
        
        if not original_metrics:
            self.log("error", f"Function {self.function_name} not found in server.py")
            return False
        
        self.log("metrics", "Original function metrics captured",
                lines=original_metrics.line_count,
                chars=original_metrics.char_count,
                hash=original_metrics.content_hash,
                start_line=original_metrics.start_line,
                end_line=original_metrics.end_line)
        
        # Step 2: Check if function already exists in mcp_tools.py
        self.log("verification", "📊 PHASE 2: Checking mcp_tools.py state")
        existing_metrics = self.extract_function_metrics(self.mcp_tools_py, self.function_name)
        
        if existing_metrics:
            self.log("info", "Function already exists in mcp_tools.py - verifying integrity")
            
            if self.verify_function_integrity(original_metrics, existing_metrics):
                self.log("success", "Existing function passed integrity check")
                
                # Check registration
                if self.verify_registration_exists(self.function_name):
                    self.log("success", "Function registration verified")
                    
                    # Test MCP integration
                    if self.test_mcp_integration(self.function_name):
                        self.log("success", "MCP integration test passed")
                        
                        # Safe to remove from server.py
                        return self.remove_from_server_safely(original_metrics)
                    else:
                        self.log("error", "MCP integration test failed")
                        return False
                else:
                    self.log("error", "Function not properly registered")
                    return False
            else:
                self.log("error", "Existing function failed integrity check")
                return False
        else:
            # Function needs to be added to mcp_tools.py
            return self.add_to_mcp_tools_safely(original_metrics)
    
    def add_to_mcp_tools_safely(self, metrics: FunctionMetrics) -> bool:
        """Safely add function to mcp_tools.py with verification"""
        self.log("info", "📊 PHASE 3: Adding function to mcp_tools.py")
        
        if self.verify_only:
            self.log("info", f"[VERIFY-ONLY] Would add {metrics.name} ({metrics.line_count} lines)")
            return True
        
        # Read current mcp_tools.py
        with open(self.mcp_tools_py, 'r') as f:
            content = f.read()
        
        # Find insertion point (before final registrations)
        pattern = r'# Register remaining.*tools.*NOW that functions are defined\n'
        match = re.search(pattern, content)
        
        if not match:
            self.log("error", "Could not find registration section in mcp_tools.py")
            return False
        
        # Insert function
        insertion_point = match.start()
        new_content = (
            content[:insertion_point] +
            metrics.content + "\n" +
            content[insertion_point:]
        )
        
        # Add registration
        tool_name = metrics.name[1:]  # Remove underscore
        registration_line = f'register_mcp_tool("{tool_name}", {metrics.name})\n'
        
        # Find end of existing registrations
        last_reg_match = None
        for match in re.finditer(r'register_mcp_tool\([^)]+\)', new_content):
            last_reg_match = match
        
        if last_reg_match:
            reg_end = last_reg_match.end()
            new_content = (
                new_content[:reg_end] + "\n" + registration_line +
                new_content[reg_end:]
            )
        
        # Write with backup
        backup_file = f"{self.mcp_tools_py}.backup_{datetime.now().strftime('%H%M%S')}"
        with open(backup_file, 'w') as f:
            f.write(content)
        
        with open(self.mcp_tools_py, 'w') as f:
            f.write(new_content)
        
        self.log("success", f"Function added to mcp_tools.py (backup: {backup_file})")
        
        # Verify the addition
        added_metrics = self.extract_function_metrics(self.mcp_tools_py, self.function_name)
        if not added_metrics:
            self.log("error", "Function not found after addition - restoring backup")
            with open(backup_file, 'r') as f:
                with open(self.mcp_tools_py, 'w') as out:
                    out.write(f.read())
            return False
        
        if not self.verify_function_integrity(metrics, added_metrics):
            self.log("error", "Function integrity check failed after addition")
            with open(backup_file, 'r') as f:
                with open(self.mcp_tools_py, 'w') as out:
                    out.write(f.read())
            return False
        
        # Test MCP integration
        if not self.test_mcp_integration(self.function_name):
            self.log("error", "MCP integration test failed after addition")
            return False
        
        # Create checkpoint
        self.create_safety_checkpoint(f"Added {metrics.name} to mcp_tools.py ({metrics.line_count} lines)")
        
        # Clean up backup on success
        try:
            os.unlink(backup_file)
        except:
            pass
        
        return True
    
    def remove_from_server_safely(self, metrics: FunctionMetrics) -> bool:
        """Safely remove function from server.py with verification"""
        self.log("info", "📊 PHASE 4: Removing function from server.py")
        
        if self.verify_only:
            self.log("info", f"[VERIFY-ONLY] Would remove {metrics.name} (lines {metrics.start_line}-{metrics.end_line})")
            return True
        
        # Read current server.py
        with open(self.server_py, 'r') as f:
            lines = f.readlines()
        
        # Remove function lines
        new_lines = lines[:metrics.start_line - 1] + lines[metrics.end_line:]
        
        # Create backup
        backup_file = f"{self.server_py}.backup_{datetime.now().strftime('%H%M%S')}"
        with open(backup_file, 'w') as f:
            f.writelines(lines)
        
        # Write modified content
        with open(self.server_py, 'w') as f:
            f.writelines(new_lines)
        
        # Also remove any registration calls
        self.remove_registration_from_server(metrics.name)
        
        # Verify removal
        removed_check = self.extract_function_metrics(self.server_py, self.function_name)
        if removed_check:
            self.log("error", "Function still found in server.py after removal")
            # Restore backup
            with open(backup_file, 'r') as f:
                with open(self.server_py, 'w') as out:
                    out.write(f.read())
            return False
        
        # Calculate reduction
        original_lines = len(lines)
        new_lines_count = len(new_lines)
        lines_removed = original_lines - new_lines_count
        
        self.log("success", f"Function removed from server.py",
                lines_removed=lines_removed,
                original_lines=original_lines,
                new_lines=new_lines_count)
        
        # Final MCP integration test
        if not self.test_mcp_integration(self.function_name):
            self.log("error", "Final MCP integration test failed")
            return False
        
        # Create final checkpoint
        self.create_safety_checkpoint(f"Completed {metrics.name} consolidation ({lines_removed} lines removed)")
        
        # Clean up backup on success
        try:
            os.unlink(backup_file)
        except:
            pass
        
        return True
    
    def remove_registration_from_server(self, func_name: str):
        """Remove registration calls from server.py"""
        tool_name = func_name[1:]  # Remove underscore
        
        with open(self.server_py, 'r') as f:
            content = f.read()
        
        # Remove registration line
        pattern = rf'register_mcp_tool\("{tool_name}"[^)]*\)\n?'
        new_content = re.sub(pattern, '', content)
        
        with open(self.server_py, 'w') as f:
            f.write(new_content)
    
    def save_verification_report(self):
        """Save comprehensive verification report"""
        report = {
            "function": self.function_name,
            "timestamp": datetime.now().isoformat(),
            "verification_log": self.verification_log,
            "mode": "verify_only" if self.verify_only else "execute"
        }
        
        report_file = f"verification_report_{self.function_name}_{datetime.now().strftime('%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log("info", f"Verification report saved: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Bulletproof function consolidation")
    parser.add_argument("--function", required=True, help="Function name to consolidate")
    parser.add_argument("--verify-only", action="store_true", help="Verify without executing")
    parser.add_argument("--execute", action="store_true", help="Actually perform consolidation")
    
    args = parser.parse_args()
    
    if not args.verify_only and not args.execute:
        print("Must specify either --verify-only or --execute")
        return 1
    
    verify_only = args.verify_only or not args.execute
    consolidator = BulletproofConsolidator(args.function, verify_only)
    
    try:
        success = consolidator.consolidate_function_safely()
        consolidator.save_verification_report()
        return 0 if success else 1
    except Exception as e:
        consolidator.log("error", f"Unexpected error: {e}")
        consolidator.save_verification_report()
        return 1

if __name__ == "__main__":
    exit(main()) 