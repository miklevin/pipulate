#!/usr/bin/env python3
"""
Python Environment Diagnostic and Fix Script
============================================

This script helps AI assistants diagnose and fix Python environment issues
that commonly occur during the progressive discovery sequence.

Usage:
    python test_python_environment_fix.py

The script will:
1. Check if we're in the correct directory
2. Verify Python environment activation
3. Test critical dependencies
4. Provide specific fixes for common issues
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * 40)

def run_command(cmd, capture_output=True):
    """Run a command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_directory():
    """Check if we're in the correct pipulate directory"""
    print_section("Directory Check")
    
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Check if we're in a pipulate directory
    if "pipulate" not in str(current_dir):
        print("❌ WARNING: Not in a pipulate directory")
        print("   Expected: /path/to/pipulate/")
        print("   Current:  {current_dir}")
        return False
    
    # Check for key files
    key_files = ["server.py", "flake.nix", "requirements.txt"]
    missing_files = []
    
    for file in key_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing key files: {missing_files}")
        return False
    
    print("✅ Directory looks correct")
    return True

def check_python_environment():
    """Check Python environment status"""
    print_section("Python Environment Check")
    
    # Check Python executable
    python_path = sys.executable
    print(f"Python executable: {python_path}")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"In virtual environment: {in_venv}")
    
    # Check VIRTUAL_ENV environment variable
    venv_env = os.environ.get('VIRTUAL_ENV')
    print(f"VIRTUAL_ENV: {venv_env}")
    
    # Check PATH
    path = os.environ.get('PATH', '')
    venv_in_path = '.venv/bin' in path or 'venv/bin' in path
    print(f"Virtual env in PATH: {venv_in_path}")
    
    # Check Python version
    python_version = sys.version
    print(f"Python version: {python_version}")
    
    return in_venv or venv_env or venv_in_path

def test_critical_dependencies():
    """Test critical dependencies"""
    print_section("Critical Dependencies Test")
    
    critical_modules = [
        'aiohttp',
        'fasthtml',
        'starlette',
        'uvicorn'
    ]
    
    failed_modules = []
    
    for module in critical_modules:
        try:
            __import__(module)
            print(f"✅ {module}: OK")
        except ImportError as e:
            print(f"❌ {module}: FAILED - {e}")
            failed_modules.append(module)
    
    return len(failed_modules) == 0

def test_mcp_tools():
    """Test MCP tools accessibility"""
    print_section("MCP Tools Test")
    
    try:
        # Add parent directory to Python path to find mcp_tools
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from mcp_tools import _builtin_get_cat_fact
        print("✅ MCP tools import: OK")
        
        # Test a simple MCP tool
        import asyncio
        result = asyncio.run(_builtin_get_cat_fact({}))
        print(f"✅ MCP tool execution: OK - {result.get('fact', 'No fact returned')[:50]}...")
        return True
    except ImportError as e:
        print(f"❌ MCP tools import: FAILED - {e}")
        return False
    except Exception as e:
        print(f"❌ MCP tool execution: FAILED - {e}")
        return False

def check_nix_environment():
    """Check Nix environment status"""
    print_section("Nix Environment Check")
    
    in_nix_shell = os.environ.get('IN_NIX_SHELL')
    print(f"IN_NIX_SHELL: {in_nix_shell}")
    
    # Check if we're in a Nix environment
    if in_nix_shell:
        print("✅ In Nix shell environment")
        return True
    else:
        print("⚠️  Not in Nix shell environment")
        return False

def provide_fixes():
    """Provide specific fixes for common issues"""
    print_section("Common Issues & Fixes")
    
    print("🚨 If you're having environment issues, try these fixes:")
    print()
    
    print("1. ENTER NIX ENVIRONMENT:")
    print("   nix develop .#quiet")
    print()
    
    print("2. CLEAN ENVIRONMENT (if nested):")
    print("   unset VIRTUAL_ENV")
    print("   unset PATH")
    print("   export PATH='/run/wrappers/bin:/usr/bin:/usr/sbin:/home/mike/.nix-profile/bin:/nix/profile/bin:/home/mike/.local/state/nix/profile/bin:/etc/profiles/per-user/mike/bin:/nix/var/nix/profiles/default/bin:/run/current-system/sw/bin'")
    print("   exec nix develop .#quiet")
    print()
    
    print("3. VERIFY ENVIRONMENT:")
    print("   echo $IN_NIX_SHELL  # Should show 'impure'")
    print("   which python       # Should show .venv/bin/python")
    print("   python --version   # Should show Python 3.12.11")
    print()
    
    print("4. TEST DEPENDENCIES:")
    print("   python -c 'import aiohttp; print(\"aiohttp OK\")'")
    print("   python -c 'from mcp_tools import _builtin_get_cat_fact; print(\"MCP tools OK\")'")
    print()

def main():
    """Main diagnostic function"""
    print_header("Python Environment Diagnostic")
    
    print("This script will diagnose your Python environment and help fix common issues.")
    print("Run this script if you encounter 'ModuleNotFoundError' or environment confusion.")
    
    # Run all checks
    checks = [
        ("Directory", check_directory()),
        ("Python Environment", check_python_environment()),
        ("Critical Dependencies", test_critical_dependencies()),
        ("MCP Tools", test_mcp_tools()),
        ("Nix Environment", check_nix_environment())
    ]
    
    print_section("Summary")
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("Your Python environment is working correctly.")
        print("You can proceed with the AI progressive discovery sequence.")
    else:
        print("⚠️  SOME CHECKS FAILED!")
        print("Please review the issues above and apply the fixes below.")
        provide_fixes()
    
    print_header("Next Steps")
    print("If environment is working, continue with:")
    print("1. python discover_mcp_tools.py")
    print("2. Follow the breadcrumb trail in the discovery sequence")
    print("3. Use helpers/ai_tool_discovery.py for easy tool access")

if __name__ == "__main__":
    main() 