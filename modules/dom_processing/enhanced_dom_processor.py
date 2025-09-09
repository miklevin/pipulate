#!/usr/bin/env python3
"""
🔧 ENHANCED DOM PROCESSOR FOR 2ND-STAGE AUTOMATION

This module enhances the DOM processing pipeline to:
1. Clean excessive whitespace from simple_dom.html
2. Capture complete redirect chains with selenium-wire
3. Prepare automation targets for Google search and other sites
4. Set up structured data for 2nd-stage lookups and automation

Key improvements:
- Whitespace normalization without losing semantic structure
- Complete HTTP transaction logging
- Google-specific automation target identification
- Regex and grep-friendly output formatting
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup, Tag, NavigableString
from urllib.parse import urlparse


class EnhancedDOMProcessor:
    """Enhanced DOM processor for 2nd-stage automation preparation"""
    
    def __init__(self):
        self.redirect_chain = []
        self.google_targets = {}
        self.automation_hints = {}
        
    def clean_simple_dom(self, html_content: str) -> str:
        """
        Clean excessive whitespace from simple_dom.html while preserving structure
        
        Rules:
        - Remove excessive line breaks (more than 2 consecutive)
        - Normalize spaces within text content  
        - Keep single spaces between attributes
        - Preserve semantic line breaks for readability
        - Don't lose any automation-relevant content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Clean up text nodes - normalize whitespace
        for text_node in soup.find_all(string=True):
            if isinstance(text_node, NavigableString):
                # Normalize internal whitespace but preserve meaningful breaks
                cleaned_text = re.sub(r'\s+', ' ', str(text_node)).strip()
                if cleaned_text != str(text_node).strip():
                    text_node.replace_with(cleaned_text)
        
        # Convert back to string and clean up formatting
        html_str = str(soup)
        
        # Remove excessive line breaks (more than 2 consecutive)
        html_str = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_str)
        
        # Clean up spaces around tags while preserving structure
        html_str = re.sub(r'>\s+<', '><', html_str)
        
        # Add strategic line breaks for readability and grep-ability
        html_str = re.sub(r'(<(?:div|section|article|nav|main|header|footer|form|input|button|select|textarea)[^>]*>)', r'\n\1', html_str)
        html_str = re.sub(r'(</(?:div|section|article|nav|main|header|footer|form)>)', r'\1\n', html_str)
        
        # Final cleanup - remove leading/trailing whitespace from lines
        lines = html_str.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        return '\n'.join(cleaned_lines)
    
    def extract_redirect_chain(self, selenium_requests) -> List[Dict]:
        """
        Extract complete redirect chain from selenium-wire requests
        
        Returns detailed information about each step in the redirect chain
        """
        redirect_chain = []
        
        for request in selenium_requests:
            if request.response:
                redirect_info = {
                    'url': request.url,
                    'method': request.method,
                    'status_code': request.response.status_code,
                    'headers': dict(request.response.headers),
                    'request_headers': dict(request.headers),
                    'timestamp': str(request.date),
                    'is_redirect': 300 <= request.response.status_code < 400
                }
                
                # Check for redirect location
                if 'location' in request.response.headers:
                    redirect_info['redirect_to'] = request.response.headers['location']
                
                redirect_chain.append(redirect_info)
        
        return redirect_chain
    
    def identify_google_search_targets(self, soup: BeautifulSoup) -> Dict:
        """
        Identify Google-specific search automation targets
        
        Returns structured data for Google search automation
        """
        google_targets = {
            'search_box': None,
            'search_button': None,
            'suggestions': None,
            'results_container': None,
            'result_items': [],
            'pagination': None
        }
        
        # Search box identification (multiple strategies)
        search_box_selectors = [
            {'selector': 'input[name="q"]', 'priority': 100, 'strategy': 'name_attribute'},
            {'selector': 'textarea[name="q"]', 'priority': 95, 'strategy': 'textarea_variant'},
            {'selector': 'input[type="search"]', 'priority': 80, 'strategy': 'type_attribute'},
            {'selector': 'input[aria-label*="Search"]', 'priority': 70, 'strategy': 'aria_label'},
            {'selector': 'input[placeholder*="Search"]', 'priority': 60, 'strategy': 'placeholder'},
        ]
        
        for target in search_box_selectors:
            elements = soup.select(target['selector'])
            if elements:
                google_targets['search_box'] = {
                    'element': elements[0],
                    'css_selector': target['selector'],
                    'priority': target['priority'],
                    'strategy': target['strategy'],
                    'xpath': self._element_to_xpath(elements[0])
                }
                break
        
        # Search button identification
        search_button_selectors = [
            {'selector': 'input[name="btnK"]', 'priority': 100, 'strategy': 'google_search_button'},
            {'selector': 'button[type="submit"]', 'priority': 80, 'strategy': 'submit_button'},
            {'selector': 'input[value*="Search"]', 'priority': 70, 'strategy': 'search_value'},
            {'selector': 'button[aria-label*="Search"]', 'priority': 60, 'strategy': 'aria_search'},
        ]
        
        for target in search_button_selectors:
            elements = soup.select(target['selector'])
            if elements:
                google_targets['search_button'] = {
                    'element': elements[0],
                    'css_selector': target['selector'],
                    'priority': target['priority'],
                    'strategy': target['strategy'],
                    'xpath': self._element_to_xpath(elements[0])
                }
                break
        
        # Results container identification
        results_selectors = [
            '#search',  # Main Google results container
            '#results', 
            '.g',       # Individual result items
            '[data-ved]' # Google result tracking
        ]
        
        for selector in results_selectors:
            elements = soup.select(selector)
            if elements:
                if selector == '.g':
                    google_targets['result_items'] = [
                        {
                            'element': elem,
                            'css_selector': f'.g:nth-child({i+1})',
                            'xpath': self._element_to_xpath(elem)
                        }
                        for i, elem in enumerate(elements[:10])  # Top 10 results
                    ]
                else:
                    google_targets['results_container'] = {
                        'element': elements[0],
                        'css_selector': selector,
                        'xpath': self._element_to_xpath(elements[0])
                    }
        
        return google_targets
    
    def generate_automation_hints(self, soup: BeautifulSoup, url: str) -> Dict:
        """
        Generate automation hints based on page analysis
        
        Returns actionable automation strategies
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        hints = {
            'domain': domain,
            'automation_strategy': 'generic',
            'key_elements': [],
            'suggested_actions': [],
            'regex_patterns': [],
            'grep_targets': []
        }
        
        # Domain-specific strategies
        if 'google.com' in domain:
            hints['automation_strategy'] = 'google_search'
            hints['suggested_actions'] = [
                'Navigate to https://google.com',
                'Wait for search box to be visible',
                'Type search query into input[name="q"]',
                'Press Enter or click search button',
                'Wait for results container #search',
                'Extract results from .g elements'
            ]
            hints['regex_patterns'] = [
                r'input\[name="q"\]',  # Search box
                r'<h3[^>]*>.*?</h3>',  # Result titles
                r'href="(/url\?q=[^"]*)"',  # Google result URLs
            ]
            hints['grep_targets'] = [
                'name="q"',
                'btnK',
                'class="g"',
                'data-ved'
            ]
        
        # Find forms for automation
        forms = soup.find_all('form')
        for i, form in enumerate(forms):
            form_info = {
                'type': 'form',
                'index': i,
                'action': form.get('action', ''),
                'method': form.get('method', 'GET'),
                'inputs': []
            }
            
            # Analyze form inputs
            inputs = form.find_all(['input', 'textarea', 'select'])
            for input_elem in inputs:
                input_info = {
                    'tag': input_elem.name,
                    'type': input_elem.get('type', ''),
                    'name': input_elem.get('name', ''),
                    'id': input_elem.get('id', ''),
                    'placeholder': input_elem.get('placeholder', ''),
                    'required': input_elem.get('required') is not None
                }
                form_info['inputs'].append(input_info)
            
            hints['key_elements'].append(form_info)
        
        return hints
    
    def _element_to_xpath(self, element: Tag) -> str:
        """Convert BeautifulSoup element to XPath"""
        if not element or not hasattr(element, 'name') or not element.name:
            return "//unknown"
            
        if not element.parent:
            return f"//{element.name}"
        
        # Build path from root
        path_parts = []
        current = element
        
        while current and hasattr(current, 'name') and current.name:
            if not current.parent:
                path_parts.insert(0, current.name)
                break
                
            # Count siblings of same type
            siblings = [s for s in current.parent.children if hasattr(s, 'name') and s.name == current.name]
            
            if len(siblings) > 1:
                try:
                    index = siblings.index(current) + 1
                    path_parts.insert(0, f"{current.name}[{index}]")
                except ValueError:
                    path_parts.insert(0, current.name)
            else:
                path_parts.insert(0, current.name)
            
            current = current.parent
        
        return '/' + '/'.join(path_parts) if path_parts else "//unknown"
    
    def process_looking_at_directory(self, looking_at_dir: str = "browser_automation/looking_at") -> Dict:
        """
        Process all files in /looking_at/ directory for 2nd-stage automation
        
        Returns comprehensive analysis and cleaned files
        """
        results = {
            'files_processed': [],
            'automation_ready': False,
            'google_targets': {},
            'automation_hints': {},
            'redirect_chain': [],
            'cleaned_files': []
        }
        
        # Process simple_dom.html - but skip cleaning since it's now LLM-optimized
        simple_dom_path = os.path.join(looking_at_dir, 'simple_dom.html')
        if os.path.exists(simple_dom_path):
            with open(simple_dom_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            results['files_processed'].append('simple_dom.html')
            
            # Analyze for automation targets using existing content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check if this looks like Google
            page_title = soup.find('title')
            current_url = "unknown"
            
            # Try to get URL from headers.json
            headers_path = os.path.join(looking_at_dir, 'headers.json')
            if os.path.exists(headers_path):
                with open(headers_path, 'r') as f:
                    headers_data = json.load(f)
                    current_url = headers_data.get('url', 'unknown')
            
            # Generate automation hints
            results['automation_hints'] = self.generate_automation_hints(soup, current_url)
            
            # If it's Google, extract Google-specific targets
            if 'google.com' in current_url.lower():
                results['google_targets'] = self.identify_google_search_targets(soup)
                results['automation_ready'] = True
        
        # Create automation-ready summary
        summary_path = os.path.join(looking_at_dir, 'automation_ready_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("🎯 2ND-STAGE AUTOMATION READINESS REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Files Processed: {len(results['files_processed'])}\n")
            f.write(f"Automation Ready: {'✅ YES' if results['automation_ready'] else '❌ NO'}\n")
            f.write(f"Domain Strategy: {results['automation_hints'].get('automation_strategy', 'unknown')}\n\n")
            
            if results['automation_hints'].get('suggested_actions'):
                f.write("🚀 SUGGESTED AUTOMATION SEQUENCE:\n")
                for i, action in enumerate(results['automation_hints']['suggested_actions'], 1):
                    f.write(f"  {i}. {action}\n")
                f.write("\n")
            
            if results['automation_hints'].get('grep_targets'):
                f.write("🔍 GREP TARGETS FOR VERIFICATION:\n")
                for target in results['automation_hints']['grep_targets']:
                    f.write(f"  grep '{target}' simple_dom.html\n")
                f.write("\n")
            
            if results['automation_hints'].get('regex_patterns'):
                f.write("📝 REGEX PATTERNS FOR EXTRACTION:\n")
                for pattern in results['automation_hints']['regex_patterns']:
                    f.write(f"  {pattern}\n")
                f.write("\n")
        
        results['cleaned_files'].append(summary_path)
        
        return results


def process_current_looking_at():
    """Process the current /looking_at/ directory"""
    processor = EnhancedDOMProcessor()
    results = processor.process_looking_at_directory()
    
    print("🔧 ENHANCED DOM PROCESSING COMPLETE!")
    print("=" * 40)
    print(f"📁 Files processed: {len(results['files_processed'])}")
    print(f"🎯 Automation ready: {'✅ YES' if results['automation_ready'] else '❌ NO'}")
    print(f"🌐 Strategy: {results['automation_hints'].get('automation_strategy', 'unknown')}")
    
    if results['cleaned_files']:
        print("\n📄 Generated files:")
        for file_path in results['cleaned_files']:
            print(f"  - {file_path}")
    
    return results


if __name__ == "__main__":
    process_current_looking_at()