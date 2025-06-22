#!/usr/bin/env python3
"""
Text Area Component Automation Improvement Script

This script analyzes the 520_text_area.py component and applies automation improvements
based on the successful pattern used for the upload component.
"""

import os
import re
import shutil
from datetime import datetime

def analyze_text_area_component():
    """Analyze the current state of the text area component"""
    plugin_path = "plugins/520_text_area.py"
    
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
        "input_elements": len(re.findall(r'Textarea\(', content)),
        "button_elements": len(re.findall(r'Button\(', content)),
        "form_elements": len(re.findall(r'Form\(', content))
    }
    
    # Calculate automation score
    score = 0
    if analysis["input_elements"] > 0:
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
    original_path = "plugins/520_text_area.py"
    backup_path = "plugins/520_text_area.py.backup"
    
    if os.path.exists(original_path) and not os.path.exists(backup_path):
        shutil.copy2(original_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    return False

def apply_automation_improvements():
    """Apply comprehensive automation improvements to the text area component"""
    plugin_path = "plugins/520_text_area.py"
    
    with open(plugin_path, 'r') as f:
        content = f.read()
    
    # Add UI_CONSTANTS after the class definition
    ui_constants_code = '''
    # UI Constants for automation testing
    UI_CONSTANTS = {
        'TEXTAREA_INPUT': 'text-area-widget-textarea-input',
        'FINALIZE_BUTTON': 'text-area-widget-finalize-button', 
        'UNLOCK_BUTTON': 'text-area-widget-unlock-button',
        'NEXT_BUTTON': 'text-area-widget-next-button',
        'REVERT_BUTTON': 'text-area-widget-revert-button'
    }
'''
    
    # Insert UI_CONSTANTS after the class docstring
    class_pattern = r'(class TextAreaWidget:.*?""".*?""")'
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
    
    # Enhance the textarea element with automation attributes
    textarea_pattern = r'Textarea\([^)]*\)'
    def enhance_textarea(match):
        textarea_content = match.group(0)
        if 'data_testid=' not in textarea_content:
            # Add data_testid and aria_label
            enhanced = textarea_content.replace(
                'Textarea(',
                'Textarea('
            ).replace(
                ', cls=\'textarea-standard\'',
                ', cls=\'textarea-standard\', data_testid=\'text-area-widget-textarea-input\', aria_label=\'Multi-line text input area\''
            )
            if ', cls=\'textarea-standard\'' not in enhanced:
                enhanced = enhanced.replace(
                    ', required=True',
                    ', cls=\'textarea-standard\', data_testid=\'text-area-widget-textarea-input\', aria_label=\'Multi-line text input area\', required=True'
                )
            return enhanced
        return textarea_content
    
    content = re.sub(textarea_pattern, enhance_textarea, content)
    
    # Enhance buttons with automation attributes
    button_patterns = [
        (r'Button\(\'Finalize 🔒\'[^)]*\)', 'data_testid=\'text-area-widget-finalize-button\', aria_label=\'Finalize text area workflow\''),
        (r'Button\(pip\.UNLOCK_BUTTON_LABEL[^)]*\)', 'data_testid=\'text-area-widget-unlock-button\', aria_label=\'Unlock text area for editing\''),
        (r'Button\(\'Next ▸\'[^)]*\)', 'data_testid=\'text-area-widget-next-button\', aria_label=\'Proceed to next step\''),
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
                'data_testid=\'text-area-widget-form\', aria_label=\'Text area input form\', hx_post='
            )
            return enhanced
        return form_content
    
    content = re.sub(form_pattern, enhance_form, content)
    
    # Save the improved content
    with open(plugin_path, 'w') as f:
        f.write(content)
    
    print("✅ Applied automation improvements to text area component")
    return True

def verify_improvements():
    """Verify that the improvements were applied correctly"""
    plugin_path = "plugins/520_text_area.py"
    
    with open(plugin_path, 'r') as f:
        content = f.read()
    
    checks = {
        "UI_CONSTANTS present": 'UI_CONSTANTS' in content,
        "Template markers present": 'STEPS_LIST_INSERTION_POINT' in content,
        "Textarea data-testid": 'text-area-widget-textarea-input' in content,
        "Textarea aria-label": 'aria_label=\'Multi-line text input area\'' in content,
        "Button automation attributes": 'text-area-widget-finalize-button' in content,
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
    print("🔍 Text Area Component Automation Improvement")
    print("=" * 50)
    
    # Step 1: Analyze current state
    print("\n📊 Analyzing current component state...")
    analysis = analyze_text_area_component()
    
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
        new_analysis = analyze_text_area_component()
        print(f"New automation score: {new_analysis['automation_score']}/100")
        
        if new_analysis['automation_score'] >= 80:
            print("\n🎉 SUCCESS! Component now meets automation standards!")
        else:
            print(f"\n⚠️  Score improved but still needs work: {new_analysis['automation_score']}/100")
    
    print("\n✨ Text Area Component improvement complete!")

if __name__ == "__main__":
    main() 