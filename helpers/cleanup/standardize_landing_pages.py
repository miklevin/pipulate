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
        # Look for async def landing method
        pattern = r'(async def landing\s*\([^)]*\).*?)(?=\n    async def|\n    def|\n\nclass|\n\n\n|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None

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
        
        template = '''    async def landing(self, request):
        """Generate the landing page using the standardized helper while maintaining WET explicitness."""
        pip = self.pipulate
        
        # Use centralized landing page helper - maintains WET principle by explicit call
        return pip.create_standard_landing_page(self)'''
        
        if not force:
            response = input(f"\nProceed with standardization of {len(self.eligible_plugins)} plugins? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Cancelled.")
                return
        
        for plugin_file in self.eligible_plugins:
            analysis = self.analysis_results[plugin_file]
            content = plugin_file.read_text(encoding='utf-8')
            new_content = content.replace(analysis['landing_method'], template)
            plugin_file.write_text(new_content, encoding='utf-8')
            print(f"✅ Standardized: {plugin_file.name}")


def main():
    parser = argparse.ArgumentParser(description='Standardize landing pages across Pipulate plugins')
    parser.add_argument('--analyze', action='store_true', help='Analyze plugins and show preview only')
    parser.add_argument('--apply', action='store_true', help='Apply standardization with confirmation')
    parser.add_argument('--force', action='store_true', help='Apply standardization without confirmation')
    
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
    standardizer.analyze_all_plugins()
    
    if args.apply or args.force:
        standardizer.preview_changes()
        standardizer.apply_standardization(force=args.force)
    else:
        standardizer.preview_changes()


if __name__ == '__main__':
    main() 