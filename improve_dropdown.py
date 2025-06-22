#!/usr/bin/env python3
"""
Dropdown Component Automation Improvement Script

This script analyzes the 530_dropdown.py component and applies automation improvements
based on the successful pattern used for previous components.
"""

import os
import re
import shutil
from datetime import datetime

def analyze_dropdown_component():
    """Analyze the current state of the dropdown component"""
    plugin_path = "plugins/530_dropdown.py"
    
    if not os.path.exists(plugin_path):
        return {"error": "Plugin file not found"}
    
    with open(plugin_path, 'r') as f:
        content = f.read()
    
    # Check for automation attributes
    analysis = {
        "has_data_testid": bool(re.search(r'data_testid=', content)),
        "has_aria_labels": bool(re.search(r'aria_label=', content)),
        "has_ui_constants": bool(re.search(r'UI_CONSTANTS', content)),
        "has_template_markers": bool(re.search(r'STEPS_LIST_INSERTION_POINT', content)),
        "select_elements": len(re.findall(r'Select\(', content)),
        "option_elements": len(re.findall(r'Option\(', content)),
        "button_elements": len(re.findall(r'Button\(', content)),
        "form_elements": len(re.findall(r'Form\(', content))
    }
    
    # Calculate automation score
    score = 0
    if analysis["select_elements"] > 0 or analysis["option_elements"] > 0:
        score += 20
    if analysis["button_elements"] > 0:
        score += 20
    if analysis["has_data_testid"]:
        score += 25
    if analysis["has_aria_labels"]:
        score += 25
    if analysis["has_ui_constants"]:
        score += 10
    
    analysis["automation_score"] = score
    analysis["needs_improvement"] = score < 80
    
    return analysis

def backup_original_plugin():
    """Create a backup of the original plugin"""
    original_path = "plugins/530_dropdown.py"
    backup_path = "plugins/530_dropdown.py.backup"
    
    if os.path.exists(original_path) and not os.path.exists(backup_path):
        shutil.copy2(original_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    return False

def apply_automation_improvements():
    """Apply comprehensive automation improvements to the dropdown component"""
    plugin_path = "plugins/530_dropdown.py"
    
    with open(plugin_path, 'r') as f:
        content = f.read()
    
    # Add UI_CONSTANTS after the class definition
    ui_constants_code = '''
    # UI Constants for automation testing
    UI_CONSTANTS = {
        'DROPDOWN_SELECT': 'dropdown-widget-select-input',
        'DROPDOWN_OPTION': 'dropdown-widget-option',
        'FINALIZE_BUTTON': 'dropdown-widget-finalize-button', 
        'UNLOCK_BUTTON': 'dropdown-widget-unlock-button',
        'NEXT_BUTTON': 'dropdown-widget-next-button',
        'REVERT_BUTTON': 'dropdown-widget-revert-button'
    }
'''
    
    # Insert UI_CONSTANTS after the class docstring
    class_pattern = r'(class DropdownWidget:.*?""".*?""")'
    if re.search(class_pattern, content, re.DOTALL):
        content = re.sub(class_pattern, r'\1' + ui_constants_code, content, flags=re.DOTALL)
    
    # Add template compatibility markers
    template_markers = '''
    # Template compatibility markers
    # STEPS_LIST_INSERTION_POINT
    # STEP_METHODS_INSERTION_POINT
'''
    
    # Insert template markers after UI_CONSTANTS
    if 'UI_CONSTANTS' in content:
        content = content.replace('UI_CONSTANTS = {', template_markers + '\n    UI_CONSTANTS = {')
    
    # Enhance select elements with automation attributes
    select_pattern = r'Select\([^)]*\)'
    def enhance_select(match):
        select_content = match.group(0)
        if 'data_testid=' not in select_content:
            # Add data_testid and aria_label
            enhanced = select_content.replace(
                'Select(',
                'Select(data_testid=\'dropdown-widget-select-input\', aria_label=\'Dropdown selection widget\', '
            )
            return enhanced
        return select_content
    
    content = re.sub(select_pattern, enhance_select, content)
    
    # Enhance option elements with automation attributes
    option_pattern = r'Option\([^)]*\)'
    def enhance_option(match):
        option_content = match.group(0)
        if 'data_testid=' not in option_content:
            # Add data_testid
            enhanced = option_content.replace(
                'Option(',
                'Option(data_testid=\'dropdown-widget-option\', '
            )
            return enhanced
        return option_content
    
    content = re.sub(option_pattern, enhance_option, content)
    
    # Enhance buttons with automation attributes
    button_patterns = [
        (r'Button\(\'Finalize 🔒\'[^)]*\)', 'data_testid=\'dropdown-widget-finalize-button\', aria_label=\'Finalize dropdown workflow\''),
        (r'Button\(pip\.UNLOCK_BUTTON_LABEL[^)]*\)', 'data_testid=\'dropdown-widget-unlock-button\', aria_label=\'Unlock dropdown for editing\''),
        (r'Button\(\'Next ▸\'[^)]*\)', 'data_testid=\'dropdown-widget-next-button\', aria_label=\'Proceed to next step\''),
    ]
    
    for pattern, attributes in button_patterns:
        def enhance_button(match):
            button_content = match.group(0)
            if 'data_testid=' not in button_content:
                # Insert before the closing parenthesis
                enhanced = button_content.rstrip(')')
                if not enhanced.endswith(', '):
                    enhanced += ', '
                enhanced += attributes + ')'
                return enhanced
            return button_content
        
        content = re.sub(pattern, enhance_button, content)
    
    # Enhance form elements
    form_pattern = r'Form\([^)]*hx_post=[^)]*\)'
    def enhance_form(match):
        form_content = match.group(0)
        if 'data_testid=' not in form_content:
            enhanced = form_content.replace(
                'hx_post=',
                'data_testid=\'dropdown-widget-form\', aria_label=\'Dropdown selection form\', hx_post='
            )
            return enhanced
        return form_content
    
    content = re.sub(form_pattern, enhance_form, content)
    
    # Save the improved content
    with open(plugin_path, 'w') as f:
        f.write(content)
    
    print("✅ Applied automation improvements to dropdown component")
    return True

def verify_improvements():
    """Verify that the improvements were applied correctly"""
    plugin_path = "plugins/530_dropdown.py"
    
    with open(plugin_path, 'r') as f:
        content = f.read()
    
    checks = {
        "UI_CONSTANTS present": 'UI_CONSTANTS' in content,
        "Template markers present": 'STEPS_LIST_INSERTION_POINT' in content,
        "Select data-testid": 'dropdown-widget-select-input' in content,
        "Select aria-label": 'aria_label=\'Dropdown selection widget\'' in content,
        "Button automation attributes": 'dropdown-widget-finalize-button' in content,
    }
    
    print("\n=== VERIFICATION RESULTS ===")
    all_passed = True
    for check, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {check}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED! Component ready for automation testing.")
    else:
        print("\n⚠️  Some checks failed. Manual review may be needed.")
    
    return all_passed

def main():
    """Main execution function"""
    print("🔍 Dropdown Component Automation Improvement")
    print("=" * 50)
    
    # Step 1: Analyze current state
    print("\n📊 Analyzing current component state...")
    analysis = analyze_dropdown_component()
    
    if "error" in analysis:
        print(f"❌ Error: {analysis['error']}")
        return
    
    print(f"Current automation score: {analysis['automation_score']}/100")
    print(f"Needs improvement: {analysis['needs_improvement']}")
    
    if not analysis['needs_improvement']:
        print("✅ Component already meets automation standards!")
        return
    
    # Step 2: Backup original
    print("\n💾 Creating backup...")
    backup_created = backup_original_plugin()
    
    # Step 3: Apply improvements
    print("\n🔧 Applying automation improvements...")
    improvements_applied = apply_automation_improvements()
    
    if improvements_applied:
        # Step 4: Verify improvements
        print("\n✅ Verifying improvements...")
        verification_passed = verify_improvements()
        
        # Step 5: Re-analyze
        print("\n📊 Re-analyzing improved component...")
        new_analysis = analyze_dropdown_component()
        print(f"New automation score: {new_analysis['automation_score']}/100")
        
        if new_analysis['automation_score'] >= 80:
            print("\n🎉 SUCCESS! Component now meets automation standards!")
        else:
            print(f"\n⚠️  Score improved but still needs work: {new_analysis['automation_score']}/100")
    
    print("\n✨ Dropdown Component improvement complete!")

if __name__ == "__main__":
    main() 