#!/usr/bin/env python3
"""
Pre-Surgery State Capture - Forensic Documentation

This script captures the complete state of server.py before surgical refactoring.
Creates a comprehensive audit trail for "perfect backup, turn a little, try again"
Roomba-style iterative improvement process.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json

def get_git_status():
    """Get current git status and commit info."""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        status = result.stdout.strip()
        
        result = subprocess.run(['git', 'log', '-1', '--pretty=format:%H|%s|%an|%ad'], 
                              capture_output=True, text=True)
        commit_info = result.stdout.strip().split('|')
        
        return {
            'status': status,
            'last_commit': {
                'hash': commit_info[0] if len(commit_info) > 0 else 'unknown',
                'message': commit_info[1] if len(commit_info) > 1 else 'unknown',
                'author': commit_info[2] if len(commit_info) > 2 else 'unknown',
                'date': commit_info[3] if len(commit_info) > 3 else 'unknown'
            }
        }
    except Exception as e:
        return {'error': str(e)}

def get_file_metrics(file_path):
    """Get comprehensive file metrics."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Calculate token count estimate (rough approximation)
        token_estimate = len(content.split())
        
        return {
            'file_path': file_path,
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'total_characters': len(content),
            'token_estimate': token_estimate,
            'file_size_bytes': os.path.getsize(file_path),
            'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        }
    except Exception as e:
        return {'error': str(e)}

def run_ast_analysis():
    """Run AST analysis and capture results."""
    try:
        result = subprocess.run([
            sys.executable, 'helpers/code_surgery/ast_analyzer.py', 'server.py'
        ], capture_output=True, text=True)
        
        # Parse the output to extract key metrics
        output_lines = result.stdout.strip().split('\n')
        blocks_line = next((line for line in output_lines if 'Blocks found:' in line), None)
        imports_line = next((line for line in output_lines if 'Imports:' in line), None)
        exports_line = next((line for line in output_lines if 'Exports:' in line), None)
        
        blocks_count = int(blocks_line.split(': ')[1]) if blocks_line else 0
        imports_count = int(imports_line.split(': ')[1]) if imports_line else 0
        exports_count = int(exports_line.split(': ')[1]) if exports_line else 0
        
        return {
            'blocks_found': blocks_count,
            'imports_count': imports_count,
            'exports_count': exports_count,
            'raw_output': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        return {'error': str(e)}

def capture_dependency_state():
    """Capture the current dependency state."""
    core_files = ['server.py', 'mcp_tools.py', 'common.py']
    dependency_state = {}
    
    for file_path in core_files:
        if os.path.exists(file_path):
            dependency_state[file_path] = get_file_metrics(file_path)
    
    return dependency_state

def create_state_report():
    """Create comprehensive state report."""
    print("🏥 PRE-SURGERY STATE CAPTURE")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Git status
    print("📂 GIT STATUS")
    print("-" * 20)
    git_status = get_git_status()
    if 'error' not in git_status:
        print(f"Working Directory: {'Clean' if not git_status['status'] else 'Modified'}")
        print(f"Last Commit: {git_status['last_commit']['hash'][:8]}")
        print(f"Commit Message: {git_status['last_commit']['message']}")
        print(f"Author: {git_status['last_commit']['author']}")
        print(f"Date: {git_status['last_commit']['date']}")
    else:
        print(f"Error: {git_status['error']}")
    print()
    
    # File metrics
    print("📊 FILE METRICS")
    print("-" * 20)
    server_metrics = get_file_metrics('server.py')
    if 'error' not in server_metrics:
        print(f"Total Lines: {server_metrics['total_lines']:,}")
        print(f"Non-Empty Lines: {server_metrics['non_empty_lines']:,}")
        print(f"Total Characters: {server_metrics['total_characters']:,}")
        print(f"Token Estimate: {server_metrics['token_estimate']:,}")
        print(f"File Size: {server_metrics['file_size_bytes']:,} bytes")
    else:
        print(f"Error: {server_metrics['error']}")
    print()
    
    # AST analysis
    print("🧬 AST ANALYSIS")
    print("-" * 20)
    ast_results = run_ast_analysis()
    if 'error' not in ast_results:
        print(f"Atomic Blocks: {ast_results['blocks_found']}")
        print(f"Import Statements: {ast_results['imports_count']}")
        print(f"Export Statements: {ast_results['exports_count']}")
    else:
        print(f"Error: {ast_results['error']}")
    print()
    
    # Dependency state
    print("🔗 DEPENDENCY STATE")
    print("-" * 20)
    dep_state = capture_dependency_state()
    for file_path, metrics in dep_state.items():
        if 'error' not in metrics:
            print(f"{file_path}: {metrics['token_estimate']:,} tokens, {metrics['total_lines']} lines")
        else:
            print(f"{file_path}: Error - {metrics['error']}")
    print()
    
    # Target distribution
    print("🎯 REFACTORING TARGET")
    print("-" * 20)
    total_tokens = sum(metrics['token_estimate'] for metrics in dep_state.values() 
                      if 'error' not in metrics)
    print(f"Current Total: {total_tokens:,} tokens")
    print(f"Target Budget: 130,000 tokens")
    print(f"Reduction Needed: {max(0, total_tokens - 130000):,} tokens")
    print()
    
    # Surgical plan
    print("⚕️  SURGICAL PLAN")
    print("-" * 20)
    print("Target files to extract:")
    print("  - pipeline.py (~20K tokens)")
    print("  - routes.py (~20K tokens)")
    print("  - plugin_system.py (~8K tokens)")
    print("  - logging_utils.py (~5K tokens)")
    print("  - database.py (~3K tokens)")
    print()
    print("Conservative approach:")
    print("  - Detect order dependencies")
    print("  - Keep global context clusters together")
    print("  - Only extract safe, standalone blocks")
    print("  - Zero disaster tolerance")
    print()
    
    # Create JSON report for programmatic use
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'git_status': git_status,
        'file_metrics': server_metrics,
        'ast_analysis': ast_results,
        'dependency_state': dep_state,
        'total_tokens': total_tokens,
        'target_budget': 130000,
        'reduction_needed': max(0, total_tokens - 130000)
    }
    
    with open('helpers/code_surgery/pre_surgery_state.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print("💾 STATE CAPTURED")
    print("-" * 20)
    print("JSON report saved to: helpers/code_surgery/pre_surgery_state.json")
    print()
    
    return report_data

if __name__ == "__main__":
    create_state_report()
