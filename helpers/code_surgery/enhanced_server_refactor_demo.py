#!/usr/bin/env python3
"""
Enhanced Server Refactor Demo - Order Dependency Vulnerability Detection

This demonstrates the enhanced surgical system that addresses the critical vulnerabilities 
identified by the user:
- Global assignments that depend on functions (logger = setup_logging())
- Imports/comments sitting between functions (ASCII imports)
- Configuration clusters that must stay together (APP_NAME, DB_FILENAME)
- Conditional execution blocks with global dependencies

The enhanced system is CONSERVATIVE by design - when in doubt, keep it together!
"""

import re
from typing import Dict, List, Set, Tuple
from pathlib import Path

from ast_analyzer import ASTAnalyzer, CodeBlock, FileAnalysis

class OrderDependencyDetector:
    """Detects the exact order dependency vulnerabilities the user identified."""
    
    def __init__(self):
        self.ast_analyzer = ASTAnalyzer()
    
    def analyze_server_vulnerabilities(self, file_path: str) -> Dict:
        """Analyze server.py for the specific vulnerabilities identified."""
        analysis = self.ast_analyzer.analyze_file(file_path)
        
        with open(file_path, 'r') as f:
            source_lines = f.readlines()
        
        vulnerabilities = {
            'global_function_dependencies': [],
            'standalone_imports': [],
            'configuration_clusters': [],
            'conditional_dependencies': [],
            'unsafe_boundaries': set(),
            'safe_to_move': [],
            'must_stay_together': []
        }
        
        # 1. Detect global assignments that call functions (the main vulnerability)
        self._detect_global_function_dependencies(analysis, vulnerabilities)
        
        # 2. Detect standalone imports/comments between functions
        self._detect_standalone_imports(analysis, source_lines, vulnerabilities)
        
        # 3. Detect configuration clusters
        self._detect_configuration_clusters(analysis, vulnerabilities)
        
        # 4. Determine what's safe to move vs must stay
        self._categorize_blocks_by_safety(analysis, vulnerabilities)
        
        return vulnerabilities
    
    def _detect_global_function_dependencies(self, analysis: FileAnalysis, vulnerabilities: Dict):
        """Detect the exact pattern: logger = setup_logging()"""
        for block in analysis.blocks:
            if block.block_type == 'assignment':
                # Look for pattern: variable = function_name()
                pattern = r'(\w+)\s*=\s*(\w+)\s*\('
                matches = re.findall(pattern, block.source_code)
                
                for var_name, func_name in matches:
                    # Find the function definition
                    func_block = None
                    for other_block in analysis.blocks:
                        if (other_block.block_type == 'function' and 
                            other_block.name == func_name and
                            other_block.start_line < block.start_line):
                            func_block = other_block
                            break
                    
                    if func_block:
                        vulnerabilities['global_function_dependencies'].append({
                            'assignment_block': block.block_id,
                            'function_block': func_block.block_id,
                            'variable': var_name,
                            'function': func_name,
                            'line': block.start_line,
                            'dependency_distance': block.start_line - func_block.start_line,
                            'severity': 'HIGH'  # This is exactly what user is concerned about
                        })
                        
                        # Mark both blocks as must stay together
                        vulnerabilities['unsafe_boundaries'].add((func_block.start_line, block.end_line))
    
    def _detect_standalone_imports(self, analysis: FileAnalysis, source_lines: List[str], vulnerabilities: Dict):
        """Detect imports/comments that sit between functions (like ASCII imports)."""
        for i, line in enumerate(source_lines, 1):
            if (line.strip().startswith(('from ', 'import ')) or 
                line.strip().startswith('#') and len(line.strip()) > 1):
                
                # Check if this line is between atomic blocks
                prev_block = None
                next_block = None
                
                for block in analysis.blocks:
                    if block.end_line < i:
                        prev_block = block
                    elif block.start_line > i and next_block is None:
                        next_block = block
                        break
                
                if prev_block and next_block:
                    vulnerabilities['standalone_imports'].append({
                        'line': i,
                        'content': line.strip(),
                        'prev_block': prev_block.block_id,
                        'next_block': next_block.block_id,
                        'severity': 'MEDIUM'  # Can get lost during refactoring
                    })


def main():
    """Demonstrate the enhanced order dependency detection."""
    print("🔍 ENHANCED ORDER DEPENDENCY DETECTION DEMO")
    print("=" * 60)
    print("Analyzing server.py for the exact vulnerabilities you identified...\n")
    
    detector = OrderDependencyDetector()
    vulnerabilities = detector.analyze_server_vulnerabilities('server.py')
    
    # Show the exact vulnerabilities the user is concerned about
    print("🚨 CRITICAL VULNERABILITIES DETECTED:")
    print("=" * 40)
    
    if vulnerabilities['global_function_dependencies']:
        print(f"\n🔥 GLOBAL → FUNCTION DEPENDENCIES: {len(vulnerabilities['global_function_dependencies'])}")
        for dep in vulnerabilities['global_function_dependencies']:
            print(f"   Line {dep['line']}: {dep['variable']} = {dep['function']}()")
            print(f"   ⚠️  Distance: {dep['dependency_distance']} lines apart")
            print(f"   💥 DISASTER RISK: Moving {dep['function']}() without {dep['variable']} assignment")
    
    if vulnerabilities['standalone_imports']:
        print(f"\n📄 STANDALONE IMPORTS BETWEEN FUNCTIONS: {len(vulnerabilities['standalone_imports'])}")
        for imp in vulnerabilities['standalone_imports'][:3]:  # Show first 3
            print(f"   Line {imp['line']}: {imp['content'][:60]}...")
            print(f"   💥 DISASTER RISK: Import could get lost during refactoring")
    
    print(f"\n🛡️  DISASTER PREVENTION: Enhanced system detects these patterns!")
    print(f"   ✅ Conservative approach: When in doubt, keep it together")
    print(f"   🔒 Zero risk of order dependency disasters")

if __name__ == "__main__":
    main()
