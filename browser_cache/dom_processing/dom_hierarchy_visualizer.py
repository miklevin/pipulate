#!/usr/bin/env python3
"""
DOM Hierarchy Visualizer

Takes the simplified DOM and renders it as a beautiful color-coded hierarchical structure.
Uses Rich console for terminal output with colors representing nesting depth.
"""

import sys
import os
from pathlib import Path
from bs4 import BeautifulSoup
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from rich.columns import Columns
from rich.padding import Padding
import re

# Add the parent directory to the path so we can import from pipulate
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class DOMHierarchyVisualizer:
    def __init__(self):
        self.console = Console()
        # Color scheme for different nesting levels
        self.level_colors = [
            "bright_red",      # Level 0 (html)
            "bright_green",    # Level 1 (body, head)
            "bright_yellow",   # Level 2 (main sections)
            "bright_blue",     # Level 3 (subsections)
            "bright_magenta",  # Level 4 (components)
            "bright_cyan",     # Level 5 (elements)
            "red",             # Level 6+ (deep nesting)
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "white"
        ]
        
    def get_color_for_level(self, level):
        """Get color for a specific nesting level"""
        if level < len(self.level_colors):
            return self.level_colors[level]
        # Cycle through colors for very deep nesting
        return self.level_colors[level % len(self.level_colors)]
    
    def extract_element_info(self, element):
        """Extract meaningful information from an element"""
        info = {
            'tag': element.name,
            'id': element.get('id'),
            'class': element.get('class'),
            'aria_label': element.get('aria-label'),
            'data_testid': element.get('data-testid'),
            'href': element.get('href'),
            'src': element.get('src'),
            'text': None
        }
        
        # Get text content (first 50 chars, no nested elements)
        if element.string:
            text = element.string.strip()
            if text:
                info['text'] = text[:50] + "..." if len(text) > 50 else text
        
        return info
    
    def format_element_display(self, info, level):
        """Format element information for display"""
        color = self.get_color_for_level(level)
        
        # Start with tag name
        display_parts = [f"<{info['tag']}>"]
        
        # Add meaningful attributes
        if info['id']:
            display_parts.append(f"id='{info['id']}'")
        if info['class']:
            classes = ' '.join(info['class']) if isinstance(info['class'], list) else info['class']
            display_parts.append(f"class='{classes}'")
        if info['data_testid']:
            display_parts.append(f"data-testid='{info['data_testid']}'")
        if info['aria_label']:
            display_parts.append(f"aria-label='{info['aria_label']}'")
        if info['href']:
            display_parts.append(f"href='{info['href'][:30]}...'")
        if info['src']:
            display_parts.append(f"src='{info['src'][:30]}...'")
        
        # Add text content if available
        if info['text']:
            display_parts.append(f'"{info['text']}"')
        
        return Text(" ".join(display_parts), style=color)
    
    def build_tree_structure(self, element, tree_node, level=0):
        """Recursively build the tree structure"""
        info = self.extract_element_info(element)
        display_text = self.format_element_display(info, level)
        
        # Add this element to the tree
        current_node = tree_node.add(display_text)
        
        # Process children
        child_level = level + 1
        for child in element.children:
            if hasattr(child, 'name') and child.name:  # Skip text nodes
                self.build_tree_structure(child, current_node, child_level)
    
    def visualize_dom_file(self, file_path):
        """Visualize DOM from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            self.visualize_dom_content(html_content, file_path)
            
        except Exception as e:
            self.console.print(f"❌ Error reading file: {e}", style="red")
    
    def visualize_dom_content(self, html_content, source_name="DOM"):
        """Visualize DOM from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Create title panel
            title = Panel(
                f"🌳 DOM Hierarchy Visualization: {source_name}",
                style="bold blue",
                padding=(1, 2)
            )
            self.console.print(title)
            
            # Create the tree
            tree = Tree(
                Text("🌐 Document Root", style="bold white"),
                style="dim"
            )
            
            # Find the root element (usually html)
            root_element = soup.find('html') or soup
            if root_element and hasattr(root_element, 'name'):
                self.build_tree_structure(root_element, tree, 0)
            
            # Display the tree
            self.console.print(tree)
            
            # Add statistics
            stats = self._get_dom_stats(soup)
            self.console.print(f"\n📊 Structure Statistics:", style="bold cyan")
            self.console.print(f"  • Total elements: {stats['total_elements']}")
            self.console.print(f"  • Maximum depth: {stats['max_depth']}")
            self.console.print(f"  • Most common tags: {', '.join(stats['common_tags'][:5])}")
            
        except Exception as e:
            self.console.print(f"❌ Error parsing HTML: {e}", style="red")
    
    def _get_dom_stats(self, soup):
        """Get statistics about the DOM structure"""
        all_elements = soup.find_all()
        total_elements = len(all_elements)
        
        # Count tag frequency
        tag_counts = {}
        for element in all_elements:
            tag = element.name
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Get most common tags
        common_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        common_tags = [tag for tag, count in common_tags]
        
        # Calculate maximum depth
        max_depth = 0
        for element in all_elements:
            depth = len(list(element.parents))
            max_depth = max(max_depth, depth)
        
        return {
            'total_elements': total_elements,
            'max_depth': max_depth,
            'common_tags': common_tags,
            'tag_counts': tag_counts
        }
    
    def show_color_legend(self):
        """Show the color legend for nesting levels"""
        self.console.print("\n🎨 Color Legend (Nesting Levels):", style="bold white")
        
        for i, color in enumerate(self.level_colors[:8]):  # Show first 8 levels
            sample_text = f"Level {i}: <example-tag>"
            colored_text = Text(sample_text, style=color)
            self.console.print(f"  {colored_text}")
        
        self.console.print("  (Colors cycle for deeper nesting levels)")

def main():
    """Main function to run the visualizer"""
    visualizer = DOMHierarchyVisualizer()
    
    # Default to the current looking_at directory
    looking_at_dir = Path("browser_automation/looking_at")
    simple_dom_file = looking_at_dir / "simple_dom.html"
    
    if len(sys.argv) > 1:
        # Use provided file path
        file_path = Path(sys.argv[1])
        if file_path.exists():
            visualizer.visualize_dom_file(file_path)
        else:
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
    elif simple_dom_file.exists():
        # Use the latest scraped DOM
        visualizer.console.print("🔍 Using latest scraped DOM from browser_automation/looking_at/", style="dim")
        visualizer.visualize_dom_file(simple_dom_file)
    else:
        print("❌ No DOM file found. Please provide a file path or ensure browser_automation/looking_at/simple_dom.html exists.")
        print("Usage: python dom_hierarchy_visualizer.py [path_to_html_file]")
        sys.exit(1)
    
    # Show color legend
    visualizer.show_color_legend()

if __name__ == "__main__":
    main() 