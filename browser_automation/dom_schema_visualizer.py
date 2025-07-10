#!/usr/bin/env python3
"""
🎭 DOM SCHEMA VISUALIZER

Beautiful Rich-based DOM visualization with hierarchical banners that make
DOM structure instantly obvious to humans and perfect for automation planning.

Inspired by the startup sequence banner aesthetic - uses Rich panels with
progressive indentation and color coding to create a stunning visual hierarchy.

Features:
- 🎨 Hierarchical banner styling with progressive indentation
- 🎯 Automation-ready element identification (IDs, ARIA, data-testid)
- 📊 Rich table summaries of key elements by category
- 🔍 Interactive element discovery with visual debugging support
- 🤖 AI-optimized output for automation context planning
"""

import sys
import os
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.columns import Columns
from rich.padding import Padding
from rich.box import ROUNDED, DOUBLE, HEAVY, ASCII
from rich.layout import Layout
from rich.align import Align

# Add parent directory to path for pipulate imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class ElementInfo:
    """Rich element information for automation targeting"""
    tag: str
    level: int
    id: Optional[str] = None
    classes: List[str] = None
    aria_label: Optional[str] = None
    aria_role: Optional[str] = None
    data_testid: Optional[str] = None
    text_content: Optional[str] = None
    href: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    automation_priority: int = 0
    children_count: int = 0

class DOMSchemaVisualizer:
    def __init__(self):
        self.console = Console(width=140)  # Wider for beautiful layouts
        
        # 🎨 Hierarchical color scheme (matches startup banner aesthetic)
        self.level_colors = [
            "bright_red",      # Level 0 (html) - Root level
            "bright_green",    # Level 1 (head, body) - Major sections  
            "bright_yellow",   # Level 2 (nav, main, header) - Layout containers
            "bright_blue",     # Level 3 (divs, sections) - Content blocks
            "bright_magenta",  # Level 4 (forms, lists) - Interactive elements
            "bright_cyan",     # Level 5 (inputs, links) - Leaf elements
            "red",             # Level 6+ (deep nesting)
            "green",
            "yellow", 
            "blue",
            "magenta",
            "cyan",
            "white"
        ]
        
        # 📏 Progressive indentation for hierarchy
        self.base_width = 130
        self.indent_reduction = 8  # Pixels reduced per level
        self.min_width = 40
        
        self.automation_elements = []
        self.element_stats = {}
        
    def get_color_for_level(self, level: int) -> str:
        """Get Rich color for DOM nesting level"""
        if level < len(self.level_colors):
            return self.level_colors[level]
        return self.level_colors[level % len(self.level_colors)]
    
    def get_panel_width(self, level: int) -> int:
        """Calculate panel width with progressive indentation"""
        calculated_width = self.base_width - (level * self.indent_reduction)
        return max(calculated_width, self.min_width)
    
    def extract_element_info(self, element: Tag, level: int) -> ElementInfo:
        """Extract comprehensive element information"""
        # Get classes as list
        classes = element.get('class', [])
        if isinstance(classes, str):
            classes = [classes]
            
        # Extract text content (first 60 chars, clean)
        text_content = None
        if element.string:
            text = element.string.strip()
            if text and len(text) > 0:
                text_content = text[:60] + "..." if len(text) > 60 else text
        
        # Count direct children
        children_count = len([child for child in element.children if hasattr(child, 'name')])
        
        # Calculate automation priority
        priority = self.calculate_automation_priority(element)
        
        return ElementInfo(
            tag=element.name,
            level=level,
            id=element.get('id'),
            classes=classes,
            aria_label=element.get('aria-label'),
            aria_role=element.get('role'),
            data_testid=element.get('data-testid'),
            text_content=text_content,
            href=element.get('href'),
            type=element.get('type'),
            name=element.get('name'),
            automation_priority=priority,
            children_count=children_count
        )
    
    def calculate_automation_priority(self, element: Tag) -> int:
        """Calculate element priority for automation (higher = more important)"""
        priority = 0
        
        # High priority: Interactive elements
        if element.name in ['button', 'input', 'select', 'textarea']:
            priority += 10
        if element.name in ['a', 'form']:
            priority += 8
            
        # Medium priority: Structural containers with semantic meaning
        if element.name in ['nav', 'main', 'header', 'footer', 'section', 'article']:
            priority += 5
            
        # Attribute-based priority
        if element.get('id'):
            priority += 7
        if element.get('data-testid'):
            priority += 9  # Highest for test targeting
        if element.get('aria-label'):
            priority += 6
        if element.get('role'):
            priority += 4
            
        return priority
    
    def format_element_header(self, info: ElementInfo) -> Text:
        """Format beautiful element header with automation indicators"""
        color = self.get_color_for_level(info.level)
        
        # Build header parts
        header_parts = [f"<{info.tag}>"]
        
        # Add automation indicators with emoji
        if info.id:
            header_parts.append(f"🆔 #{info.id}")
        if info.data_testid:
            header_parts.append(f"🧪 data-testid='{info.data_testid}'")
        if info.aria_label:
            header_parts.append(f"♿ aria-label='{info.aria_label[:30]}...'")
        if info.aria_role:
            header_parts.append(f"🎭 role='{info.aria_role}'")
        if info.classes:
            class_str = ' '.join(info.classes[:3])  # Show first 3 classes
            if len(info.classes) > 3:
                class_str += f" +{len(info.classes)-3}"
            header_parts.append(f"📝 .{class_str}")
            
        # Add interaction indicators
        if info.href:
            header_parts.append(f"🔗 href='{info.href[:25]}...'")
        if info.type:
            header_parts.append(f"⚙️ type='{info.type}'")
        if info.name:
            header_parts.append(f"📛 name='{info.name}'")
            
        # Add priority indicator
        if info.automation_priority >= 10:
            header_parts.append("🎯 HIGH-PRIORITY")
        elif info.automation_priority >= 5:
            header_parts.append("🔍 AUTOMATION-TARGET")
            
        return Text(" ".join(header_parts), style=color)
    
    def format_element_content(self, info: ElementInfo) -> List[Text]:
        """Format element content with metadata"""
        content_lines = []
        
        # Add text content if available
        if info.text_content:
            content_lines.append(Text(f'💬 Text: "{info.text_content}"', style="dim white"))
            
        # Add structural info
        if info.children_count > 0:
            content_lines.append(Text(f"📦 Contains: {info.children_count} child elements", style="dim cyan"))
            
        return content_lines
    
    def build_hierarchical_panels(self, element: Tag, level: int = 0, max_depth: int = 8) -> Panel:
        """Build beautiful hierarchical panels (core visualization method)"""
        if level > max_depth:
            return None
            
        info = self.extract_element_info(element, level)
        
        # Track for automation registry
        if info.automation_priority >= 5:
            self.automation_elements.append(info)
            
        # Update element statistics
        tag = info.tag
        self.element_stats[tag] = self.element_stats.get(tag, 0) + 1
        
        # Format header and content
        header = self.format_element_header(info)
        content_lines = self.format_element_content(info)
        
        # Process children recursively
        child_panels = []
        for child in element.children:
            if hasattr(child, 'name') and child.name:  # Skip text nodes
                child_panel = self.build_hierarchical_panels(child, level + 1, max_depth)
                if child_panel:
                    child_panels.append(child_panel)
        
        # Combine content
        all_content = content_lines[:]
        if content_lines and child_panels:
            all_content.append(Text(""))  # Spacer
        all_content.extend(child_panels)
        
        # Create panel with progressive styling
        if not all_content:
            all_content = [Text("(empty element)", style="dim")]
            
        color = self.get_color_for_level(level)
        width = self.get_panel_width(level)
        
        # Choose box style based on level
        box_styles = [DOUBLE, HEAVY, ROUNDED, ASCII]
        box_style = box_styles[min(level, len(box_styles) - 1)]
        
        from rich.console import Group
        return Panel(
            Group(*all_content) if len(all_content) > 1 else all_content[0],
            title=str(header),
            border_style=color,
            box=box_style,
            padding=(0, 1),
            width=width
        )
    
    def create_automation_registry_table(self) -> Table:
        """Create beautiful table of automation targets"""
        table = Table(
            title="🎯 Automation Target Registry",
            caption="Elements prioritized for automation workflows",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
            box=ROUNDED
        )
        
        table.add_column("Priority", style="bold red", width=8)
        table.add_column("Element", style="bright_yellow", width=12)
        table.add_column("ID", style="bright_green", width=20)
        table.add_column("Test ID", style="bright_cyan", width=25)
        table.add_column("ARIA Label", style="bright_white", width=30)
        table.add_column("Role", style="magenta", width=15)
        
        # Sort by priority (highest first)
        sorted_elements = sorted(self.automation_elements, 
                               key=lambda x: x.automation_priority, reverse=True)
        
        for elem in sorted_elements[:15]:  # Top 15 automation targets
            table.add_row(
                str(elem.automation_priority),
                f"<{elem.tag}>",
                elem.id or "—",
                elem.data_testid or "—",
                (elem.aria_label[:28] + "...") if elem.aria_label and len(elem.aria_label) > 28 else (elem.aria_label or "—"),
                elem.aria_role or "—"
            )
            
        return table
    
    def create_element_stats_table(self) -> Table:
        """Create beautiful statistics table"""
        table = Table(
            title="📊 DOM Element Statistics",
            show_header=True,
            header_style="bold cyan",
            border_style="bright_green",
            box=HEAVY
        )
        
        table.add_column("Element Type", style="bright_yellow", width=15)
        table.add_column("Count", style="bright_white", width=8, justify="right")
        table.add_column("Usage", style="green", width=30)
        
        # Sort by count (most common first)
        sorted_stats = sorted(self.element_stats.items(), 
                            key=lambda x: x[1], reverse=True)
        
        total_elements = sum(self.element_stats.values())
        
        for tag, count in sorted_stats[:12]:  # Top 12 most common elements
            percentage = (count / total_elements) * 100
            usage_bar = "█" * int(percentage / 3)  # Visual bar
            table.add_row(
                f"<{tag}>",
                str(count),
                f"{usage_bar} {percentage:.1f}%"
            )
            
        return table
    
    def create_banner_header(self, source_name: str, total_elements: int) -> Panel:
        """Create stunning banner header"""
        header_content = Text.assemble(
            ("🎭 ", "bright_magenta"),
            ("DOM SCHEMA VISUALIZATION", "bold bright_white"),
            (" 🎭\n\n", "bright_magenta"),
            ("📄 Source: ", "bright_cyan"), (source_name, "bright_yellow"), ("\n"),
            ("📊 Elements: ", "bright_cyan"), (f"{total_elements:,}", "bright_green"), ("\n"),
            ("🎯 Purpose: ", "bright_cyan"), ("Human-readable DOM structure for automation planning", "bright_white")
        )
        
        return Panel(
            Align.center(header_content),
            border_style="bright_magenta",
            box=DOUBLE,
            padding=(1, 2),
            width=self.base_width
        )
    
    def visualize_dom_file(self, file_path: Path) -> None:
        """Main visualization method for DOM files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            self.visualize_dom_content(html_content, file_path.name)
            
        except Exception as e:
            self.console.print(f"❌ Error reading file: {e}", style="red")
    
    def visualize_dom_content(self, html_content: str, source_name: str = "DOM") -> None:
        """Main visualization method for DOM content"""
        try:
            # Reset state
            self.automation_elements = []
            self.element_stats = {}
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get total element count
            all_elements = soup.find_all()
            total_elements = len(all_elements)
            
            # Create banner header
            header_banner = self.create_banner_header(source_name, total_elements)
            self.console.print(header_banner)
            self.console.print()
            
            # Find root element - handle nested HTML gracefully
            html_elements = soup.find_all('html')
            if len(html_elements) > 1:
                # Use the outermost HTML element for structure
                root_element = html_elements[0]
                # But if there's nested content, use the body of the outer element
                outer_body = root_element.find('body')
                if outer_body:
                    # Get the actual content from nested structure
                    nested_content = outer_body.find('html')
                    if nested_content:
                        root_element = nested_content
            else:
                root_element = soup.find('html') or soup
                
            if root_element and hasattr(root_element, 'name'):
                
                # Adjust depth based on complexity (allow deeper for better structure visibility)
                max_depth = 10 if total_elements > 100 else 15
                
                if total_elements > 100:
                    self.console.print(
                        Panel(
                            f"🔍 Complex DOM detected ({total_elements:,} elements) - showing simplified view (max {max_depth} levels)",
                            style="yellow",
                            border_style="bright_yellow"
                        )
                    )
                    self.console.print()
                
                # Build and display hierarchical structure
                dom_structure = self.build_hierarchical_panels(root_element, 0, max_depth)
                if dom_structure:
                    self.console.print(dom_structure)
                    self.console.print()
                    
                # Create summary tables side by side
                automation_table = self.create_automation_registry_table()
                stats_table = self.create_element_stats_table()
                
                # Display tables in columns for better layout
                summary_layout = Columns([automation_table, stats_table], equal=True, expand=True)
                self.console.print(summary_layout)
                
                # Final summary banner
                summary_banner = Panel(
                    Text.assemble(
                        ("🎯 ", "bright_green"),
                        ("AUTOMATION READY", "bold bright_white"),
                        (" | ", "dim white"),
                        (f"{len(self.automation_elements)} high-priority targets identified", "bright_green"),
                        (" | ", "dim white"), 
                        (f"DOM structure visualized across {max_depth} levels", "bright_cyan")
                    ),
                    border_style="bright_green",
                    box=ROUNDED
                )
                self.console.print(summary_banner)
                
        except Exception as e:
            self.console.print(f"❌ Error parsing HTML: {e}", style="red")

def main():
    """CLI entry point"""
    visualizer = DOMSchemaVisualizer()
    
    # Default to looking_at directory
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
        visualizer.console.print()
        visualizer.visualize_dom_file(simple_dom_file)
    else:
        print("❌ No DOM file found.")
        print("Usage: python dom_schema_visualizer.py [path_to_html_file]")
        print("Default: Uses browser_automation/looking_at/simple_dom.html")
        sys.exit(1)

if __name__ == "__main__":
    main() 