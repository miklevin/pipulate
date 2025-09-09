#!/usr/bin/env python3
"""
Simple ARIA Validation Script - Prevents Critical Accessibility Regressions

This script validates that critical ARIA attributes are present in server.py dropdown functions.
Lightweight replacement for the full validate_aria.py functionality now integrated into DevAssistant.

Usage:
    python helpers/validate_aria_simple.py
"""

import re
import sys
from pathlib import Path

def validate_server_dropdowns():
    """Validate that server.py dropdown functions have required ARIA attributes."""
    
    server_path = Path("server.py")
    if not server_path.exists():
        print("❌ server.py not found!")
        return False
    
    content = server_path.read_text()
    
    # Check for forbidden regression patterns that caused the original issue
    forbidden_patterns = {
        "role='group' in PROFILE dropdown": {
            'pattern': r'profile-dropdown-menu.*role=[\'"]group[\'"]',
            'message': 'PROFILE dropdown should NOT have role="group" (causes width issues)'
        }
    }
    
    print("🔍 Checking server.py for critical ARIA regressions...")
    
    regression_found = False
    for check_name, check_info in forbidden_patterns.items():
        if re.search(check_info['pattern'], content):
            print(f"   ❌ {check_name}: {check_info['message']}")
            regression_found = True
        else:
            print(f"   ✅ {check_name}: OK")
    
    # Basic check that dropdown functions exist and have some ARIA attributes
    dropdown_functions = ['create_profile_menu', 'create_menu_container']
    aria_patterns = ['aria_label', 'aria_expanded', 'aria_haspopup']
    
    for func_name in dropdown_functions:
        func_pattern = rf'def {func_name}\([^)]*\):(.*?)(?=\ndef|\Z)'
        func_match = re.search(func_pattern, content, re.DOTALL)
        
        if func_match:
            func_content = func_match.group(1)
            aria_found = any(pattern in func_content for pattern in aria_patterns)
            if aria_found:
                print(f"   ✅ {func_name}: Has ARIA attributes")
            else:
                print(f"   ❌ {func_name}: Missing ARIA attributes")
                regression_found = True
        else:
            print(f"   ⚠️  {func_name}: Function not found (may be OK)")
    
    return not regression_found

def main():
    """Main validation function."""
    
    print("🛡️  ARIA ACCESSIBILITY VALIDATION (Simple)")
    print("=" * 50)
    
    if validate_server_dropdowns():
        print(f"\n🎉 VALIDATION PASSED! No critical ARIA regressions detected.")
        return 0
    else:
        print(f"\n💥 VALIDATION FAILED! Fix critical issues before committing.")
        print(f"\n💡 For detailed analysis, use the Development Assistant plugin:")
        print(f"   1. Navigate to Development Assistant in Pipulate")
        print(f"   2. Analyze server.py for complete ARIA validation")
        print(f"   3. Review automation readiness report")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 