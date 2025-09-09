#!/usr/bin/env python3
"""
Adaptive Transparency System Verification Test

Tests all components of the capability-aware AI assistance system:
1. Local LLM helper tools (file access, log search, context)
2. Context pre-seeding system
3. Capability-aware documentation
4. MCP tool registration and functionality
"""

import requests
import json
import time
from pathlib import Path

def test_mcp_tool(tool_name, params=None):
    """Test an MCP tool via the executor endpoint"""
    if params is None:
        params = {}
    
    try:
        response = requests.post(
            "http://localhost:5001/mcp-tool-executor",
            headers={"Content-Type": "application/json"},
            json={"tool": tool_name, "params": params},
            timeout=10
        )
        
        # Handle both 200 and 503 status codes (503 is used by some MCP tools)
        if response.status_code in [200, 503]:
            result = response.json()
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("🧪 Testing Adaptive Transparency System")
    print("=" * 50)
    
    # Test 1: Local LLM Context Tool
    print("\n1. Testing Local LLM Context Tool...")
    result = test_mcp_tool("local_llm_get_context")
    if result["success"] and result["data"].get("success"):
        context = result["data"]["context"]
        print(f"   ✅ Context retrieved successfully")
        print(f"   📊 System: {context['system_overview']['name']}")
        print(f"   🔧 Tools: {len(context['available_mcp_tools'])} categories")
        print(f"   🗂️ Directories: {len(context['key_directories'])} mapped")
    else:
        print(f"   ❌ Context tool failed: {result.get('error', 'Unknown error')}")
    
    # Test 2: File Listing Tool
    print("\n2. Testing File Listing Tool...")
    result = test_mcp_tool("local_llm_list_files", {"directory": "training"})
    if result["success"] and result["data"].get("success"):
        files = result["data"]["files"]
        print(f"   ✅ Listed {len(files)} items in training directory")
        guide_files = [f for f in files if "guide" in f["name"] or "prompt" in f["name"]]
        print(f"   📚 Found {len(guide_files)} guidance files")
    else:
        print(f"   ❌ File listing failed: {result.get('error', 'Unknown error')}")
    
    # Test 3: File Reading Tool
    print("\n3. Testing File Reading Tool...")
    result = test_mcp_tool("local_llm_read_file", {
        "file_path": "training/system_prompt.md", 
        "max_lines": 10
    })
    if result["success"] and result["data"].get("success"):
        content = result["data"]["content"]
        lines_shown = result["data"]["displayed_lines"]
        total_lines = result["data"]["total_lines"]
        print(f"   ✅ Read {lines_shown}/{total_lines} lines from system prompt")
        print(f"   📄 Content preview: {content[:100]}...")
    else:
        print(f"   ❌ File reading failed: {result.get('error', 'Unknown error')}")
    
    # Test 4: Log Grep Tool
    print("\n4. Testing Log Grep Tool...")
    result = test_mcp_tool("local_llm_grep_logs", {
        "pattern": "FINDER_TOKEN", 
        "max_results": 3
    })
    if result["success"] and result["data"].get("success"):
        matches = result["data"]["matches"]
        print(f"   ✅ Found {len(matches)} FINDER_TOKEN entries")
        if matches:
            latest = matches[-1]
            print(f"   🔍 Latest: Line {latest['line_number']}")
    else:
        print(f"   ❌ Log grep failed: {result.get('error', 'Unknown error')}")
    
    # Test 5: Documentation Files
    print("\n5. Testing Documentation Architecture...")
    docs_to_check = [
        "training/system_prompt.md",
        "training/advanced_ai_guide.md"
    ]
    
    for doc_path in docs_to_check:
        if Path(doc_path).exists():
            size = Path(doc_path).stat().st_size
            print(f"   ✅ {doc_path} exists ({size:,} bytes)")
        else:
            print(f"   ❌ {doc_path} missing")
    
    # Test 6: Context File Generation
    print("\n6. Testing Context File Generation...")
    context_file = Path("data/local_llm_context.json")
    if context_file.exists():
        with open(context_file, 'r') as f:
            context_data = json.load(f)
        
        print(f"   ✅ Context file exists ({context_file.stat().st_size:,} bytes)")
        print(f"   🎯 System role: {context_data['system_overview']['local_llm_role']}")
        
        tool_count = sum(len(tools) for tools in context_data['available_mcp_tools'].values())
        print(f"   🔧 Total tools documented: {tool_count}")
    else:
        print(f"   ❌ Context file missing at {context_file}")
    
    print("\n" + "=" * 50)
    print("🎯 Adaptive Transparency System Verification Complete")
    print("\nSystem Status:")
    print("• Local LLM: Guided assistant with MCP tool access")
    print("• Advanced AI: Full radical transparency exploration")
    print("• Context: Pre-seeded for immediate capability awareness")
    print("• Tools: Capability-aware with appropriate security boundaries")

if __name__ == "__main__":
    main() 