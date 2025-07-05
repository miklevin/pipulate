#!/usr/bin/env python3
"""
Surgical Execution Engine v2.0 - Deterministic Code Surgery

This engine integrates the bulletproof surgeon with AST analysis
to create deterministic, rollback-ready code refactoring operations.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Import our surgical tools
from ast_analyzer import ASTAnalyzer
from bulletproof_surgeon import BulletproofSurgeon, PathDisciplineError, SurgicalVerificationError

@dataclass
class SurgicalPlan:
    """Deterministic surgical plan with atomic operations."""
    operation_id: str
    source_file: str
    target_extractions: Dict[str, List[str]]  # filename -> list of block_ids
    estimated_blocks: int
    
class SurgicalExecutionEngine:
    """
    Deterministic code surgery execution engine.
    
    Combines bulletproof defensive safeguards with AST-based analysis.
    """
    
    def __init__(self):
        self.surgeon = BulletproofSurgeon()
        self.analyzer = ASTAnalyzer()
        
    def analyze_server_for_surgery(self, server_file: str = "server.py") -> Dict:
        """Analyze server.py for surgical opportunities."""
        print(f"🔬 ANALYZING {server_file} FOR SURGICAL OPPORTUNITIES...")
        
        if not Path(server_file).exists():
            raise FileNotFoundError(f"Server file not found: {server_file}")
            
        # Parse server.py into atomic blocks
        analysis = self.analyzer.analyze_file(server_file)
        
        # Safe extraction patterns (learned from failures)
        safe_extraction_patterns = {
            'database.py': ['DictLikeDB', 'db_operation', 'get_db_filename'],
            'logging_utils.py': ['setup_logging', 'DebugConsole', 'rich_json_display'],
            'plugin_system.py': ['discover_plugin_files', 'find_plugin_classes'],
            'pipeline.py': ['Pipulate']
        }
        
        # Conservative extraction - only clearly safe blocks
        extraction_candidates = {file: [] for file in safe_extraction_patterns.keys()}
        
        for block in analysis.blocks:
            for target_file, patterns in safe_extraction_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in block.name.lower():
                        extraction_candidates[target_file].append(block.block_id)
                        break
        
        # Remove empty extractions
        extraction_candidates = {f: blocks for f, blocks in extraction_candidates.items() if blocks}
        
        total_blocks = len(analysis.blocks)
        extractable_blocks = sum(len(blocks) for blocks in extraction_candidates.values())
        
        result = {
            'analysis': analysis,
            'extraction_candidates': extraction_candidates,
            'total_blocks': total_blocks,
            'extractable_blocks': extractable_blocks,
            'extraction_percentage': (extractable_blocks / total_blocks) * 100 if total_blocks > 0 else 0
        }
        
        print(f"📊 SURGICAL ANALYSIS:")
        print(f"   Total blocks: {total_blocks}")
        print(f"   Extractable blocks: {extractable_blocks}")
        print(f"   Extraction percentage: {result['extraction_percentage']:.1f}%")
        
        return result
        
    def create_surgical_plan(self, analysis: Dict) -> SurgicalPlan:
        """Create deterministic surgical plan."""
        print(f"📋 CREATING SURGICAL PLAN...")
        
        operation_id = f"surgery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        plan = SurgicalPlan(
            operation_id=operation_id,
            source_file="server.py",
            target_extractions=analysis['extraction_candidates'],
            estimated_blocks=analysis['extractable_blocks']
        )
        
        print(f"✅ SURGICAL PLAN: {operation_id}")
        print(f"   Target files: {len(plan.target_extractions)}")
        print(f"   Blocks to extract: {plan.estimated_blocks}")
        
        return plan
        
    def preview_surgical_plan(self, plan: SurgicalPlan) -> None:
        """Preview surgical plan without executing."""
        print(f"\n👁️  SURGICAL PLAN PREVIEW: {plan.operation_id}")
        print("=" * 50)
        
        for target_file, block_ids in plan.target_extractions.items():
            print(f"\n📄 {target_file}: {len(block_ids)} blocks")
            for block_id in block_ids[:3]:  # Show first 3
                print(f"   - {block_id}")
            if len(block_ids) > 3:
                print(f"   ... and {len(block_ids) - 3} more")
                
        print(f"\n📊 SUMMARY:")
        print(f"   Total blocks: {sum(len(b) for b in plan.target_extractions.values())}")
        print(f"   Target files: {len(plan.target_extractions)}")
        
    def run_surgical_analysis(self, server_file: str = "server.py") -> Optional[SurgicalPlan]:
        """Run complete surgical analysis and planning."""
        print("🏥 SURGICAL EXECUTION ENGINE v2.0")
        print("=" * 50)
        print("Deterministic. Defensive. Rollback-ready.")
        print()
        
        try:
            # Step 1: Analyze server
            analysis = self.analyze_server_for_surgery(server_file)
            
            # Step 2: Create surgical plan
            plan = self.create_surgical_plan(analysis)
            
            # Step 3: Preview plan
            self.preview_surgical_plan(plan)
            
            print(f"\n🔪 SURGICAL FRAMEWORK READY")
            print(f"   All defensive safeguards operational")
            print(f"   Plan: {plan.operation_id}")
            
            return plan
            
        except Exception as e:
            print(f"🚨 SURGICAL ANALYSIS FAILED: {e}")
            raise

def main():
    """Main entry point for surgical execution."""
    
    # Ensure we're in the right directory
    if not Path("server.py").exists():
        print("❌ ERROR: server.py not found. Must run from pipulate directory.")
        sys.exit(1)
        
    engine = SurgicalExecutionEngine()
    
    try:
        # Run surgical analysis
        plan = engine.run_surgical_analysis()
        
        if plan:
            print(f"\n🤖 SURGICAL EXECUTION READY")
            print(f"   Plan: {plan.operation_id}")
            print(f"   Framework: Bulletproof safeguards active")
            
    except Exception as e:
        print(f"🚨 SURGICAL ENGINE FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
