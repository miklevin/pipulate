#!/usr/bin/env python3
"""
🤖 AI DOM BEAUTIFIER & AUTOMATION REGISTRY

The ultimate DOM processing tool designed specifically for AI automation needs.
Creates beautiful, hierarchical DOM representations with comprehensive automation
target registries for every possible selector type.

Features:
- Hierarchical indentation for visual DOM structure
- Comprehensive automation registry (CSS, XPath, ARIA, data-testid)
- AI-optimized output for context window efficiency
- Multiple selector strategies for robust automation
- Element scoring for automation priority
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup, Tag, NavigableString


@dataclass
class AutomationTarget:
    """Complete automation information for a DOM element"""
    tag: str
    text: str
    css_selector: str
    xpath_absolute: str
    xpath_simplified: str
    jquery_selector: str
    beautiful_soup_selector: str
    regex_patterns: List[str]
    aria_attributes: Dict[str, str]
    automation_attributes: Dict[str, str]
    priority_score: int
    element_id: str
    automation_strategies: List[str]


class AIDOMBeautifier:
    """AI-optimized DOM beautifier with automation registry"""
    
    def __init__(self):
        self.automation_registry: List[AutomationTarget] = []
        self.element_counter = 0
        
    def beautify_dom(self, html_content: str, max_text_length: int = 50) -> Tuple[str, List[AutomationTarget]]:
        """
        Create beautiful, hierarchical DOM with comprehensive automation registry
        
        Returns:
            Tuple of (beautified_html, automation_registry)
        """
        self.automation_registry = []
        self.element_counter = 0
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unwanted elements that clutter automation
        for tag in soup(['script', 'style', 'noscript', 'meta', 'link', 'head']):
            tag.decompose()
            
        # Build beautified DOM with automation registry
        beautified_lines = []
        self._process_element(soup, beautified_lines, indent_level=0, max_text_length=max_text_length)
        
        return '\n'.join(beautified_lines), self.automation_registry
    
    def _process_element(self, element, lines: List[str], indent_level: int, max_text_length: int):
        """Process a single element and its children recursively"""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                lines.append(f"{'  ' * indent_level}📝 \"{self._truncate_text(text, max_text_length)}\"")
            return
            
        if not isinstance(element, Tag):
            return
            
        # Generate automation target for this element
        automation_target = self._create_automation_target(element, indent_level)
        
        # Only register elements with automation value
        if automation_target.priority_score > 0:
            self.automation_registry.append(automation_target)
        
        # Create beautiful hierarchical representation
        indent = "  " * indent_level
        tag_repr = self._create_tag_representation(element, automation_target, max_text_length)
        lines.append(f"{indent}{tag_repr}")
        
        # Process children with increased indentation
        for child in element.children:
            self._process_element(child, lines, indent_level + 1, max_text_length)
    
    def _create_automation_target(self, element: Tag, indent_level: int) -> AutomationTarget:
        """Create comprehensive automation target for element"""
        self.element_counter += 1
        element_id = f"ai_element_{self.element_counter}"
        
        # Extract text content
        text_content = element.get_text(strip=True)
        
        # Build CSS selector path
        css_selector = self._build_css_selector(element)
        
        # Build XPath selectors
        xpath_absolute = self._build_xpath_absolute(element)
        xpath_simplified = self._build_xpath_simplified(element)
        
        # Build jQuery selector (similar to CSS but with jQuery syntax)
        jquery_selector = self._build_jquery_selector(element)
        
        # Build Beautiful Soup selector
        bs_selector = self._build_beautiful_soup_selector(element)
        
        # Extract ARIA attributes
        aria_attrs = {k: v for k, v in element.attrs.items() if k.startswith('aria-')}
        
        # Extract automation-friendly attributes
        automation_attrs = {}
        for attr in ['id', 'data-testid', 'name', 'type', 'role', 'class']:
            if element.get(attr):
                automation_attrs[attr] = element.get(attr)
        
        # Generate regex patterns for text-based targeting
        regex_patterns = self._generate_regex_patterns(element, text_content)
        
        # Calculate priority score for automation
        priority_score = self._calculate_priority_score(element, automation_attrs, aria_attrs)
        
        # Determine available automation strategies
        strategies = self._determine_automation_strategies(element, automation_attrs, aria_attrs)
        
        return AutomationTarget(
            tag=element.name,
            text=self._truncate_text(text_content, 100),
            css_selector=css_selector,
            xpath_absolute=xpath_absolute,
            xpath_simplified=xpath_simplified,
            jquery_selector=jquery_selector,
            beautiful_soup_selector=bs_selector,
            regex_patterns=regex_patterns,
            aria_attributes=aria_attrs,
            automation_attributes=automation_attrs,
            priority_score=priority_score,
            element_id=element_id,
            automation_strategies=strategies
        )
    
    def _create_tag_representation(self, element: Tag, target: AutomationTarget, max_text_length: int) -> str:
        """Create beautiful visual representation of tag"""
        tag_name = element.name.upper()
        
        # Choose emoji based on tag type
        emoji = self._get_tag_emoji(element.name)
        
        # Build attribute summary
        attr_parts = []
        
        # Priority: data-testid > id > aria-label > class
        if element.get('data-testid'):
            attr_parts.append(f"testid='{element.get('data-testid')}'")
        elif element.get('id'):
            attr_parts.append(f"id='{element.get('id')}'")
        elif element.get('aria-label'):
            attr_parts.append(f"aria-label='{element.get('aria-label')}'")
        elif element.get('class'):
            classes = ' '.join(element.get('class', []))
            attr_parts.append(f"class='{self._truncate_text(classes, 30)}'")
        
        # Add other important attributes
        for attr in ['type', 'name', 'role', 'href']:
            if element.get(attr) and attr not in str(attr_parts):
                attr_parts.append(f"{attr}='{element.get(attr)}'")
        
        attr_str = f" [{', '.join(attr_parts)}]" if attr_parts else ""
        
        # Add text content if meaningful
        text_content = element.get_text(strip=True)
        text_str = ""
        if text_content and len(text_content.strip()) > 0:
            truncated = self._truncate_text(text_content, max_text_length)
            text_str = f" 📝 \"{truncated}\""
        
        # Add priority indicator
        priority_indicator = self._get_priority_indicator(target.priority_score)
        
        return f"{emoji} {tag_name}{attr_str}{text_str} {priority_indicator}"
    
    def _get_tag_emoji(self, tag_name: str) -> str:
        """Get appropriate emoji for tag type"""
        emoji_map = {
            'button': '🔘', 'input': '📝', 'form': '📋', 'a': '🔗',
            'img': '🖼️', 'div': '📦', 'span': '📄', 'p': '📄',
            'h1': '📰', 'h2': '📰', 'h3': '📰', 'h4': '📰', 'h5': '📰', 'h6': '📰',
            'ul': '📋', 'ol': '📋', 'li': '•', 'table': '📊',
            'select': '📋', 'textarea': '📝', 'label': '🏷️',
            'nav': '🧭', 'main': '🏠', 'section': '📑', 'article': '📰',
            'header': '🔝', 'footer': '🔚', 'aside': '📌'
        }
        return emoji_map.get(tag_name, '📄')
    
    def _get_priority_indicator(self, score: int) -> str:
        """Get visual priority indicator"""
        if score >= 90:
            return "🎯🔥"  # Highest priority
        elif score >= 70:
            return "🎯"    # High priority  
        elif score >= 50:
            return "⭐"    # Medium priority
        elif score >= 30:
            return "💫"    # Low priority
        else:
            return "⚪"    # No automation value
    
    def _build_css_selector(self, element: Tag) -> str:
        """Build CSS selector path to element"""
        path_parts = []
        current = element
        
        while current and current.name:
            part = current.name
            
            # Use data-testid if available (highest priority)
            if current.get('data-testid'):
                part = f"{part}[data-testid='{current.get('data-testid')}']"
                path_parts.insert(0, part)
                break  # data-testid should be unique
            # Use id if available (second priority)
            elif current.get('id'):
                part = f"{part}#{current.get('id')}"
                path_parts.insert(0, part)
                break  # id should be unique
            # Use class if available
            elif current.get('class'):
                classes = '.'.join(current.get('class', []))
                part = f"{part}.{classes}"
            
            path_parts.insert(0, part)
            current = current.parent
            
        return ' > '.join(path_parts)
    
    def _build_xpath_absolute(self, element: Tag) -> str:
        """Build absolute XPath to element"""
        path_parts = []
        current = element
        
        while current and current.name:
            siblings = [sibling for sibling in current.parent.children 
                       if hasattr(sibling, 'name') and sibling.name == current.name] if current.parent else [current]
            
            if len(siblings) > 1:
                index = siblings.index(current) + 1
                path_parts.insert(0, f"{current.name}[{index}]")
            else:
                path_parts.insert(0, current.name)
                
            current = current.parent
            
        return '/' + '/'.join(path_parts) if path_parts else ''
    
    def _build_xpath_simplified(self, element: Tag) -> str:
        """Build simplified XPath using attributes when possible"""
        # Use data-testid if available
        if element.get('data-testid'):
            return f"//{element.name}[@data-testid='{element.get('data-testid')}']"
        # Use id if available
        elif element.get('id'):
            return f"//{element.name}[@id='{element.get('id')}']"
        # Use aria-label if available
        elif element.get('aria-label'):
            return f"//{element.name}[@aria-label='{element.get('aria-label')}']"
        # Use text content if meaningful
        elif element.get_text(strip=True):
            text = element.get_text(strip=True)[:30]  # Limit length
            return f"//{element.name}[contains(text(), '{text}')]"
        else:
            return self._build_xpath_absolute(element)
    
    def _build_jquery_selector(self, element: Tag) -> str:
        """Build jQuery-style selector"""
        # jQuery syntax is similar to CSS but with $ prefix
        css_selector = self._build_css_selector(element)
        return f"$('{css_selector}')"
    
    def _build_beautiful_soup_selector(self, element: Tag) -> str:
        """Build Beautiful Soup find/select syntax"""
        if element.get('data-testid'):
            return f"soup.find('{element.name}', {{'data-testid': '{element.get('data-testid')}'}})"
        elif element.get('id'):
            return f"soup.find('{element.name}', {{'id': '{element.get('id')}'}})"
        elif element.get('class'):
            classes = element.get('class', [])
            return f"soup.find('{element.name}', class_={classes})"
        else:
            return f"soup.find('{element.name}')"
    
    def _generate_regex_patterns(self, element: Tag, text_content: str) -> List[str]:
        """Generate useful regex patterns for text-based targeting"""
        patterns = []
        
        # Pattern for exact text match
        if text_content.strip():
            escaped_text = re.escape(text_content.strip())
            patterns.append(f"r'{escaped_text}'")
        
        # Pattern for partial text match
        if len(text_content.strip()) > 10:
            words = text_content.strip().split()[:3]  # First 3 words
            if words:
                pattern = r'\s+'.join(re.escape(word) for word in words)
                patterns.append(f"r'{pattern}'")
        
        return patterns
    
    def _calculate_priority_score(self, element: Tag, automation_attrs: Dict, aria_attrs: Dict) -> int:
        """Calculate automation priority score (0-100)"""
        score = 0
        
        # Automation-friendly attributes (highest priority)
        if element.get('data-testid'):
            score += 50
        if element.get('id'):
            score += 30
        if aria_attrs:
            score += 20
        
        # Interactive elements get priority
        if element.name in ['button', 'input', 'select', 'textarea', 'a']:
            score += 20
        
        # Form elements get extra priority
        if element.name in ['form']:
            score += 15
        
        # Navigation elements
        if element.get('role') in ['navigation', 'menu', 'menuitem']:
            score += 10
        
        # Has meaningful text
        if element.get_text(strip=True):
            score += 5
        
        return min(score, 100)  # Cap at 100
    
    def _determine_automation_strategies(self, element: Tag, automation_attrs: Dict, aria_attrs: Dict) -> List[str]:
        """Determine available automation strategies for element"""
        strategies = []
        
        if element.get('data-testid'):
            strategies.append('data-testid')
        if element.get('id'):
            strategies.append('id')
        if aria_attrs:
            strategies.append('aria-attributes')
        if element.get('class'):
            strategies.append('css-class')
        if element.get_text(strip=True):
            strategies.append('text-content')
        if element.name in ['button', 'input', 'select', 'textarea']:
            strategies.append('selenium-direct')
        
        strategies.append('xpath')
        strategies.append('css-selector')
        
        return strategies
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis"""
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def export_automation_registry(self, format: str = 'json') -> str:
        """Export automation registry in specified format"""
        if format == 'json':
            return json.dumps([asdict(target) for target in self.automation_registry], indent=2)
        elif format == 'python':
            return self._export_python_registry()
        elif format == 'summary':
            return self._export_summary()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_python_registry(self) -> str:
        """Export as Python code for direct use"""
        lines = [
            "# AI Automation Registry - Generated by AIDOMBeautifier",
            "AUTOMATION_TARGETS = {",
        ]
        
        for target in self.automation_registry:
            if target.priority_score >= 50:  # Only high-priority targets
                lines.append(f"    '{target.element_id}': {{")
                lines.append(f"        'tag': '{target.tag}',")
                lines.append(f"        'text': '{target.text}',")
                lines.append(f"        'css': '{target.css_selector}',")
                lines.append(f"        'xpath': '{target.xpath_simplified}',")
                lines.append(f"        'strategies': {target.automation_strategies},")
                lines.append(f"        'priority': {target.priority_score}")
                lines.append("    },")
        
        lines.append("}")
        return '\n'.join(lines)
    
    def _export_summary(self) -> str:
        """Export summary for AI context"""
        high_priority = [t for t in self.automation_registry if t.priority_score >= 70]
        medium_priority = [t for t in self.automation_registry if 50 <= t.priority_score < 70]
        
        lines = [
            "🎯 AUTOMATION REGISTRY SUMMARY",
            "=" * 40,
            f"High Priority Targets: {len(high_priority)}",
            f"Medium Priority Targets: {len(medium_priority)}",
            f"Total Automation Targets: {len(self.automation_registry)}",
            "",
            "🔥 TOP AUTOMATION TARGETS:",
        ]
        
        for target in high_priority[:10]:  # Top 10
            lines.append(f"  {target.tag.upper()} - {target.text[:30]} - Score: {target.priority_score}")
            lines.append(f"    CSS: {target.css_selector}")
            lines.append(f"    XPath: {target.xpath_simplified}")
            lines.append("")
        
        return '\n'.join(lines)


def beautify_current_looking_at() -> Tuple[str, List[AutomationTarget]]:
    """Beautify the current /looking_at/ simple_dom.html file"""
    import os
    
    simple_dom_path = "browser_automation/looking_at/simple_dom.html"
    
    if not os.path.exists(simple_dom_path):
        raise FileNotFoundError(f"No current DOM state found at {simple_dom_path}")
    
    with open(simple_dom_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    beautifier = AIDOMBeautifier()
    beautified_html, registry = beautifier.beautify_dom(html_content)
    
    # Save beautified version
    with open("browser_automation/looking_at/beautiful_dom.html", 'w', encoding='utf-8') as f:
        f.write(beautified_html)
    
    # Save automation registry
    with open("browser_automation/looking_at/automation_registry.json", 'w', encoding='utf-8') as f:
        f.write(beautifier.export_automation_registry('json'))
    
    # Save Python registry
    with open("browser_automation/looking_at/automation_targets.py", 'w', encoding='utf-8') as f:
        f.write(beautifier.export_automation_registry('python'))
    
    # Save summary
    with open("browser_automation/looking_at/automation_summary.txt", 'w', encoding='utf-8') as f:
        f.write(beautifier.export_automation_registry('summary'))
    
    return beautified_html, registry


if __name__ == "__main__":
    # Test with current /looking_at/ state
    try:
        beautified, registry = beautify_current_looking_at()
        print("🎉 DOM Beautification Complete!")
        print(f"📊 Found {len(registry)} automation targets")
        print(f"🎯 High priority targets: {len([t for t in registry if t.priority_score >= 70])}")
        print("\n📁 Generated files:")
        print("  - browser_automation/looking_at/beautiful_dom.html")
        print("  - browser_automation/looking_at/automation_registry.json") 
        print("  - browser_automation/looking_at/automation_targets.py")
        print("  - browser_automation/looking_at/automation_summary.txt")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("💡 Run browser_scrape_page first to capture current page state")