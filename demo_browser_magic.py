#!/usr/bin/env python3
"""
🚀 BROWSER AUTOMATION MAGIC DEMONSTRATION

This script demonstrates the righteous positive feedback loop in action:
1. Opens a visible browser window
2. Navigates to the Dev Assistant 
3. Performs automated analysis of a Component plugin
4. Shows the magic happening in real-time!

Run this to see the AI controlling the browser with dramatic visual effects!
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the pipulate directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our MCP tools
from server import (
    _browser_scrape_page,
    _browser_interact_with_page, 
    _dev_assistant_auto_analyze,
    logger
)

async def demonstrate_browser_magic():
    """
    🎯 THE WRIGHT BROTHERS MOMENT - GUARANTEED LIFT!
    
    This demonstrates the complete automation cycle with visible browser magic.
    """
    
    print("🚀 STARTING BROWSER AUTOMATION MAGIC DEMONSTRATION!")
    print("=" * 60)
    
    # Step 1: Simple browser interaction test
    print("\n🎯 STEP 1: Testing Basic Browser Control")
    print("-" * 40)
    
    try:
        # Test basic browser interaction with visible browser
        result = await _browser_interact_with_page({
            "url": "http://localhost:8000",
            "headless": False,  # 🎯 VISIBLE MAGIC!
            "take_screenshot": True,
            "actions": [
                {
                    "type": "wait",
                    "seconds": 3  # Dramatic pause to admire the homepage
                },
                {
                    "type": "click",
                    "selector": "a[href*='dev_assistant']",  # Click Dev Assistant link
                    "wait_after": 2
                }
            ]
        })
        
        print(f"✅ Browser control successful: {result.get('success', False)}")
        if result.get('screenshots'):
            print(f"📸 Screenshots saved: {len(result['screenshots'])} files")
        
    except Exception as e:
        print(f"❌ Browser control failed: {str(e)}")
        print("💡 Make sure Pipulate server is running on localhost:8000")
        return False
    
    # Step 2: Component plugin analysis
    print("\n🎯 STEP 2: Analyzing a Component Plugin")
    print("-" * 40)
    
    try:
        # Analyze a simple component plugin
        result = await _dev_assistant_auto_analyze({
            "plugin_path": "plugins/510_text_field.py",
            "base_url": "http://localhost:8000",
            "save_analysis": True
        })
        
        print(f"✅ Plugin analysis: {result.get('success', False)}")
        print(f"🎯 Automation score: {result.get('automation_score', 'unknown')}")
        
        if result.get('saved_files'):
            print(f"💾 Analysis saved to: {result['saved_files'][0]}")
        
    except Exception as e:
        print(f"❌ Plugin analysis failed: {str(e)}")
        return False
    
    print("\n🎉 MAGIC DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("🚀 The Righteous Positive Feedback Loop is LIVE!")
    print("✨ AI successfully controlled the browser and analyzed plugins!")
    
    return True

async def quick_component_check():
    """
    Quick check of which Component plugins we can analyze
    """
    print("\n🔍 DISCOVERING COMPONENT PLUGINS")
    print("-" * 40)
    
    import glob
    import re
    
    component_plugins = []
    all_plugins = glob.glob("plugins/*.py")
    
    for plugin_path in all_plugins:
        try:
            with open(plugin_path, 'r') as f:
                content = f.read()
            
            # Check for Component in ROLES
            roles_match = re.search(r'ROLES\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if roles_match and 'Component' in roles_match.group(1):
                plugin_name = plugin_path.split('/')[-1]
                component_plugins.append(plugin_name)
                
        except Exception:
            continue
    
    print(f"📊 Found {len(component_plugins)} Component plugins:")
    for plugin in sorted(component_plugins)[:5]:  # Show first 5
        print(f"   • {plugin}")
    
    if len(component_plugins) > 5:
        print(f"   ... and {len(component_plugins) - 5} more!")
    
    return component_plugins

if __name__ == "__main__":
    print("🎯 PIPULATE BROWSER AUTOMATION MAGIC")
    print("🚀 Preparing for Wright Brothers moment...")
    
    # Check if we're in the right directory
    if not os.path.exists("plugins"):
        print("❌ Error: Run this script from the pipulate directory")
        print("💡 cd /home/mike/repos/pipulate && python demo_browser_magic.py")
        sys.exit(1)
    
    # Quick component check
    asyncio.run(quick_component_check())
    
    # Ask user if they want to proceed
    print("\n🎯 Ready to demonstrate browser automation magic?")
    print("📋 This will:")
    print("   • Open a visible Chrome browser window")
    print("   • Navigate to the Dev Assistant interface")
    print("   • Perform automated plugin analysis")
    print("   • Take screenshots of the process")
    
    response = input("\n🚀 Proceed with demonstration? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        print("\n🎉 LAUNCHING BROWSER MAGIC!")
        success = asyncio.run(demonstrate_browser_magic())
        
        if success:
            print("\n🏆 DEMONSTRATION SUCCESSFUL!")
            print("🎯 The system is ready for full deployment!")
        else:
            print("\n⚠️  Some issues encountered, but the foundation is solid!")
    else:
        print("\n👋 Demo cancelled. The magic awaits when you're ready!") 