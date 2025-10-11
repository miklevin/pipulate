#!/usr/bin/env python3
"""
DOM Box Visualizer

Renders DOM hierarchy as actual nested boxes/rectangles showing containment relationships.
Each element is a box, child elements are drawn inside parent boxes.
"""

import sys
import os
from pathlib import Path
from bs4 import BeautifulSoup
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.align import Align
from rich.padding import Padding
from rich.box import ROUNDED, DOUBLE, HEAVY, ASCII
import re

# Add the parent directory to the path so we can import from pipulate
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class DOMBoxVisualizer:
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
        
        # Box styles for different levels
        self.box_styles = [DOUBLE, HEAVY, ROUNDED, ASCII]
        
        # Use 90% of console width, with fallback for when width detection fails
        try:
            console_width = self.console.size.width
            self.max_content_width = int(console_width * 0.9)
        except:
            self.max_content_width = 120  # Fallback to larger default
        
        self.max_children_to_show = 8  # Limit children to keep readable
        
    def get_color_for_level(self, level):
        """Get color for a specific nesting level"""
        if level < len(self.level_colors):
            return self.level_colors[level]
        # Cycle through colors for very deep nesting
        return self.level_colors[level % len(self.level_colors)]
    
    def get_box_style_for_level(self, level):
        """Get box style for a specific nesting level"""
        if level < len(self.box_styles):
            return self.box_styles[level]
        return ASCII
    
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
        
        # Get text content (first 60 chars, including text from immediate children)
        if element.string:
            text = element.string.strip()
            if text:
                info['text'] = text[:60] + "..." if len(text) > 60 else text
        else:
            # Try to get text from direct text content
            texts = []
            for child in element.children:
                if isinstance(child, str):
                    child_text = child.strip()
                    if child_text:
                        texts.append(child_text)
                elif hasattr(child, 'string') and child.string:
                    child_text = child.string.strip()
                    if child_text:
                        texts.append(child_text)
            
            if texts:
                combined_text = ' '.join(texts)
                info['text'] = combined_text[:60] + "..." if len(combined_text) > 60 else combined_text
        
        return info
    
    def format_element_title(self, info, level):
        """Format element information for display as box title"""
        color = self.get_color_for_level(level)
        
        # Build title components
        title_parts = [f"<{info['tag']}>"]
        
        # Add key attributes
        if info['id']:
            title_parts.append(f"#{info['id']}")
        if info['data_testid']:
            title_parts.append(f"[testid={info['data_testid']}]")
        if info['aria_label']:
            title_parts.append(f"[aria={info['aria_label'][:15]}...]")
        
        title = " ".join(title_parts)
        return Text(title, style=f"bold {color}")
    
    def format_element_content(self, info, children_count, level):
        """Format element content for display inside box"""
        color = self.get_color_for_level(level)
        content_lines = []
        
        # Add classes if present
        if info['class']:
            classes = ' '.join(info['class']) if isinstance(info['class'], list) else info['class']
            if len(classes) > 50:
                classes = classes[:47] + "..."
            content_lines.append(Text(f"class: {classes}", style=f"dim {color}"))
        
        # Add href if present
        if info['href']:
            href = info['href'][:45] + "..." if len(info['href']) > 45 else info['href']
            content_lines.append(Text(f"href: {href}", style=f"dim {color}"))
        
        # Add src if present
        if info['src']:
            src = info['src'][:45] + "..." if len(info['src']) > 45 else info['src']
            content_lines.append(Text(f"src: {src}", style=f"dim {color}"))
        
        # Add text content if available
        if info['text']:
            content_lines.append(Text(f'"{info["text"]}"', style=f"italic {color}"))
        
        # Add child count info
        if children_count > 0:
            child_info = f"[{children_count} child element{'s' if children_count != 1 else ''}]"
            if children_count > self.max_children_to_show:
                child_info += f" (showing first {self.max_children_to_show})"
            content_lines.append(Text(child_info, style=f"dim {color}"))
        
        return content_lines
    
    def build_nested_boxes(self, element, level=0, max_depth=6):
        """Recursively build nested box structure"""
        if level > max_depth:
            return Text("... (max depth reached)", style="dim white")
        
        info = self.extract_element_info(element)
        
        # Get child elements (not text nodes)
        child_elements = [child for child in element.children 
                         if hasattr(child, 'name') and child.name]
        
        # Limit children for readability
        children_to_show = child_elements[:self.max_children_to_show]
        
        # Format title and content
        title = self.format_element_title(info, level)
        content_lines = self.format_element_content(info, len(child_elements), level)
        
        # Build content
        if children_to_show and level < max_depth:
            # Create nested boxes for children
            child_boxes = []
            for child in children_to_show:
                child_box = self.build_nested_boxes(child, level + 1, max_depth)
                if child_box:
                    child_boxes.append(child_box)
            
            # Combine content lines with child boxes
            all_content = []
            for line in content_lines:
                all_content.append(line)
            
            if content_lines and child_boxes:
                all_content.append(Text(""))  # Empty line separator
            
            for child_box in child_boxes:
                all_content.append(child_box)
                if child_box != child_boxes[-1]:  # Not the last child
                    all_content.append(Text(""))  # Space between children
        else:
            all_content = content_lines
        
        # If no content, show minimal info
        if not all_content:
            all_content = [Text("(empty element)", style="dim")]
        
        # Create the panel with appropriate styling
        color = self.get_color_for_level(level)
        box_style = self.get_box_style_for_level(level)
        
        # Build the renderable content
        if len(all_content) == 1 and isinstance(all_content[0], (Text, Panel)):
            panel_content = all_content[0]
        else:
            # Create a proper Group of renderables for Rich
            from rich.console import Group
            panel_content = Group(*all_content)
        
        # Calculate width: start with full width, shrink gradually but keep generous minimum
        # Use percentage-based shrinking for better proportions
        width_reduction = int(self.max_content_width * 0.08 * level)  # 8% reduction per level
        min_width = max(int(self.max_content_width * 0.25), 40)  # 25% of max width minimum
        calculated_width = max(self.max_content_width - width_reduction, min_width)
        
        return Panel(
            panel_content,
            title=title,
            border_style=color,
            box=box_style,
            padding=(0, 1),
            width=calculated_width
        )
    
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
            
            # Create title with width info
            width_info = f"📦 DOM Box Layout: {source_name} (Console width: {self.console.size.width}, Using: {self.max_content_width})"
            title = Panel(
                width_info,
                style="bold blue",
                padding=(1, 2)
            )
            self.console.print(title)
            
            # Find the root element (usually html)
            root_element = soup.find('html') or soup
            if root_element and hasattr(root_element, 'name'):
                
                # Show a simplified version first for complex DOMs
                all_elements = soup.find_all()
                if len(all_elements) > 100:
                    self.console.print("🔍 Complex DOM detected - showing simplified view (first 6 levels)\n", style="yellow")
                    max_depth = 6
                else:
                    max_depth = 12  # Increased depth for simpler pages
                
                # Build and display the nested box structure
                nested_layout = self.build_nested_boxes(root_element, 0, max_depth)
                self.console.print(nested_layout)
                
                # Add statistics
                stats = self._get_dom_stats(soup)
                self.console.print(f"\n📊 Layout Statistics:", style="bold cyan")
                self.console.print(f"  • Total elements: {stats['total_elements']}")
                self.console.print(f"  • Maximum depth: {stats['max_depth']}")
                self.console.print(f"  • Most common containers: {', '.join(stats['common_tags'][:5])}")
                
                if len(all_elements) > 100:
                    self.console.print(f"  • Simplified view: Showing up to {max_depth} levels deep", style="dim")
            
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
        self.console.print("\n🎨 Box Color Legend:", style="bold white")
        
        legend_width = max(int(self.max_content_width * 0.2), 30)  # 20% of max width for legend
        
        for i, color in enumerate(self.level_colors[:8]):  # Show first 8 levels
            box_style = self.get_box_style_for_level(i)
            sample_panel = Panel(
                f"Level {i} content - {box_style.name if hasattr(box_style, 'name') else 'Custom'} style",
                title=f"Level {i}",
                border_style=color,
                box=box_style,
                width=legend_width
            )
            self.console.print(sample_panel)

def main():
    """Main function to run the visualizer"""
    visualizer = DOMBoxVisualizer()
    
    # Default to the current looking_at directory
    looking_at_dir = Path("browser_cache/looking_at")
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
        visualizer.console.print("🔍 Using latest scraped DOM from browser_cache/looking_at/", style="dim")
        visualizer.visualize_dom_file(simple_dom_file)
    else:
        print("❌ No DOM file found. Please provide a file path or ensure browser_cache/looking_at/simple_dom.html exists.")
        print("Usage: python dom_box_visualizer.py [path_to_html_file]")
        sys.exit(1)
    
    # Show color legend
    visualizer.show_color_legend()

if __name__ == "__main__":
    main() 