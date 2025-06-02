#!/usr/bin/env python3
"""
Normalize Inline CSS Styles in server.py

This script uses AST parsing to find all inline CSS styles (style="...") in server.py
and normalizes them by:
1. Splitting CSS properties
2. Sorting them alphabetically 
3. Reformatting consistently
4. Handling both single-line and multi-line formats

ENHANCED VERSION: Also finds partial matches and semantic patterns for better consolidation.
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set
from collections import defaultdict, Counter


def find_project_root():
    """Find the Pipulate project root by looking for server.py"""
    current = Path.cwd()
    while current != current.parent:
        if (current / "server.py").exists():
            return current
        current = current.parent
    
    # If not found, assume we're already in the right place
    return Path.cwd()


def parse_css_string(css_string: str) -> List[str]:
    """
    Parse a CSS string and return a list of normalized property declarations.
    
    Args:
        css_string: Raw CSS string like "color: red; margin: 10px;"
        
    Returns:
        List of normalized CSS properties sorted alphabetically
    """
    if not css_string or not css_string.strip():
        return []
    
    # Remove extra whitespace and split on semicolons
    properties = []
    for prop in css_string.split(';'):
        prop = prop.strip()
        if prop and ':' in prop:
            # Normalize spacing around colons
            key, value = prop.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                properties.append(f"{key}: {value}")
    
    # Sort alphabetically for consistency
    return sorted(properties)


def reconstruct_css_string(properties: List[str], force_multiline: bool = False) -> str:
    """
    Reconstruct a CSS string from normalized properties.
    
    Args:
        properties: List of normalized CSS properties
        force_multiline: Whether to force multiline format for readability
        
    Returns:
        Formatted CSS string (multiline for 2+ properties, single for 1)
    """
    if not properties:
        return ""
    
    # Use multiline format for 2+ properties OR when forced
    if len(properties) >= 2 or force_multiline:
        # Multi-line format for better readability
        # Each property on its own line with proper spacing
        formatted_props = []
        for i, prop in enumerate(properties):
            if i == len(properties) - 1:
                # Last property - no trailing semicolon in the string
                formatted_props.append(f"'{prop}'")
            else:
                # All other properties - trailing semicolon and space
                formatted_props.append(f"'{prop}; '")
        
        # Join with newlines and proper indentation
        joined = ',\n    '.join(formatted_props)
        return f"(\n    {joined}\n)"
    else:
        # Single property - keep it simple
        return f"'{properties[0]}'"


def extract_string_value(node) -> Optional[str]:
    """
    Extract string value from an AST node, handling concatenation.
    
    Args:
        node: AST node that should represent a string
        
    Returns:
        The string value or None if not a string
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
        return node.s
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # Handle string concatenation
        left = extract_string_value(node.left)
        right = extract_string_value(node.right)
        if left is not None and right is not None:
            return left + right
    elif isinstance(node, ast.JoinedStr):
        # Handle f-strings - for now, we'll skip these as they're complex
        return None
    
    return None


class StyleNormalizer(ast.NodeTransformer):
    """AST transformer that normalizes inline CSS styles."""
    
    def __init__(self):
        self.changes_made = 0
        self.styles_found = []
    
    def visit_keyword(self, node):
        """Visit keyword arguments looking for style= assignments."""
        if node.arg == 'style':
            original_value = extract_string_value(node.value)
            if original_value is not None:
                # Parse and normalize the CSS
                properties = parse_css_string(original_value)
                if properties:
                    # Create a basic normalized version for AST (post-processing will beautify)
                    normalized_value = '; '.join(properties)
                    
                    # Store information about the change
                    self.styles_found.append({
                        'original': original_value,
                        'normalized': normalized_value,
                        'properties': properties,
                        'line': getattr(node, 'lineno', 'unknown')
                    })
                    
                    if original_value != normalized_value:
                        self.changes_made += 1
                        # Update the node with normalized value
                        if isinstance(node.value, ast.Constant):
                            node.value.value = normalized_value
                        elif hasattr(node.value, 's'):  # Python < 3.8
                            node.value.s = normalized_value
        
        return self.generic_visit(node)


def normalize_styles_in_file(file_path: Path) -> Tuple[int, List[dict]]:
    """
    Normalize all inline styles in a Python file.
    
    Args:
        file_path: Path to the Python file to process
        
    Returns:
        Tuple of (number of changes made, list of all styles found)
    """
    print(f"🔍 Analyzing {file_path}...")
    
    # Read the original file
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    try:
        # Parse the AST
        tree = ast.parse(original_content)
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return 0, []
    
    # Transform the AST
    normalizer = StyleNormalizer()
    new_tree = normalizer.visit(tree)
    
    # Convert back to source code
    try:
        import astor
        new_content = astor.to_source(new_tree)
    except ImportError:
        print("⚠️  astor not available, using ast.unparse (Python 3.9+)")
        try:
            new_content = ast.unparse(new_tree)
        except AttributeError:
            print("❌ Need either astor package or Python 3.9+ for ast.unparse")
            return 0, []
    
    # Post-process to create beautiful multi-line styles
    if normalizer.changes_made > 0:
        new_content = convert_to_multiline_styles(new_content)
        print(f"✅ Making {normalizer.changes_made} changes to {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    else:
        print(f"✨ No changes needed in {file_path}")
    
    return normalizer.changes_made, normalizer.styles_found


def convert_to_multiline_styles(content: str) -> str:
    """
    Convert inline styles with multiple properties to beautiful multi-line format.
    
    This function looks for style="..." patterns and converts them to the readable
    parenthesized multi-line format that FastHTML supports.
    
    IMPORTANT: Only converts style attributes in FastHTML components, not CSS inside HTML strings.
    """
    import re
    
    def replace_style(match):
        full_match = match.group(0)
        style_content = match.group(1)
        
        # Skip if this looks like it's inside an HTML template string
        # Check for common HTML template patterns before the match
        before_match = content[:match.start()]
        recent_context = before_match[-200:] if len(before_match) > 200 else before_match
        
        # Skip if we're inside HTML template strings (f-strings, triple quotes, etc.)
        if ('"""' in recent_context or "'''" in recent_context or 
            'HTMLResponse(' in recent_context or 
            'f"""' in recent_context or
            "f'''" in recent_context or
            '\n' in style_content):  # Skip if style content has newlines (template formatting)
            return full_match
        
        # Parse the CSS properties
        properties = parse_css_string(style_content)
        
        if len(properties) >= 2:
            # Multi-line format for 2+ properties
            formatted_props = []
            for i, prop in enumerate(properties):
                if i == len(properties) - 1:
                    # Last property - no trailing semicolon
                    formatted_props.append(f"'{prop}'")
                else:
                    # All other properties - trailing semicolon and space
                    formatted_props.append(f"'{prop}; '")
            
            # Join with proper indentation
            joined = ',\n        '.join(formatted_props)
            return f"style=(\n        {joined}\n    )"
        else:
            # Single property - keep it simple
            return f"style='{properties[0]}'" if properties else full_match
    
    # Pattern to match style="..." (handles both single and double quotes)
    style_pattern = r'style=["\']([^"\']*)["\']'
    
    # Replace all matches
    result = re.sub(style_pattern, replace_style, content)
    
    return result


def categorize_properties():
    """Define semantic categories for CSS properties."""
    return {
        'layout': {
            'display', 'position', 'top', 'right', 'bottom', 'left', 'float', 'clear',
            'flex', 'flex-direction', 'flex-wrap', 'justify-content', 'align-items', 
            'align-content', 'grid', 'grid-template-columns', 'grid-template-rows',
            'overflow', 'overflow-x', 'overflow-y', 'z-index'
        },
        'spacing': {
            'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'gap'
        },
        'sizing': {
            'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
            'box-sizing'
        },
        'visual': {
            'background', 'background-color', 'background-image', 'background-size',
            'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
            'border-radius', 'border-color', 'border-width', 'border-style',
            'box-shadow', 'opacity'
        },
        'typography': {
            'font-family', 'font-size', 'font-weight', 'font-style', 'line-height',
            'text-align', 'text-decoration', 'text-transform', 'color',
            'white-space', 'word-wrap', 'text-overflow'
        },
        'interaction': {
            'cursor', 'pointer-events', 'user-select'
        }
    }


def find_partial_matches(all_styles: List[dict], min_shared_props: int = 2, min_occurrences: int = 3):
    """Find styles that share common properties."""
    property_combinations = defaultdict(list)
    
    # For each combination of properties, track which styles use them
    for style_idx, style in enumerate(all_styles):
        properties = style['properties']
        
        # Generate all combinations of properties (2 to n-1)
        for combo_size in range(min_shared_props, len(properties)):
            from itertools import combinations
            for prop_combo in combinations(properties, combo_size):
                combo_key = tuple(sorted(prop_combo))
                property_combinations[combo_key].append({
                    'style_idx': style_idx,
                    'line': style['line'],
                    'all_properties': properties,
                    'combo_properties': list(prop_combo),
                    'remaining_properties': [p for p in properties if p not in prop_combo]
                })
    
    # Filter to combinations that appear in multiple styles
    significant_combinations = {
        combo: styles for combo, styles in property_combinations.items()
        if len(styles) >= min_occurrences
    }
    
    return significant_combinations


def find_semantic_patterns(all_styles: List[dict]):
    """Find styles that follow common semantic patterns."""
    categories = categorize_properties()
    patterns = defaultdict(list)
    
    for style_idx, style in enumerate(all_styles):
        properties = style['properties']
        
        # Categorize each property
        style_categories = defaultdict(list)
        for prop in properties:
            prop_name = prop.split(':')[0].strip()
            for category, props in categories.items():
                if prop_name in props:
                    style_categories[category].append(prop)
                    break
        
        # Look for significant category patterns
        for category, category_props in style_categories.items():
            if len(category_props) >= 2:  # At least 2 properties in this category
                pattern_key = f"{category}_pattern_{len(category_props)}"
                patterns[pattern_key].append({
                    'style_idx': style_idx,
                    'line': style['line'],
                    'category': category,
                    'category_properties': category_props,
                    'all_properties': properties,
                    'other_properties': [p for p in properties if p not in category_props]
                })
    
    return patterns


def find_utility_opportunities(all_styles: List[dict]):
    """Find individual properties that could become utility classes."""
    property_counter = Counter()
    property_usage = defaultdict(list)
    
    for style_idx, style in enumerate(all_styles):
        for prop in style['properties']:
            property_counter[prop] += 1
            property_usage[prop].append({
                'style_idx': style_idx,
                'line': style['line'],
                'all_properties': style['properties']
            })
    
    # Find properties used frequently enough to warrant utility classes
    utility_candidates = {
        prop: usage for prop, usage in property_usage.items()
        if property_counter[prop] >= 3  # Used 3+ times
    }
    
    return utility_candidates


def analyze_enhanced_consolidation(all_styles: List[dict]):
    """Enhanced analysis to find more consolidation opportunities."""
    print(f"\n🔬 Enhanced Consolidation Analysis")
    print(f"=" * 50)
    
    if not all_styles:
        print("No styles found.")
        return
    
    # 1. Exact duplicates (original analysis)
    style_groups = {}
    for style in all_styles:
        normalized = style['normalized']
        if normalized not in style_groups:
            style_groups[normalized] = []
        style_groups[normalized].append(style)
    
    exact_duplicates = {k: v for k, v in style_groups.items() if len(v) > 1}
    
    # 2. Partial matches
    partial_matches = find_partial_matches(all_styles, min_shared_props=2, min_occurrences=3)
    
    # 3. Semantic patterns
    semantic_patterns = find_semantic_patterns(all_styles)
    
    # 4. Utility opportunities
    utility_opportunities = find_utility_opportunities(all_styles)
    
    # Report findings
    print(f"\n📋 EXACT DUPLICATES:")
    if exact_duplicates:
        for i, (normalized, occurrences) in enumerate(exact_duplicates.items(), 1):
            lines = [str(occ.get('line', 'unknown')) for occ in occurrences]
            print(f"  {i}. Used {len(occurrences)} times (lines {', '.join(lines)})")
            print(f"     {normalized}")
    else:
        print("  None found.")
    
    print(f"\n🧩 PARTIAL PROPERTY MATCHES:")
    if partial_matches:
        sorted_partials = sorted(partial_matches.items(), key=lambda x: len(x[1]), reverse=True)
        for i, (combo, styles) in enumerate(sorted_partials[:5], 1):  # Top 5
            lines = [str(s['line']) for s in styles]
            print(f"  {i}. {len(styles)} styles share {len(combo)} properties (lines {', '.join(lines)})")
            print(f"     Shared: {'; '.join(combo)}")
            
            # Show what's different
            remaining_groups = defaultdict(list)
            for style_info in styles:
                remaining_key = tuple(sorted(style_info['remaining_properties']))
                remaining_groups[remaining_key].append(style_info['line'])
            
            if len(remaining_groups) > 1:
                print(f"     Variations:")
                for remaining, lines in remaining_groups.items():
                    if remaining:
                        print(f"       Lines {', '.join(map(str, lines))}: + {'; '.join(remaining)}")
                    else:
                        print(f"       Lines {', '.join(map(str, lines))}: (no additional properties)")
            print()
    else:
        print("  None found with current thresholds.")
    
    print(f"\n🎯 SEMANTIC PATTERNS:")
    if semantic_patterns:
        for pattern_name, styles in semantic_patterns.items():
            if len(styles) >= 3:  # Only show patterns with 3+ occurrences
                lines = [str(s['line']) for s in styles]
                category = styles[0]['category']
                print(f"  {len(styles)} styles with {category} patterns (lines {', '.join(lines)})")
                
                # Show common properties in this category
                category_props = styles[0]['category_properties']
                print(f"     Common {category}: {'; '.join(category_props)}")
    else:
        print("  None found.")
    
    print(f"\n⚡ UTILITY CLASS OPPORTUNITIES:")
    if utility_opportunities:
        sorted_utilities = sorted(utility_opportunities.items(), key=lambda x: len(x[1]), reverse=True)
        for prop, usage in sorted_utilities[:10]:  # Top 10
            lines = [str(u['line']) for u in usage]
            print(f"  {prop} → Used {len(usage)} times (lines {', '.join(lines)})")
    else:
        print("  None found.")
    
    # Generate practical consolidation suggestions
    print(f"\n💡 PRACTICAL CONSOLIDATION SUGGESTIONS:")
    print(f"=" * 50)
    
    suggestion_count = 0
    
    # Suggest base classes for partial matches
    if partial_matches:
        print(f"\n🏗️  BASE + MODIFIER PATTERN:")
        for combo, styles in sorted(partial_matches.items(), key=lambda x: len(x[1]), reverse=True)[:3]:
            if len(styles) >= 3:
                suggestion_count += 1
                class_name = f"base-pattern-{suggestion_count}"
                print(f"\n  .{class_name} {{")
                for prop in combo:
                    print(f"      {prop};")
                print(f"  }}")
                print(f"  /* Base class for {len(styles)} styles */")
                
                # Show how to use it
                remaining_groups = defaultdict(list)
                for style_info in styles:
                    remaining_key = tuple(sorted(style_info['remaining_properties']))
                    remaining_groups[remaining_key].append(style_info['line'])
                
                print(f"  Usage:")
                for i, (remaining, lines) in enumerate(remaining_groups.items(), 1):
                    if remaining:
                        modifier_class = f"{class_name}-variant-{i}"
                        print(f"    Lines {', '.join(map(str, lines))}: cls='{class_name} {modifier_class}'")
                        print(f"    .{modifier_class} {{ {'; '.join(remaining)}; }}")
                    else:
                        print(f"    Lines {', '.join(map(str, lines))}: cls='{class_name}'")
    
    # Suggest utility classes
    if utility_opportunities:
        print(f"\n🔧 UTILITY CLASSES:")
        for prop, usage in sorted(utility_opportunities.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            if len(usage) >= 4:  # Only suggest for frequently used properties
                suggestion_count += 1
                # Create utility class name
                prop_name = prop.split(':')[0].strip()
                prop_value = prop.split(':', 1)[1].strip()
                
                # Simple utility naming
                utility_name = f"u-{prop_name.replace('-', '_')}"
                if 'center' in prop_value.lower():
                    utility_name += "-center"
                elif 'flex' in prop_value.lower():
                    utility_name += "-flex"
                elif prop_value == 'none':
                    utility_name += "-none"
                
                print(f"  .{utility_name} {{ {prop}; }}")
                lines = [str(u['line']) for u in usage]
                print(f"  /* Used {len(usage)} times: lines {', '.join(lines)} */")
    
    if suggestion_count == 0:
        print(f"  Current styles are quite unique - limited consolidation opportunities.")
        print(f"  Consider this a sign of good, specific styling! 🎨")


def analyze_styles_for_consolidation(all_styles: List[dict]):
    """
    Analyze all found styles to identify consolidation opportunities.
    
    Args:
        all_styles: List of style dictionaries from normalization
    """
    print(f"\n📊 Basic Style Analysis Report")
    print(f"=" * 50)
    
    if not all_styles:
        print("No styles found.")
        return
    
    print(f"Total styles found: {len(all_styles)}")
    
    # Group by normalized content to find duplicates
    style_groups = {}
    for style in all_styles:
        normalized = style['normalized']
        if normalized not in style_groups:
            style_groups[normalized] = []
        style_groups[normalized].append(style)
    
    # Report duplicates
    duplicates = {k: v for k, v in style_groups.items() if len(v) > 1}
    if duplicates:
        print(f"\n🔄 Found {len(duplicates)} exact duplicate patterns:")
        for i, (normalized, occurrences) in enumerate(duplicates.items(), 1):
            print(f"\n  {i}. Used {len(occurrences)} times:")
            print(f"     {normalized}")
            lines = [str(occ.get('line', 'unknown')) for occ in occurrences]
            print(f"     Lines: {', '.join(lines)}")
    
    # Report most common properties
    property_counts = {}
    for style in all_styles:
        for prop in style['properties']:
            prop_name = prop.split(':')[0].strip()
            property_counts[prop_name] = property_counts.get(prop_name, 0) + 1
    
    print(f"\n📈 Most common CSS properties:")
    sorted_props = sorted(property_counts.items(), key=lambda x: x[1], reverse=True)
    for prop, count in sorted_props[:10]:
        print(f"  {prop}: {count} occurrences")
    
    # Enhanced analysis
    analyze_enhanced_consolidation(all_styles)


def main():
    """Main function to normalize styles in server.py"""
    print("🎨 Enhanced Inline CSS Style Analyzer")
    print("=" * 40)
    
    # Find project root
    project_root = find_project_root()
    server_file = project_root / "server.py"
    
    if not server_file.exists():
        print(f"❌ Could not find server.py in {project_root}")
        print("   Make sure you're running this from the Pipulate project directory.")
        return 1
    
    # Normalize styles
    changes_made, all_styles = normalize_styles_in_file(server_file)
    
    # Analyze for consolidation opportunities
    analyze_styles_for_consolidation(all_styles)
    
    print(f"\n✨ Analysis complete!")
    print(f"   Changes made: {changes_made}")
    print(f"   Styles found: {len(all_styles)}")
    
    if changes_made > 0:
        print(f"\n💡 Next steps:")
        print(f"   1. Review the changes with: git diff")
        print(f"   2. Look for consolidation patterns above")
        print(f"   3. Extract common patterns to CSS classes")
        print(f"   4. Replace inline styles with class references")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 