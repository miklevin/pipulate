#!/usr/bin/env python3
"""
Conservative Formatter for Pipulate Codebase

Philosophy: Surgical precision over sledgehammer formatting.
- Respects deliberate aesthetic line-wrapping decisions
- Fixes obvious spacing and consistency issues
- Preserves beautiful multi-line expressions
- Uses incremental, reviewable changes

Usage:
    python helpers/cleanup/conservative_formatter.py --analyze plugins/
    python helpers/cleanup/conservative_formatter.py --imports plugins/
    python helpers/cleanup/conservative_formatter.py --spacing plugins/
    python helpers/cleanup/conservative_formatter.py --all plugins/
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
import subprocess


class ConservativeFormatter:
    """Conservative code formatter that preserves aesthetic decisions."""
    
    def __init__(self, target_path: Path):
        self.target_path = target_path
        self.issues_found = {
            'import_sorting': [],
            'method_spacing': [],
            'trailing_whitespace': [],
            'basic_spacing': []
        }
        self.fixes_applied = {
            'import_sorting': 0,
            'method_spacing': 0,
            'trailing_whitespace': 0,
            'basic_spacing': 0
        }
    
    def analyze_all_files(self) -> None:
        """Analyze all Python files and identify formatting issues."""
        python_files = list(self.target_path.rglob("*.py"))
        
        print(f"🔍 CONSERVATIVE FORMATTING ANALYSIS")
        print(f"=" * 50)
        print(f"Analyzing {len(python_files)} Python files...\n")
        
        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue
                
            self._analyze_file(py_file)
        
        self._print_analysis_summary()
    
    def _should_skip_file(self, py_file: Path) -> bool:
        """Check if file should be skipped."""
        # Skip __pycache__ and other generated files
        if '__pycache__' in str(py_file):
            return True
        
        # Skip files that start with xx_ or contain parentheses
        name = py_file.name
        if name.startswith(('xx_', 'XX_')) or '(' in name or ')' in name:
            return True
            
        return False
    
    def _analyze_file(self, py_file: Path) -> None:
        """Analyze a single Python file for formatting issues."""
        try:
            content = py_file.read_text(encoding='utf-8')
            
            # Check import sorting
            if self._needs_import_sorting(content):
                self.issues_found['import_sorting'].append(py_file)
            
            # Check method spacing
            spacing_issues = self._check_method_spacing(content)
            if spacing_issues:
                self.issues_found['method_spacing'].append((py_file, spacing_issues))
            
            # Check trailing whitespace
            if self._has_trailing_whitespace(content):
                self.issues_found['trailing_whitespace'].append(py_file)
            
            # Check basic spacing (very conservative)
            basic_issues = self._check_basic_spacing(content)
            if basic_issues:
                self.issues_found['basic_spacing'].append((py_file, basic_issues))
                
        except Exception as e:
            print(f"⚠️ Error analyzing {py_file}: {e}")
    
    def _needs_import_sorting(self, content: str) -> bool:
        """Check if imports need sorting (using isort in check mode)."""
        try:
            result = subprocess.run(
                ['isort', '--check-only', '--diff', '--quiet', '-'],
                input=content,
                text=True,
                capture_output=True
            )
            return result.returncode != 0
        except subprocess.SubprocessError:
            return False
    
    def _check_method_spacing(self, content: str) -> List[str]:
        """Check for missing blank lines between methods."""
        lines = content.split('\n')
        issues = []
        
        for i in range(len(lines) - 1):
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            # Look for method definitions followed immediately by another method
            if (re.match(r'^\s*(async\s+)?def\s+\w+', lines[i]) and 
                re.match(r'^\s*(async\s+)?def\s+\w+', lines[i + 1])):
                issues.append(f"Line {i + 1}: Missing blank line between methods")
            
            # Look for method ending followed immediately by another method
            elif (current_line and not current_line.startswith('#') and 
                  re.match(r'^\s*(async\s+)?def\s+\w+', lines[i + 1])):
                # Check if there's proper indentation (method is at class level)
                current_indent = len(lines[i]) - len(lines[i].lstrip())
                next_indent = len(lines[i + 1]) - len(lines[i + 1].lstrip())
                
                if current_indent >= next_indent and current_indent > 0:
                    issues.append(f"Line {i + 2}: Missing blank line before method")
        
        return issues
    
    def _has_trailing_whitespace(self, content: str) -> bool:
        """Check for trailing whitespace."""
        lines = content.split('\n')
        return any(line.endswith(' ') or line.endswith('\t') for line in lines)
    
    def _check_basic_spacing(self, content: str) -> List[str]:
        """Check for very basic spacing issues (conservative)."""
        lines = content.split('\n')
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Only check for the most obvious issues
            
            # Missing space after comma (but not in strings)
            if ',,' in line:
                issues.append(f"Line {i}: Double comma found")
            
            # Multiple spaces where one would do (but preserve alignment)
            if '  =' in line and '==' not in line and '!=' not in line:
                # Only flag if it's clearly not intentional alignment
                stripped = line.lstrip()
                if stripped.startswith('=') or '  =' not in stripped[:20]:
                    continue  # Likely intentional alignment
                issues.append(f"Line {i}: Extra spaces before =")
        
        return issues
    
    def _print_analysis_summary(self) -> None:
        """Print summary of analysis results."""
        total_issues = (len(self.issues_found['import_sorting']) + 
                       len(self.issues_found['method_spacing']) + 
                       len(self.issues_found['trailing_whitespace']) + 
                       len(self.issues_found['basic_spacing']))
        
        print(f"📊 ANALYSIS SUMMARY:")
        print(f"   🔄 Import sorting needed: {len(self.issues_found['import_sorting'])} files")
        print(f"   📏 Method spacing issues: {len(self.issues_found['method_spacing'])} files")
        print(f"   🧹 Trailing whitespace: {len(self.issues_found['trailing_whitespace'])} files")
        print(f"   ⚡ Basic spacing issues: {len(self.issues_found['basic_spacing'])} files")
        print(f"   📈 Total files needing attention: {total_issues}")
        
        if self.issues_found['import_sorting']:
            print(f"\n🔄 FILES NEEDING IMPORT SORTING:")
            for file_path in self.issues_found['import_sorting'][:10]:  # Show first 10
                print(f"   📄 {file_path.name}")
            if len(self.issues_found['import_sorting']) > 10:
                print(f"   ... and {len(self.issues_found['import_sorting']) - 10} more")
        
        if self.issues_found['method_spacing']:
            print(f"\n📏 FILES NEEDING METHOD SPACING:")
            for file_path, issues in self.issues_found['method_spacing'][:5]:  # Show first 5
                print(f"   📄 {file_path.name} ({len(issues)} issues)")
            if len(self.issues_found['method_spacing']) > 5:
                print(f"   ... and {len(self.issues_found['method_spacing']) - 5} more files")
    
    def fix_imports(self, apply: bool = False) -> None:
        """Fix import sorting using isort."""
        if not self.issues_found['import_sorting']:
            print("✅ No import sorting issues found!")
            return
        
        if not apply:
            print(f"🔄 IMPORT SORTING PREVIEW:")
            print(f"Would fix imports in {len(self.issues_found['import_sorting'])} files")
            print("Use --apply-imports to make changes")
            return
        
        print(f"🔄 APPLYING IMPORT SORTING...")
        
        for py_file in self.issues_found['import_sorting']:
            try:
                # Use isort with conservative settings
                result = subprocess.run(
                    ['isort', '--profile=pep8', '--line-length=120', '--multi-line=3', str(py_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.fixes_applied['import_sorting'] += 1
                    print(f"✅ Fixed imports: {py_file.name}")
                else:
                    print(f"❌ Failed to fix imports: {py_file.name}")
                    
            except subprocess.SubprocessError as e:
                print(f"❌ Error fixing imports in {py_file.name}: {e}")
        
        print(f"\n🎉 Import sorting complete: {self.fixes_applied['import_sorting']} files fixed")
    
    def fix_method_spacing(self, apply: bool = False) -> None:
        """Fix method spacing by adding blank lines where needed."""
        if not self.issues_found['method_spacing']:
            print("✅ No method spacing issues found!")
            return
        
        if not apply:
            print(f"📏 METHOD SPACING PREVIEW:")
            for file_path, issues in self.issues_found['method_spacing'][:5]:
                print(f"   📄 {file_path.name}: {len(issues)} spacing issues")
            print("Use --apply-spacing to make changes")
            return
        
        print(f"📏 APPLYING METHOD SPACING FIXES...")
        
        for py_file, issues in self.issues_found['method_spacing']:
            try:
                content = py_file.read_text(encoding='utf-8')
                fixed_content = self._fix_method_spacing_in_content(content)
                
                if fixed_content != content:
                    py_file.write_text(fixed_content, encoding='utf-8')
                    self.fixes_applied['method_spacing'] += 1
                    print(f"✅ Fixed spacing: {py_file.name}")
                    
            except Exception as e:
                print(f"❌ Error fixing spacing in {py_file.name}: {e}")
        
        print(f"\n🎉 Method spacing complete: {self.fixes_applied['method_spacing']} files fixed")
    
    def _fix_method_spacing_in_content(self, content: str) -> str:
        """Fix method spacing in content by adding blank lines."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # Look ahead to see if we need to add a blank line
            if i < len(lines) - 1:
                next_line = lines[i + 1]
                
                # Add blank line before method if missing
                if (re.match(r'^\s*(async\s+)?def\s+\w+', next_line) and 
                    line.strip() and not line.strip().startswith('#')):
                    
                    # Check indentation to make sure it's a class method
                    current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
                    next_indent = len(next_line) - len(next_line.lstrip())
                    
                    if current_indent >= next_indent and next_indent > 0:
                        # Add blank line if not already there
                        if not line.strip() == '':
                            fixed_lines.append('')
        
        return '\n'.join(fixed_lines)
    
    def fix_trailing_whitespace(self, apply: bool = False) -> None:
        """Remove trailing whitespace."""
        if not self.issues_found['trailing_whitespace']:
            print("✅ No trailing whitespace found!")
            return
        
        if not apply:
            print(f"🧹 TRAILING WHITESPACE PREVIEW:")
            print(f"Would clean trailing whitespace in {len(self.issues_found['trailing_whitespace'])} files")
            print("Use --apply-whitespace to make changes")
            return
        
        print(f"🧹 REMOVING TRAILING WHITESPACE...")
        
        for py_file in self.issues_found['trailing_whitespace']:
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Remove trailing whitespace from each line
                lines = content.split('\n')
                fixed_lines = [line.rstrip() for line in lines]
                fixed_content = '\n'.join(fixed_lines)
                
                py_file.write_text(fixed_content, encoding='utf-8')
                self.fixes_applied['trailing_whitespace'] += 1
                print(f"✅ Cleaned whitespace: {py_file.name}")
                
            except Exception as e:
                print(f"❌ Error cleaning whitespace in {py_file.name}: {e}")
        
        print(f"\n🎉 Whitespace cleanup complete: {self.fixes_applied['trailing_whitespace']} files fixed")


def main():
    parser = argparse.ArgumentParser(description='Conservative code formatter for Pipulate')
    parser.add_argument('target', help='Target directory or file to format')
    parser.add_argument('--analyze', action='store_true', help='Analyze files and show issues')
    parser.add_argument('--imports', action='store_true', help='Preview import sorting fixes')
    parser.add_argument('--apply-imports', action='store_true', help='Apply import sorting fixes')
    parser.add_argument('--spacing', action='store_true', help='Preview method spacing fixes')
    parser.add_argument('--apply-spacing', action='store_true', help='Apply method spacing fixes')
    parser.add_argument('--whitespace', action='store_true', help='Preview trailing whitespace fixes')
    parser.add_argument('--apply-whitespace', action='store_true', help='Apply trailing whitespace fixes')
    parser.add_argument('--all', action='store_true', help='Preview all fixes')
    parser.add_argument('--apply-all', action='store_true', help='Apply all fixes')
    
    args = parser.parse_args()
    
    target_path = Path(args.target)
    if not target_path.exists():
        print(f"Error: {target_path} does not exist")
        sys.exit(1)
    
    formatter = ConservativeFormatter(target_path)
    
    # Always analyze first
    formatter.analyze_all_files()
    
    if args.analyze:
        return  # Just show analysis
    
    if args.imports or args.all:
        formatter.fix_imports(apply=False)
    
    if args.apply_imports or args.apply_all:
        formatter.fix_imports(apply=True)
    
    if args.spacing or args.all:
        formatter.fix_method_spacing(apply=False)
    
    if args.apply_spacing or args.apply_all:
        formatter.fix_method_spacing(apply=True)
    
    if args.whitespace or args.all:
        formatter.fix_trailing_whitespace(apply=False)
    
    if args.apply_whitespace or args.apply_all:
        formatter.fix_trailing_whitespace(apply=True)
    
    # Summary
    total_fixes = sum(formatter.fixes_applied.values())
    if total_fixes > 0:
        print(f"\n🎉 FORMATTING COMPLETE:")
        print(f"   Total files improved: {total_fixes}")
        print(f"   Ready for git commit!")


if __name__ == '__main__':
    main() 