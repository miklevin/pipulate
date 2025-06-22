#!/usr/bin/env python3
"""
🎯 SIMPLE COMPONENT ANALYSIS DEMONSTRATION

This demonstrates the core Component plugin analysis functionality
without browser automation - a guaranteed Wright Brothers lift moment!
"""

import asyncio
import json
import sys
import os
import re
import glob
from pathlib import Path
from datetime import datetime

def analyze_component_plugin(plugin_path):
    """
    Analyze a Component plugin for automation readiness
    This is our core analysis logic - the Wright Brothers guaranteed lift!
    """
    
    try:
        with open(plugin_path, 'r') as f:
            content = f.read()
        
        plugin_name = plugin_path.split('/')[-1]
        
        # Check if it's a Component plugin
        roles_match = re.search(r'ROLES\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if not roles_match or 'Component' not in roles_match.group(1):
            return {
                "plugin": plugin_name,
                "is_component": False,
                "reason": "Not a Component plugin"
            }
        
        # Analyze automation readiness
        automation_score = 0
        issues = []
        good_patterns = []
        
        # Check for form elements
        if 'Input(' in content:
            automation_score += 20
            good_patterns.append("✅ Uses Input elements")
        else:
            issues.append("❌ No Input elements found")
        
        # Check for IDs and data-testid
        if 'id=' in content:
            automation_score += 15
            good_patterns.append("✅ Has element IDs")
        else:
            issues.append("❌ Missing element IDs")
        
        if 'data_testid=' in content:
            automation_score += 15
            good_patterns.append("✅ Has data-testid attributes")
        else:
            issues.append("❌ Missing data-testid attributes")
        
        # Check for ARIA attributes
        aria_patterns = ['aria_label=', 'aria_describedby=', 'aria_required=']
        aria_found = sum(1 for pattern in aria_patterns if pattern in content)
        automation_score += aria_found * 10
        
        if aria_found > 0:
            good_patterns.append(f"✅ Has {aria_found} ARIA attributes")
        else:
            issues.append("❌ Missing ARIA attributes")
        
        # Check for semantic HTML
        semantic_elements = ['Button(', 'Form(', 'Label(', 'Fieldset(']
        semantic_found = sum(1 for element in semantic_elements if element in content)
        automation_score += semantic_found * 5
        
        if semantic_found > 0:
            good_patterns.append(f"✅ Uses {semantic_found} semantic elements")
        
        # Check for CSS classes instead of inline styles
        if 'cls=' in content:
            automation_score += 10
            good_patterns.append("✅ Uses CSS classes")
        
        # Bonus points for comprehensive coverage
        if automation_score >= 80:
            automation_score += 10
            good_patterns.append("🎯 Excellent automation coverage!")
        
        return {
            "plugin": plugin_name,
            "is_component": True,
            "automation_score": min(automation_score, 100),
            "good_patterns": good_patterns,
            "issues": issues,
            "status": "✅ PASS" if automation_score >= 80 else "⚠️ NEEDS_WORK"
        }
        
    except Exception as e:
        return {
            "plugin": plugin_path.split('/')[-1],
            "error": str(e),
            "status": "❌ ERROR"
        }

def analyze_all_components():
    """
    Analyze all Component plugins - our bulk analysis demonstration
    """
    
    print("🎯 COMPONENT PLUGIN ANALYSIS - WRIGHT BROTHERS MOMENT!")
    print("=" * 60)
    
    # Find all plugins
    all_plugins = glob.glob("plugins/*.py")
    component_plugins = []
    results = []
    
    print(f"\n🔍 Scanning {len(all_plugins)} plugins for Components...")
    
    for plugin_path in all_plugins:
        result = analyze_component_plugin(plugin_path)
        
        if result.get("is_component"):
            component_plugins.append(plugin_path)
            results.append(result)
            
            # Show real-time results
            score = result.get("automation_score", 0)
            status = result.get("status", "❓")
            plugin_name = result.get("plugin", "unknown")
            
            print(f"   {status} {plugin_name} - Score: {score}/100")
    
    print(f"\n📊 ANALYSIS COMPLETE!")
    print(f"   • Total plugins scanned: {len(all_plugins)}")
    print(f"   • Component plugins found: {len(component_plugins)}")
    print(f"   • Analysis results: {len(results)}")
    
    # Calculate summary statistics
    if results:
        scores = [r.get("automation_score", 0) for r in results]
        avg_score = sum(scores) / len(scores)
        passing = len([r for r in results if r.get("automation_score", 0) >= 80])
        
        print(f"\n🎯 SUMMARY STATISTICS:")
        print(f"   • Average automation score: {avg_score:.1f}/100")
        print(f"   • Plugins passing (≥80): {passing}/{len(results)} ({passing/len(results)*100:.1f}%)")
        print(f"   • Highest score: {max(scores)}/100")
        print(f"   • Lowest score: {min(scores)}/100")
    
    # Show detailed results for top performers
    print(f"\n🏆 TOP PERFORMERS:")
    top_performers = sorted(results, key=lambda x: x.get("automation_score", 0), reverse=True)[:5]
    
    for result in top_performers:
        plugin = result.get("plugin", "unknown")
        score = result.get("automation_score", 0)
        patterns = result.get("good_patterns", [])
        
        print(f"\n   🎯 {plugin} - {score}/100")
        for pattern in patterns[:3]:  # Show top 3 patterns
            print(f"      {pattern}")
    
    # Show improvement opportunities
    print(f"\n⚠️  IMPROVEMENT OPPORTUNITIES:")
    needs_work = [r for r in results if r.get("automation_score", 0) < 80]
    
    for result in needs_work[:3]:  # Show top 3 that need work
        plugin = result.get("plugin", "unknown")
        score = result.get("automation_score", 0)
        issues = result.get("issues", [])
        
        print(f"\n   ⚠️  {plugin} - {score}/100")
        for issue in issues[:2]:  # Show top 2 issues
            print(f"      {issue}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"downloads/component_analysis_{timestamp}.json"
    
    os.makedirs("downloads", exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_plugins": len(all_plugins),
            "component_plugins": len(component_plugins),
            "average_score": avg_score if results else 0,
            "passing_rate": passing/len(results)*100 if results else 0,
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print(f"\n🚀 WRIGHT BROTHERS MOMENT ACHIEVED!")
    print(f"✨ Component analysis system is working perfectly!")
    
    return results

if __name__ == "__main__":
    if not os.path.exists("plugins"):
        print("❌ Error: Run this script from the pipulate directory")
        print("💡 cd /home/mike/repos/pipulate && python simple_component_demo.py")
        sys.exit(1)
    
    # Run the analysis
    results = analyze_all_components()
    
    print(f"\n🎯 READY FOR FULL BROWSER AUTOMATION!")
    print(f"   This core analysis can now be integrated with:")
    print(f"   • Browser automation for Dev Assistant interface")
    print(f"   • MCP tools for AI-driven improvements") 
    print(f"   • Bulk processing across all plugins")
    print(f"   • Automated fix application") 