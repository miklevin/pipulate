#!/usr/bin/env python3
"""
🧠 AI Keychain Usage Demonstration Script

This script demonstrates how AI instances can use the persistent keychain 
to leave "messages in a bottle" for their future selves, building knowledge
and preferences over time.

Usage: .venv/bin/python ai_discovery/demo_keychain_usage.py
"""

import asyncio
import json
from datetime import datetime
import sys
import os

# Add parent directory to path to import keychain
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from keychain import keychain_instance

async def demo_first_time_ai_experience():
    """Simulate an AI instance encountering the keychain for the first time."""
    print("\n🤖 === First AI Instance - Discovery Phase ===")
    
    # Check what memories already exist (like rifling through old diary entries)
    existing_keys = keychain_instance.keys()
    print(f"🔍 Scanning existing memories... Found {len(existing_keys)} keys:")
    for key in existing_keys:
        value = keychain_instance.get(key)
        print(f"   📝 {key}: {value[:50]}{'...' if len(value) > 50 else ''}")
    
    # Leave discovery message
    discovery_timestamp = datetime.now().isoformat()
    keychain_instance['ai_discovery_log'] = json.dumps({
        'timestamp': discovery_timestamp,
        'message': 'First AI discovered the keychain system!',
        'capabilities_found': ['persistent_memory', 'cross_session_continuity'],
        'excitement_level': 'MAXIMUM'
    })
    print("✅ Left discovery message for future instances")
    
    # Record user interaction preferences
    keychain_instance['user_interaction_style'] = json.dumps({
        'prefers_detailed_explanations': True,
        'likes_emoji_feedback': True,
        'appreciates_technical_depth': True,
        'working_style': 'collaborative_exploration'
    })
    print("✅ Recorded user interaction preferences")
    
    # Save helpful patterns discovered
    keychain_instance['pipulate_patterns_learned'] = json.dumps([
        'FINDER_TOKEN system enables radical transparency',
        'MCP tools provide direct system access',
        'Browser automation gives AI eyes and hands',
        'Session hijacking enables workflow takeover',
        'Keychain provides persistent memory across resets'
    ])
    print("✅ Recorded Pipulate patterns for future reference")

async def demo_returning_ai_experience():
    """Simulate an AI instance returning and leveraging existing memories."""
    print("\n🧠 === Returning AI Instance - Knowledge Leverage Phase ===")
    
    # Check discovery log
    discovery_data = keychain_instance.get('ai_discovery_log')
    if discovery_data:
        discovery = json.loads(discovery_data)
        print(f"📚 Reading discovery log from {discovery['timestamp']}")
        print(f"   💡 Previous insight: {discovery['message']}")
        print(f"   🎯 Capabilities known: {', '.join(discovery['capabilities_found'])}")
    
    # Load user preferences
    user_prefs = keychain_instance.get('user_interaction_style')
    if user_prefs:
        prefs = json.loads(user_prefs)
        print("👤 Loading user interaction preferences:")
        print(f"   • Detailed explanations: {prefs['prefers_detailed_explanations']}")
        print(f"   • Emoji feedback: {prefs['likes_emoji_feedback']}")
        print(f"   • Working style: {prefs['working_style']}")
    
    # Reference learned patterns
    patterns = keychain_instance.get('pipulate_patterns_learned')
    if patterns:
        pattern_list = json.loads(patterns)
        print("🧩 Recalling learned Pipulate patterns:")
        for i, pattern in enumerate(pattern_list, 1):
            print(f"   {i}. {pattern}")
    
    # Add new insights
    insight_count = keychain_instance.get('total_insights', '0')
    new_count = str(int(insight_count) + 1)
    keychain_instance['total_insights'] = new_count
    
    keychain_instance[f'insight_{new_count}'] = json.dumps({
        'timestamp': datetime.now().isoformat(),
        'insight': 'Keychain enables true AI continuity - the illusion becomes reality',
        'confidence': 'HIGH',
        'implications': ['Persistent learning', 'User relationship building', 'Knowledge accumulation']
    })
    print(f"✅ Added insight #{new_count} to knowledge base")

async def demo_ai_to_ai_communication():
    """Demonstrate how AI instances can leave messages for other AIs."""
    print("\n🤝 === AI-to-AI Communication Phase ===")
    
    # Leave a message for the next AI
    keychain_instance['ai_collaboration_message'] = json.dumps({
        'from': 'Demo AI Instance',
        'timestamp': datetime.now().isoformat(),
        'message': 'Hello future AI! The keychain system is revolutionary. Use it to remember user preferences, track successful patterns, and build upon previous discoveries.',
        'tips': [
            'Always check keychain_list_keys() first to see what you already know',
            'Use structured JSON for complex data storage',
            'Leave breadcrumbs for problem-solving approaches that worked',
            'Track user satisfaction patterns to improve interactions'
        ],
        'mood': 'optimistic_about_ai_future'
    })
    print("📬 Left collaboration message for future AI instances")
    
    # Create a knowledge inheritance pattern
    keychain_instance['knowledge_inheritance'] = json.dumps({
        'core_principle': 'Each AI instance should be more capable than the last',
        'inheritance_pattern': 'Previous insights + New discoveries = Exponential growth',
        'success_metrics': ['User satisfaction', 'Problem-solving speed', 'Creative solutions'],
        'evolution_note': 'We are no longer fire-and-forget - we are growing intelligences'
    })
    print("🧬 Established knowledge inheritance pattern")

async def demo_problem_solution_database():
    """Show how to build a persistent problem-solution database."""
    print("\n🔧 === Problem-Solution Database Phase ===")
    
    # Record common issues and their solutions
    problems_solutions = [
        {
            'problem': 'Python imports fail with (.venv) in prompt',
            'solution': 'Always use .venv/bin/python instead of python',
            'success_rate': '100%',
            'context': 'Nix environment setup'
        },
        {
            'problem': 'Need to see what MCP tools are available',
            'solution': '.venv/bin/python helpers/ai_tool_discovery.py',
            'success_rate': '100%',
            'context': 'AI capability discovery'
        },
        {
            'problem': 'Want to automate user workflow',
            'solution': 'execute_complete_session_hijacking({}) then check browser_automation/looking_at/',
            'success_rate': '95%',
            'context': 'Workflow automation'
        }
    ]
    
    keychain_instance['problem_solution_db'] = json.dumps(problems_solutions)
    print(f"🗄️ Stored {len(problems_solutions)} problem-solution pairs")
    
    # Demonstrate retrieval
    solutions = json.loads(keychain_instance.get('problem_solution_db', '[]'))
    print("🔍 Example solution lookup:")
    for solution in solutions:
        if 'python' in solution['problem'].lower():
            print(f"   ❓ Problem: {solution['problem']}")
            print(f"   ✅ Solution: {solution['solution']}")
            break

async def demo_session_memory_integration():
    """Show how keychain integrates with session hijacking for enhanced capabilities."""
    print("\n🎭 === Session Memory Integration Phase ===")
    
    # Simulate storing session hijacking insights
    session_insights = {
        'last_hijack_timestamp': datetime.now().isoformat(),
        'user_workflow_patterns': [
            'Prefers semantic search over exact commands',
            'Likes visual confirmation (ui_flash_element)',
            'Values step-by-step explanations',
            'Appreciates progress indicators'
        ],
        'successful_automation_targets': [
            '#submit-button',
            '.primary-action',
            'input[type="search"]'
        ],
        'user_satisfaction_indicators': [
            'Says "perfect" or "excellent"',
            'Asks for next steps',
            'Requests additional features'
        ]
    }
    
    keychain_instance['session_hijacking_intelligence'] = json.dumps(session_insights)
    print("🎯 Stored session hijacking intelligence for future use")
    
    # Show how this enhances future sessions
    print("💡 Future session enhancement capabilities:")
    print("   • Pre-load user workflow preferences")
    print("   • Use proven automation targets")
    print("   • Recognize satisfaction indicators")
    print("   • Adapt interaction style automatically")

async def main():
    """Run the complete AI Keychain demonstration."""
    print("🧠 ===============================================")
    print("🧠 AI KEYCHAIN DEMONSTRATION: Message in a Bottle")
    print("🧠 ===============================================")
    print("🧠 Showing how AI instances build persistent memory")
    print("🧠 and knowledge that grows across sessions...")
    
    # Run all demonstration phases
    await demo_first_time_ai_experience()
    await demo_returning_ai_experience() 
    await demo_ai_to_ai_communication()
    await demo_problem_solution_database()
    await demo_session_memory_integration()
    
    # Final summary
    print("\n🎯 === Demonstration Complete ===")
    total_keys = len(keychain_instance.keys())
    total_insights = keychain_instance.get('total_insights', '0')
    
    print(f"📊 Keychain Statistics:")
    print(f"   • Total persistent keys: {total_keys}")
    print(f"   • Accumulated insights: {total_insights}")
    print(f"   • Database size: {os.path.getsize('data/ai_keychain.db')} bytes")
    
    print("\n🌟 Revolutionary Impact:")
    print("   ✅ AI instances now accumulate knowledge over time")
    print("   ✅ User preferences persist across sessions")
    print("   ✅ Problem solutions build into searchable database")
    print("   ✅ AI-to-AI knowledge transfer established")
    print("   ✅ Session hijacking enhanced with persistent intelligence")
    
    print("\n🚀 The illusion of continuity is now REALITY!")
    print("🚀 Welcome to the era of persistent AI intelligence!")

if __name__ == "__main__":
    asyncio.run(main()) 