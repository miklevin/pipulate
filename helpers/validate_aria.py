#!/usr/bin/env python3
"""
ARIA Validation Script - Prevents Accessibility Regressions

This script validates that critical ARIA attributes are present in dropdown functions.
Run this before commits to catch accessibility regressions early.

Usage:
    python helpers/validate_aria.py
    
Expected in CI/CD:
    - Pre-commit hook
    - GitHub Actions validation
    - Manual testing checklist
"""

import re
import sys
from pathlib import Path

def validate_dropdown_aria(file_path):
    """Validate that dropdown functions have required ARIA attributes."""
    
    # Define required ARIA patterns for each dropdown function
    required_patterns = {
        'create_profile_menu': {
            'aria_label': 'Profile selection menu',
            'aria_expanded': 'false',
            'aria_haspopup': 'menu',
            'aria_labelledby': 'profile-id',
            'role_menu': "role='menu'",
            'ul_aria_label': 'Profile options'
        },
        'create_menu_container': {
            'aria_label': 'Application menu',
            'aria_expanded': 'false', 
            'aria_haspopup': 'menu',
            'aria_labelledby': 'app-id',
            'role_menu': "role='menu'",
            'ul_aria_label': 'Application options'
        },
        'create_env_menu': {
            'dev_aria_label': 'Switch to Development environment',
            'prod_aria_label': 'Switch to Production environment'
        }
    }
    
    # Read the server.py file
    try:
        content = Path(file_path).read_text()
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return False
    
    validation_results = []
    
    # Check each function
    for func_name, required_attrs in required_patterns.items():
        print(f"\n🔍 Validating {func_name}...")
        
        # Extract function content
        func_pattern = rf'def {func_name}\([^)]*\):(.*?)(?=\ndef|\Z)'
        func_match = re.search(func_pattern, content, re.DOTALL)
        
        if not func_match:
            print(f"❌ Function {func_name} not found!")
            validation_results.append(False)
            continue
            
        func_content = func_match.group(1)
        
        # Check each required attribute
        func_valid = True
        for attr_name, expected_value in required_attrs.items():
            if expected_value in func_content:
                print(f"   ✅ {attr_name}: Found '{expected_value}'")
            else:
                print(f"   ❌ {attr_name}: Missing '{expected_value}'")
                func_valid = False
        
        validation_results.append(func_valid)
    
    return all(validation_results)

def validate_forbidden_patterns(file_path):
    """Check for patterns that indicate regressions."""
    
    forbidden_patterns = {
        "role='group' in PROFILE dropdown": {
            'pattern': r'profile-dropdown-menu.*role=[\'"]group[\'"]',
            'message': 'PROFILE dropdown should NOT have role="group" (causes width issues)'
        },
        "Missing ARIA in APP dropdown": {
            'pattern': r'create_menu_container.*return Details\(Summary\([^)]*\), Ul\([^)]*\), cls=[\'"]dropdown[\'"]',
            'message': 'APP dropdown appears to be missing ARIA attributes'
        }
    }
    
    content = Path(file_path).read_text()
    
    print(f"\n🚨 Checking for forbidden regression patterns...")
    
    regression_found = False
    for check_name, check_info in forbidden_patterns.items():
        if re.search(check_info['pattern'], content):
            print(f"   ❌ {check_name}: {check_info['message']}")
            regression_found = True
        else:
            print(f"   ✅ {check_name}: OK")
    
    return not regression_found

def main():
    """Main validation function."""
    
    print("🛡️  ARIA ACCESSIBILITY VALIDATION")
    print("=" * 50)
    
    server_path = "server.py"
    
    # Run validations
    aria_valid = validate_dropdown_aria(server_path)
    regression_safe = validate_forbidden_patterns(server_path)
    
    print(f"\n📊 VALIDATION RESULTS:")
    print(f"   ARIA Attributes: {'✅ PASS' if aria_valid else '❌ FAIL'}")
    print(f"   Regression Check: {'✅ PASS' if regression_safe else '❌ FAIL'}")
    
    if aria_valid and regression_safe:
        print(f"\n🎉 ALL VALIDATIONS PASSED! Accessibility is protected.")
        return 0
    else:
        print(f"\n💥 VALIDATION FAILED! Fix issues before committing.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 