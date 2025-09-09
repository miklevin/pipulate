#!/usr/bin/env python3
"""
Landing Page Standardization Helper Script

Automatically applies the Phase 2 "Landing Page Standardization" pattern across
eligible plugins. This script:

1. Identifies plugins with standard landing page boilerplate
2. Shows preview of proposed changes
3. Applies the standardization with user confirmation
4. Preserves unique plugin characteristics

Usage:
    python helpers/cleanup/standardize_landing_pages.py --analyze    # Preview only
    python helpers/cleanup/standardize_landing_pages.py --apply     # Apply changes
    python helpers/cleanup/standardize_landing_pages.py --force     # Apply without confirmation
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set


class LandingPageStandardizer:
    """Automates the standardization of landing page methods across plugins."""
    
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.eligible_plugins: List[Path] = []
        self.ineligible_plugins: Dict[Path, str] = {}
        self.analysis_results: Dict[Path, Dict] = {}
        
        # Patterns that indicate a standard landing page
        self.standard_patterns = [
            r'pip\.generate_pipeline_key',
            r'Container\s*\(',
            r'Card\s*\(',
            r'Form\s*\(',
            r'pipeline_id.*list.*pipeline-ids',
            r'hx_post.*init',
            r'Datalist.*Option'
        ]
        
        # Patterns that indicate non-standard (custom) implementation
        self.custom_patterns = [
            r'class.*(?:Connect|Roadmap|Introduction|Documentation)',  # Special purpose classes
            r'render_items',  # Display-only plugins
            r'async def landing.*render_items',  # Non-workflow plugins
            r'mermaid|diagram',  # Visualization plugins
            r'get_endpoint_message',  # Dynamic message generation
        ]

    def analyze_all_plugins(self) -> None:
        """Analyze all plugins to determine eligibility for standardization."""
        plugin_files = sorted(self.plugins_dir.glob("*.py"))
        
        for plugin_file in plugin_files:
            if plugin_file.name.startswith('__'):
                continue
                
            try:
                analysis = self.analyze_plugin(plugin_file)
                self.analysis_results[plugin_file] = analysis
                
                if analysis['eligible']:
                    self.eligible_plugins.append(plugin_file)
                else:
                    self.ineligible_plugins[plugin_file] = analysis['reason']
                    
            except Exception as e:
                self.ineligible_plugins[plugin_file] = f"Analysis error: {str(e)}"

    def analyze_plugin(self, plugin_file: Path) -> Dict:
        """Analyze a single plugin for landing page standardization eligibility."""
        content = plugin_file.read_text(encoding='utf-8')
        
        # Quick exclusions
        if any(re.search(pattern, content, re.IGNORECASE) for pattern in self.custom_patterns):
            return {
                'eligible': False,
                'reason': 'Custom/special purpose plugin',
                'current_lines': 0,
                'standard_score': 0
            }
        
        # Find the landing method
        landing_method = self.extract_landing_method(content)
        if not landing_method:
            return {
                'eligible': False,
                'reason': 'No standard landing method found',
                'current_lines': 0,
                'standard_score': 0
            }
        
        # Check for standard patterns
        standard_score = sum(1 for pattern in self.standard_patterns 
                           if re.search(pattern, landing_method, re.IGNORECASE))
        
        # Count lines in current landing method
        current_lines = len([line for line in landing_method.split('\n') 
                           if line.strip() and not line.strip().startswith('#')])
        
        # Eligibility criteria
        eligible = (
            standard_score >= 4 and  # Must have most standard patterns
            current_lines >= 8 and   # Must have significant boilerplate
            'pip.create_standard_landing_page' not in landing_method  # Not already standardized
        )
        
        return {
            'eligible': eligible,
            'reason': self.get_ineligibility_reason(standard_score, current_lines, landing_method),
            'current_lines': current_lines,
            'standard_score': standard_score,
            'landing_method': landing_method
        }

    def extract_landing_method(self, content: str) -> Optional[str]:
        """Extract the landing method from plugin content."""
        lines = content.split('\n')
        start_idx = None
        end_idx = None
        
        # Find the start of the landing method
        for i, line in enumerate(lines):
            if re.search(r'^\s*async def landing\s*\(', line):
                start_idx = i
                break
        
        if start_idx is None:
            return None
        
        # Find the indentation level of the method
        method_line = lines[start_idx]
        method_indent = len(method_line) - len(method_line.lstrip())
        
        # Find the end of the method by looking for the next method at the same or lower indentation
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.strip() == '':  # Skip empty lines
                continue
            
            # Check if this line starts a new method/function at the same or lower indentation
            line_indent = len(line) - len(line.lstrip())
            if (line_indent <= method_indent and 
                (re.search(r'^\s*(async\s+)?def\s+', line) or 
                 re.search(r'^\s*class\s+', line) or
                 re.search(r'^\s*#\s*---', line))):  # Also stop at comment markers
                end_idx = i
                break
        
        if end_idx is None:
            end_idx = len(lines)
        
        # Extract the method
        method_lines = lines[start_idx:end_idx]
        return '\n'.join(method_lines)

    def get_ineligibility_reason(self, standard_score: int, current_lines: int, landing_method: str) -> str:
        """Determine why a plugin is not eligible for standardization."""
        if 'pip.create_standard_landing_page' in landing_method:
            return 'Already standardized'
        elif standard_score < 4:
            return f'Non-standard pattern (score: {standard_score}/7)'
        elif current_lines < 8:
            return f'Too simple (only {current_lines} lines)'
        else:
            return 'Eligible'

    def preview_changes(self) -> None:
        """Preview what changes would be made to eligible plugins."""
        print("\n🔍 LANDING PAGE STANDARDIZATION ANALYSIS")
        print("=" * 60)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total plugins analyzed: {len(self.analysis_results)}")
        print(f"   ✅ Eligible for standardization: {len(self.eligible_plugins)}")
        print(f"   ❌ Not eligible: {len(self.ineligible_plugins)}")
        
        if self.eligible_plugins:
            print(f"\n✅ ELIGIBLE PLUGINS ({len(self.eligible_plugins)}):")
            for plugin_file in self.eligible_plugins:
                analysis = self.analysis_results[plugin_file]
                savings = analysis['current_lines'] - 3  # Standardized method is ~3 lines
                print(f"   📄 {plugin_file.name}")
                print(f"      Current: {analysis['current_lines']} lines → Standardized: 3 lines (−{savings} lines)")
                print(f"      Pattern score: {analysis['standard_score']}/7")
        
        if self.ineligible_plugins:
            print(f"\n❌ INELIGIBLE PLUGINS ({len(self.ineligible_plugins)}):")
            by_reason = {}
            for plugin_file, reason in self.ineligible_plugins.items():
                by_reason.setdefault(reason, []).append(plugin_file.name)
            
            for reason, files in by_reason.items():
                print(f"   🔸 {reason}: {len(files)} plugins")
                for file in sorted(files)[:3]:  # Show first 3
                    print(f"      • {file}")
                if len(files) > 3:
                    print(f"      • ... and {len(files) - 3} more")

    def apply_standardization(self, force: bool = False) -> None:
        """Apply standardization to eligible plugins."""
        if not self.eligible_plugins:
            print("No eligible plugins found.")
            return
        
        if not force:
            response = input(f"\nProceed with standardization of {len(self.eligible_plugins)} plugins? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Cancelled.")
                return
        
        success_count = 0
        for plugin_file in self.eligible_plugins:
            try:
                if self.standardize_plugin(plugin_file):
                    success_count += 1
                    print(f"✅ Standardized: {plugin_file.name}")
                else:
                    print(f"❌ Failed: {plugin_file.name}")
            except Exception as e:
                print(f"❌ Error in {plugin_file.name}: {str(e)}")
        
        print(f"\n🎉 Successfully standardized: {success_count}/{len(self.eligible_plugins)} plugins")

    def standardize_plugin(self, plugin_file: Path) -> bool:
        """Standardize a single plugin's landing method with proper indentation."""
        content = plugin_file.read_text(encoding='utf-8')
        analysis = self.analysis_results[plugin_file]
        landing_method = analysis['landing_method']
        
        # Detect the base indentation of the method
        lines = landing_method.split('\n')
        method_line = lines[0]  # The "async def landing..." line
        
        # Find the indentation by looking at the method definition line
        base_indent = len(method_line) - len(method_line.lstrip())
        method_indent = ' ' * base_indent
        body_indent = ' ' * (base_indent + 4)  # Method body is indented 4 more spaces
        
        # Create properly indented replacement
        standardized_method = f'''{method_indent}async def landing(self, request):
{body_indent}"""Generate the landing page using the standardized helper while maintaining WET explicitness."""
{body_indent}pip = self.pipulate
{body_indent}
{body_indent}# Use centralized landing page helper - maintains WET principle by explicit call
{body_indent}return pip.create_standard_landing_page(self)'''
        
        # Replace the method
        new_content = content.replace(landing_method, standardized_method)
        
        # Verify the replacement worked
        if new_content == content:
            return False
        
        # Create backup before writing
        backup_file = plugin_file.with_suffix('.py.backup_landing')
        backup_file.write_text(content, encoding='utf-8')
        
        # Write the standardized version
        plugin_file.write_text(new_content, encoding='utf-8')
        return True


def main():
    parser = argparse.ArgumentParser(description='Standardize landing pages across Pipulate plugins')
    parser.add_argument('--analyze', action='store_true', help='Analyze plugins and show preview only')
    parser.add_argument('--apply', action='store_true', help='Apply standardization with confirmation')
    parser.add_argument('--force', action='store_true', help='Apply standardization without confirmation')
    parser.add_argument('--test', type=str, help='Test on single plugin file')
    
    args = parser.parse_args()
    
    plugins_dir = Path('plugins')
    if not plugins_dir.exists():
        plugins_dir = Path.cwd() / 'plugins'
        if not plugins_dir.exists():
            plugins_dir = Path('pipulate/plugins')
            if not plugins_dir.exists():
                print("Error: Plugins directory not found")
                sys.exit(1)
    
    standardizer = LandingPageStandardizer(plugins_dir)
    
    if args.test:
        # Test on single file
        test_file = plugins_dir / args.test
        if test_file.exists():
            analysis = standardizer.analyze_plugin(test_file)
            print(f"Test file: {test_file.name}")
            print(f"Eligible: {analysis['eligible']}")
            print(f"Reason: {analysis['reason']}")
            print(f"Lines: {analysis['current_lines']}")
            print(f"Score: {analysis['standard_score']}")
            
            if analysis['eligible']:
                print("\nTesting standardization...")
                # Store the analysis for the standardize method
                standardizer.analysis_results[test_file] = analysis
                if standardizer.standardize_plugin(test_file):
                    print("✅ Test standardization successful!")
                    print("Run: git diff to see the changes")
                else:
                    print("❌ Test standardization failed")
        else:
            print(f"Test file not found: {args.test}")
        return
    
    standardizer.analyze_all_plugins()
    
    if args.apply or args.force:
        standardizer.preview_changes()
        standardizer.apply_standardization(force=args.force)
    else:
        standardizer.preview_changes()


if __name__ == '__main__':
    main() 