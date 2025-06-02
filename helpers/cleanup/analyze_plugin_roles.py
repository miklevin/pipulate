#!/usr/bin/env python3
"""
Plugin Role Analyzer
====================

A one-off cleanup helper to analyze ROLES membership across all plugins.
Scans the plugins directory to identify which roles each plugin belongs to
and reports any unassigned plugins.

This script is designed to be a temporary analysis tool that will itself
eventually be cleaned up.
"""

import ast
import os
from pathlib import Path
from collections import defaultdict, Counter
import re


class RoleAnalyzer(ast.NodeVisitor):
    """AST visitor to extract ROLES variable declarations from Python files."""
    
    def __init__(self):
        self.roles = []
        self.found_roles = False
        
    def visit_Assign(self, node):
        """Visit assignment nodes to find ROLES = [...] declarations."""
        # Check if this is a ROLES assignment
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'ROLES':
                self.found_roles = True
                
                # Extract the assigned value
                if isinstance(node.value, ast.List):
                    # Handle list literals: ROLES = ['Core', 'Tutorial']
                    for element in node.value.elts:
                        if isinstance(element, ast.Constant) and isinstance(element.value, str):
                            self.roles.append(element.value)
                elif isinstance(node.value, ast.Constant):
                    # Handle single values (shouldn't happen, but just in case)
                    if isinstance(node.value.value, str):
                        self.roles.append(node.value.value)
                        
        self.generic_visit(node)


def extract_roles_from_file(filepath):
    """Extract ROLES from a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content)
        analyzer = RoleAnalyzer()
        analyzer.visit(tree)
        
        return analyzer.roles if analyzer.found_roles else None
        
    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}")
        return None


def get_plugin_filename_info(filepath):
    """Extract plugin number and name from filename."""
    filename = filepath.name
    base_name = filename.replace('.py', '')
    
    # Check for numeric prefix pattern (e.g., "030_roles" -> prefix=030, name=roles)
    match = re.match(r'^(\d+)_(.+)$', base_name)
    if match:
        prefix = match.group(1)
        name = match.group(2)
        return prefix, name, True
    else:
        # No numeric prefix
        return None, base_name, False


def analyze_plugin_roles(plugins_dir):
    """Analyze roles across all plugins in the directory."""
    plugins_path = Path(plugins_dir)
    
    if not plugins_path.exists() or not plugins_path.is_dir():
        print(f"Error: {plugins_dir} does not exist or is not a directory")
        return
    
    # Get all Python files in plugins directory (flat, not recursive)
    plugin_files = [f for f in plugins_path.glob('*.py') if f.is_file()]
    
    if not plugin_files:
        print(f"No Python files found in {plugins_dir}")
        return
    
    print(f"Analyzing {len(plugin_files)} plugin files for ROLES membership...\n")
    
    # Data structures for analysis
    plugin_roles = {}  # plugin_name -> list of roles
    role_plugins = defaultdict(list)  # role_name -> list of plugins
    unassigned_plugins = []
    role_counter = Counter()
    
    # Analyze each plugin file
    for plugin_file in sorted(plugin_files):
        prefix, name, has_prefix = get_plugin_filename_info(plugin_file)
        display_name = f"{prefix}_{name}" if has_prefix else name
        
        roles = extract_roles_from_file(plugin_file)
        
        if roles is None:
            # No ROLES variable found
            unassigned_plugins.append((plugin_file.name, display_name))
        elif not roles:
            # Empty ROLES list found
            plugin_roles[display_name] = []
            print(f"📄 {plugin_file.name:<35} → Empty ROLES list")
        else:
            # Roles found
            plugin_roles[display_name] = roles
            role_str = ", ".join(roles)
            print(f"📄 {plugin_file.name:<35} → {role_str}")
            
            # Update counters and reverse mapping
            for role in roles:
                role_plugins[role].append(display_name)
                role_counter[role] += 1
    
    # Summary section
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    # Role distribution
    if role_counter:
        print(f"\n📊 ROLE DISTRIBUTION:")
        print(f"{'='*50}")
        for role, count in role_counter.most_common():
            print(f"🏷️  {role:<20} → {count:>2} plugin(s)")
    
    # Plugins by role
    if role_plugins:
        print(f"\n📂 PLUGINS BY ROLE:")
        print(f"{'='*50}")
        for role in sorted(role_plugins.keys()):
            plugins = role_plugins[role]
            print(f"\n🏷️  {role} ({len(plugins)} plugin(s)):")
            for plugin in sorted(plugins):
                print(f"   • {plugin}")
    
    # Unassigned plugins
    if unassigned_plugins:
        print(f"\n⚠️  UNASSIGNED PLUGINS ({len(unassigned_plugins)}):")
        print(f"{'='*50}")
        print("These plugins have no ROLES variable defined:")
        for filename, display_name in sorted(unassigned_plugins):
            print(f"   • {filename} ({display_name})")
    else:
        print(f"\n✅ All plugins have ROLES assigned!")
    
    # Statistics
    total_plugins = len(plugin_files)
    assigned_plugins = total_plugins - len(unassigned_plugins)
    empty_roles = len([p for p, roles in plugin_roles.items() if not roles])
    
    print(f"\n📈 STATISTICS:")
    print(f"{'='*50}")
    print(f"Total plugins:        {total_plugins}")
    print(f"Assigned plugins:     {assigned_plugins}")
    print(f"Unassigned plugins:   {len(unassigned_plugins)}")
    print(f"Empty ROLES:          {empty_roles}")
    print(f"Unique roles:         {len(role_counter)}")
    
    if total_plugins > 0:
        assignment_rate = (assigned_plugins / total_plugins) * 100
        print(f"Assignment rate:      {assignment_rate:.1f}%")


def main():
    """Main function to run the analysis."""
    # Determine project root (this script is in helpers/cleanup/)
    current_script_path = Path(__file__).resolve()
    
    # Navigate up to project root
    project_root = current_script_path.parent.parent.parent
    if project_root.name != "pipulate":
        print(f"Warning: Expected to be in pipulate project, but found: {project_root.name}")
        print(f"Script path: {current_script_path}")
        print("Continuing anyway...")
    
    plugins_dir = project_root / "plugins"
    
    print("🔍 Plugin Role Analyzer")
    print("=" * 80)
    print(f"Project root: {project_root}")
    print(f"Plugins dir:  {plugins_dir}")
    print()
    
    analyze_plugin_roles(plugins_dir)
    
    print(f"\n{'='*80}")
    print("Analysis complete! 🎯")
    print("This helper script can be safely deleted once you're done with the analysis.")
    print(f"{'='*80}")


if __name__ == "__main__":
    main() 