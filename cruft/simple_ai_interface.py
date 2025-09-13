#!/usr/bin/env python3
"""
Simple AI Interface - Level 3 Progressive Intelligence Hierarchy
For lightweight local LLMs that can only handle [command parameter] patterns

This is the ultimate simplification of the golden path system.
"""

import asyncio
import sys
import re
from pathlib import Path

# Add the pipulate directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_tools import (
    execute_automation_recipe,
    pipeline_state_inspector,
    browser_scrape_page,
    browser_analyze_scraped_page,
    browser_automate_workflow_walkthrough,
    local_llm_grep_logs,
    local_llm_read_file,
    local_llm_list_files,
    ui_flash_element,
    ui_list_elements
)

class SimpleAIInterface:
    """
    Ultra-simplified interface for lightweight local LLMs
    Pattern: [command parameter] -> result
    """
    
    def __init__(self):
        self.commands = {
            'execute_automation_recipe': self.execute_recipe,
            'automation_recipe': self.execute_recipe,  # Alias
            'recipe': self.execute_recipe,  # Short alias
            'pipeline_state': self.get_pipeline_state,
            'state': self.get_pipeline_state,  # Alias
            'scrape_page': self.scrape_page,
            'scrape': self.scrape_page,  # Alias
            'analyze_page': self.analyze_page,
            'analyze': self.analyze_page,  # Alias
            'automate_workflow': self.automate_workflow,
            'automate': self.automate_workflow,  # Alias
            'grep_logs': self.grep_logs,
            'logs': self.grep_logs,  # Alias
            'read_file': self.read_file,
            'read': self.read_file,  # Alias
            'list_files': self.list_files,
            'list': self.list_files,  # Alias
            'flash_element': self.flash_element,
            'flash': self.flash_element,  # Alias
            'list_elements': self.list_elements,
            'elements': self.list_elements,  # Alias
        }
    
    async def execute_recipe(self, parameter):
        """Execute automation recipe with minimal parameters"""
        # Default to profile_creation_recipe if no specific recipe given
        recipe = parameter if parameter else 'profile_creation_recipe'
        
        result = await execute_automation_recipe({
            'origin': 'http://localhost:5001',
            'recipe': recipe
        })
        
        return f"✅ Recipe '{recipe}' executed with {result.get('success_rate', 0)}% success rate"
    
    async def get_pipeline_state(self, parameter):
        """Get pipeline state information"""
        result = await pipeline_state_inspector({})
        return f"📊 Pipeline state: {len(result.get('active_workflows', []))} active workflows"
    
    async def scrape_page(self, parameter):
        """Scrape a web page"""
        url = parameter if parameter.startswith('http') else f'http://localhost:5001/{parameter}'
        
        result = await browser_scrape_page({
            'url': url,
            'take_screenshot': True
        })
        
        return f"📸 Scraped {url} - Screenshot saved to {result.get('looking_at_files', {}).get('screenshot', 'N/A')}"
    
    async def analyze_page(self, parameter):
        """Analyze scraped page content"""
        analysis_type = parameter if parameter else 'all'
        
        result = await browser_analyze_scraped_page({
            'analysis_type': analysis_type
        })
        
        return f"🔍 Analysis complete: {result.get('target_count', 0)} targets found"
    
    async def automate_workflow(self, parameter):
        """Automate browser workflow"""
        instructions = parameter if parameter else 'Click login button'
        
        result = await browser_automate_workflow_walkthrough({
            'instructions': instructions,
            'target_url': 'http://localhost:5001'
        })
        
        return f"🤖 Workflow automated: {result.get('success', 'Unknown')} status"
    
    async def grep_logs(self, parameter):
        """Search logs for specific terms"""
        search_term = parameter if parameter else 'FINDER_TOKEN'
        
        result = await local_llm_grep_logs({
            'search_term': search_term
        })
        
        return f"🔍 Found {len(result.get('matches', []))} log entries for '{search_term}'"
    
    async def read_file(self, parameter):
        """Read a file"""
        file_path = parameter if parameter else 'README.md'
        
        result = await local_llm_read_file({
            'file_path': file_path
        })
        
        return f"📄 Read {file_path}: {len(result.get('content', ''))} characters"
    
    async def list_files(self, parameter):
        """List files in directory"""
        directory = parameter if parameter else '.'
        
        result = await local_llm_list_files({
            'directory': directory
        })
        
        return f"📁 Found {len(result.get('files', []))} files in {directory}"
    
    async def flash_element(self, parameter):
        """Flash UI element for visual debugging"""
        selector = parameter if parameter else '.problematic-element'
        
        result = await ui_flash_element({
            'selector': selector,
            'color': 'red'
        })
        
        return f"⚡ Flashed element '{selector}': {result.get('success', 'Unknown')} status"
    
    async def list_elements(self, parameter):
        """List UI elements"""
        selector = parameter if parameter else 'h2, h3, h4'
        
        result = await ui_list_elements({
            'selector': selector
        })
        
        return f"🎯 Found {len(result.get('elements', []))} elements matching '{selector}'"

    def parse_command(self, input_text):
        """Parse [command parameter] pattern"""
        # Handle [command parameter] pattern
        bracket_match = re.match(r'\[([^\]]+)\]', input_text.strip())
        if bracket_match:
            parts = bracket_match.group(1).split(' ', 1)
            command = parts[0].lower()
            parameter = parts[1] if len(parts) > 1 else ''
            return command, parameter
        
        # Handle simple "command parameter" pattern
        parts = input_text.strip().split(' ', 1)
        command = parts[0].lower()
        parameter = parts[1] if len(parts) > 1 else ''
        return command, parameter

    async def process_command(self, input_text):
        """Process a simple command from local LLM"""
        command, parameter = self.parse_command(input_text)
        
        if command in self.commands:
            try:
                result = await self.commands[command](parameter)
                return result
            except Exception as e:
                return f"❌ Error executing '{command}': {str(e)}"
        else:
            available_commands = ', '.join(self.commands.keys())
            return f"❓ Unknown command '{command}'. Available: {available_commands}"

async def main():
    """Main entry point for simple AI interface"""
    interface = SimpleAIInterface()
    
    if len(sys.argv) < 2:
        print("Usage: python simple_ai_interface.py '[command parameter]'")
        print("Example: python simple_ai_interface.py '[recipe profile_creation_recipe]'")
        print("Example: python simple_ai_interface.py 'automation_recipe'")
        return
    
    # Join all arguments to handle spaces in commands
    input_text = ' '.join(sys.argv[1:])
    
    result = await interface.process_command(input_text)
    print(result)

if __name__ == "__main__":
    asyncio.run(main()) 