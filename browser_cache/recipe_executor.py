"""
🎯 BABY STEPS RECIPE EXECUTOR - Minimal Working Version

This is a ground-up rebuild of the recipe execution system.
Focus: Reliability over sophistication, baby steps to 100% success.

Phase 1: Get basic navigation and form filling working
Phase 2: Add template processing 
Phase 3: Add error handling and fallbacks
Phase 4: Add progressive feedback
Phase 5: Integrate with MCP tools
"""

import json
import time
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from loguru import logger


class RecipeExecutor:
    """
    🎯 Ultra-simple recipe executor that focuses on reliability.
    
    Design Philosophy:
    - Start with minimal functionality that works 100%
    - Add features incrementally with validation
    - Prefer explicit over implicit
    - Clear error messages over sophisticated recovery
    """
    
    def __init__(self, headless: bool = False, debug: bool = True):
        self.headless = headless
        self.debug = debug
        self.driver = None
        self.temp_profile_dir = None
        
    def setup_driver(self) -> bool:
        """Setup Chrome driver with minimal, reliable configuration."""
        try:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            
            if self.headless:
                options.add_argument('--headless')
            
            # Create temporary profile directory
            self.temp_profile_dir = tempfile.mkdtemp(prefix='baby_steps_automation_')
            options.add_argument(f'--user-data-dir={self.temp_profile_dir}')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            if self.debug:
                logger.info(f"🎯 BABY_STEPS: Driver setup complete, temp profile: {self.temp_profile_dir}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ BABY_STEPS: Driver setup failed: {e}")
            return False
    
    def cleanup_driver(self):
        """Clean up driver and temporary files."""
        if self.driver:
            try:
                self.driver.quit()
                if self.debug:
                    logger.info("🎯 BABY_STEPS: Driver quit successfully")
            except Exception as e:
                logger.warning(f"⚠️ BABY_STEPS: Driver quit warning: {e}")
        
        if self.temp_profile_dir:
            try:
                shutil.rmtree(self.temp_profile_dir, ignore_errors=True)
                if self.debug:
                    logger.info("🎯 BABY_STEPS: Temp profile cleanup complete")
            except Exception as e:
                logger.warning(f"⚠️ BABY_STEPS: Temp profile cleanup warning: {e}")
    
    def process_template_variables(self, text: str, template_data: Dict[str, Any]) -> str:
        """
        Process template variables in text.
        
        Phase 1: Simple string replacement with nested resolution
        Phase 2: Will add datetime processing, etc.
        """
        if not text:
            return text
            
        # Generate timestamp-based variables if needed
        now = datetime.now()
        default_variables = {
            'timestamp': now.strftime('%Y%m%d_%H%M%S'),
            'timestamp_short': now.strftime('%m%d%H%M'),
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S')
        }
        
        # Merge with provided template data - template_data takes precedence
        all_variables = {**default_variables, **(template_data or {})}
        
        # First, process template_data values that might contain nested variables
        processed_template_data = {}
        for key, value in all_variables.items():
            if isinstance(value, str):
                # Process nested template variables in the value
                processed_value = value
                for var_key, var_value in all_variables.items():
                    processed_value = processed_value.replace(f'{{{{ {var_key} }}}}', str(var_value))
                    processed_value = processed_value.replace(f'{{{{{var_key}}}}}', str(var_value))
                processed_template_data[key] = processed_value
            else:
                processed_template_data[key] = value
        
        # Now process the main text with the fully resolved variables
        processed_text = text
        for key, value in processed_template_data.items():
            # Handle both {{ key }} and {{key}} formats
            processed_text = processed_text.replace(f'{{{{ {key} }}}}', str(value))
            processed_text = processed_text.replace(f'{{{{{key}}}}}', str(value))
        
        if self.debug and processed_text != text:
            logger.info(f"🎯 BABY_STEPS: Template processed: '{text}' -> '{processed_text}'")
            
        return processed_text
    
    def find_element_with_selector(self, selector: Dict[str, str], timeout: int = 10):
        """Find element using selector dictionary."""
        selector_type = selector.get('type', '').lower()
        selector_value = selector.get('value', '')
        
        if not selector_type or not selector_value:
            raise ValueError(f"Invalid selector: {selector}")
        
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            if selector_type == 'id':
                return wait.until(EC.presence_of_element_located((By.ID, selector_value)))
            elif selector_type == 'css':
                return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector_value)))
            elif selector_type == 'name':
                return wait.until(EC.presence_of_element_located((By.NAME, selector_value)))
            elif selector_type == 'xpath':
                return wait.until(EC.presence_of_element_located((By.XPATH, selector_value)))
            else:
                raise ValueError(f"Unsupported selector type: {selector_type}")
                
        except Exception as e:
            logger.error(f"❌ BABY_STEPS: Element not found with selector {selector}: {e}")
            raise
    
    def execute_step(self, step: Dict[str, Any], template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single recipe step."""
        step_num = step.get('step', 0)
        step_type = step.get('type', 'unknown')
        description = step.get('description', f'Step {step_num}')
        step_params = step.get('params', {})
        
        if self.debug:
            logger.info(f"🎯 BABY_STEPS: Executing Step {step_num} ({step_type}): {description}")
        
        step_result = {
            'step': step_num,
            'type': step_type,
            'description': description,
            'success': False,
            'error': None,
            'details': {}
        }
        
        try:
            if step_type == 'navigate':
                # Navigate to URL
                url = step_params.get('url', '')
                if not url:
                    raise ValueError("No URL specified for navigate step")
                
                self.driver.get(url)
                step_result['details']['final_url'] = self.driver.current_url
                
                # Wait for specific element if specified
                wait_for = step_params.get('wait_for_element')
                if wait_for:
                    timeout = step_params.get('timeout_seconds', 15)
                    element = self.find_element_with_selector(wait_for, timeout)
                    step_result['details']['waited_for_element'] = wait_for
                
                step_result['success'] = True
                
            elif step_type == 'form_fill':
                # Fill form field
                selector = step_params.get('selector', {})
                text = step_params.get('text', '')
                
                # Process template variables
                processed_text = self.process_template_variables(text, template_data)
                
                # Find and fill element
                element = self.find_element_with_selector(selector)
                element.clear()
                element.send_keys(processed_text)
                
                step_result['details']['filled_text'] = processed_text
                step_result['details']['original_text'] = text
                step_result['success'] = True
                
            elif step_type == 'submit':
                # Click submit button
                selector = step_params.get('selector', {})
                wait_after = step_params.get('wait_after', 1000)
                
                element = self.find_element_with_selector(selector)
                element.click()
                
                # Wait after click
                time.sleep(wait_after / 1000.0)
                
                step_result['details']['wait_after_ms'] = wait_after
                step_result['success'] = True
                
            elif step_type == 'verify':
                # Basic verification - check current URL
                verify_url = step_params.get('url', self.driver.current_url)
                wait_seconds = step_params.get('wait_seconds', 2)
                
                # Navigate if needed
                if verify_url != self.driver.current_url:
                    self.driver.get(verify_url)
                
                time.sleep(wait_seconds)
                
                step_result['details']['current_url'] = self.driver.current_url
                step_result['details']['expected_url'] = verify_url
                step_result['success'] = True
                
            else:
                raise ValueError(f"Unknown step type: {step_type}")
                
        except Exception as e:
            step_result['error'] = str(e)
            step_result['success'] = False
            logger.error(f"❌ BABY_STEPS: Step {step_num} failed: {e}")
        
        return step_result
    
    def execute_recipe(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete recipe."""
        recipe_name = recipe_data.get('recipe_name', 'Unknown Recipe')
        steps = recipe_data.get('steps', [])
        form_data = recipe_data.get('form_data', {})
        timing = recipe_data.get('timing', {})
        
        if self.debug:
            logger.info(f"🎯 BABY_STEPS: Starting recipe execution: {recipe_name}")
        
        # Setup driver
        if not self.setup_driver():
            return {
                'success': False,
                'error': 'Failed to setup browser driver',
                'recipe_name': recipe_name
            }
        
        step_results = []
        
        try:
            for step in steps:
                # Execute step
                step_result = self.execute_step(step, form_data)
                step_results.append(step_result)
                
                # Apply timing delays
                step_type = step.get('type', '')
                delay_key = f"{step_type}_delay"
                if delay_key in timing:
                    delay = timing[delay_key]
                    if self.debug:
                        logger.info(f"🎯 BABY_STEPS: Applying {delay_key}: {delay}s")
                    time.sleep(delay)
                
                # Stop on failure
                if not step_result['success']:
                    logger.error(f"❌ BABY_STEPS: Stopping execution at failed step {step_result['step']}")
                    break
            
            # Calculate success
            successful_steps = sum(1 for result in step_results if result['success'])
            total_steps = len(step_results)
            success_rate = (successful_steps / total_steps) * 100 if total_steps > 0 else 0
            overall_success = success_rate >= 100  # Require 100% success for now
            
            result = {
                'success': overall_success,
                'recipe_name': recipe_name,
                'total_steps': total_steps,
                'successful_steps': successful_steps,
                'success_rate': success_rate,
                'step_results': step_results,
                'execution_time': datetime.now().isoformat()
            }
            
            if self.debug:
                logger.info(f"🎯 BABY_STEPS: Recipe complete - Success: {overall_success}, Rate: {success_rate:.1f}%")
            
            return result
            
        finally:
            self.cleanup_driver()
    
    def execute_recipe_from_file(self, recipe_path: str) -> Dict[str, Any]:
        """Execute a recipe from a JSON file."""
        try:
            with open(recipe_path, 'r') as f:
                recipe_data = json.load(f)
            
            return self.execute_recipe(recipe_data)
            
        except Exception as e:
            logger.error(f"❌ BABY_STEPS: Failed to load recipe from {recipe_path}: {e}")
            return {
                'success': False,
                'error': f'Failed to load recipe file: {str(e)}',
                'recipe_path': recipe_path
            }


# 🎯 BABY STEPS TEST FUNCTION
async def test_baby_steps_executor():
    """Test the baby steps executor with the profile creation recipe."""
    executor = RecipeExecutor(headless=False, debug=True)
    
    # Test with existing profile creation recipe
    recipe_path = "browser_automation/automation_recipes/http_localhost_5001/profile_creation_recipe.json"
    
    logger.info("🎯 BABY_STEPS: Starting test execution")
    result = executor.execute_recipe_from_file(recipe_path)
    
    logger.info(f"🎯 BABY_STEPS: Test complete - Success: {result.get('success', False)}")
    return result


if __name__ == "__main__":
    # Quick test
    import asyncio
    asyncio.run(test_baby_steps_executor()) 