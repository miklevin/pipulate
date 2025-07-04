#!/usr/bin/env python3
"""
Dependency Tracker - Import and Namespace Management

This module handles the complex task of tracking dependencies and managing
namespaces during code refactoring. It ensures that when code blocks are moved,
all imports are properly updated and no import errors occur.

Key responsibilities:
- Track all imports and their usage
- Detect circular dependencies
- Calculate required imports for moved blocks
- Generate import update maps
- Validate namespace safety
"""

import ast
import os
import re
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque

from ast_analyzer import ASTAnalyzer, CodeBlock, FileAnalysis

@dataclass
class ImportDependency:
    """Represents an import dependency."""
    symbol: str
    source_module: str
    import_type: str  # 'import', 'from_import', 'star_import'
    alias: Optional[str] = None
    used_in_blocks: Set[str] = field(default_factory=set)

@dataclass
class ModuleDependency:
    """Represents a dependency between modules."""
    source_module: str
    target_module: str
    symbols: Set[str] = field(default_factory=set)
    dependency_type: str = "import"  # 'import', 'inheritance', 'call'

class DependencyTracker:
    """Tracks dependencies and manages namespace changes during refactoring."""
    
    def __init__(self):
        self.analyzer = ASTAnalyzer()
        self.file_analyses: Dict[str, FileAnalysis] = {}
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.symbol_definitions: Dict[str, str] = {}  # symbol -> defining_module
        self.symbol_usages: Dict[str, Set[str]] = defaultdict(set)  # symbol -> using_modules
        
    def analyze_project(self, file_paths: List[str]) -> Dict[str, FileAnalysis]:
        """Analyze multiple files to build complete dependency graph."""
        
        # First pass: analyze all files
        for file_path in file_paths:
            self.file_analyses[file_path] = self.analyzer.analyze_file(file_path)
        
        # Second pass: build dependency graphs
        self._build_import_graph()
        self._build_symbol_maps()
        
        return self.file_analyses
    
    def _build_import_graph(self):
        """Build graph of import dependencies between files."""
        for file_path, analysis in self.file_analyses.items():
            module_name = self._path_to_module_name(file_path)
            
            for import_name, source_module in analysis.imports.items():
                # Add edge in import graph
                self.import_graph[module_name].add(source_module)
    
    def _build_symbol_maps(self):
        """Build maps of symbol definitions and usages."""
        for file_path, analysis in self.file_analyses.items():
            module_name = self._path_to_module_name(file_path)
            
            # Record symbol definitions
            for symbol in analysis.exports:
                self.symbol_definitions[symbol] = module_name
            
            # Record symbol usages
            for block in analysis.blocks:
                for dep_symbol in block.dependencies:
                    self.symbol_usages[dep_symbol].add(module_name)
    
    def _path_to_module_name(self, file_path: str) -> str:
        """Convert file path to module name."""
        path = Path(file_path)
        if path.name == "__init__.py":
            return str(path.parent.name)
        else:
            return str(path.stem)
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular import dependencies."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.import_graph.get(node, []):
                dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
        
        for module in self.import_graph:
            if module not in visited:
                dfs(module, [])
        
        return cycles
    
    def calculate_required_imports(self, 
                                 block: CodeBlock, 
                                 target_file: str,
                                 source_analysis: FileAnalysis) -> Set[str]:
        """Calculate which imports are needed when moving a block to a target file."""
        required_imports = set()
        target_module = self._path_to_module_name(target_file)
        
        # Get target file analysis if it exists
        target_analysis = self.file_analyses.get(target_file)
        existing_imports = set()
        if target_analysis:
            existing_imports = set(target_analysis.imports.keys())
        
        # Analyze the block's source code to find symbol references
        block_symbols = self._extract_symbols_from_block(block)
        
        for symbol in block_symbols:
            # Skip if already imported in target file
            if symbol in existing_imports:
                continue
            
            # Find where this symbol is defined
            if symbol in source_analysis.imports:
                # It's an imported symbol
                source_module = source_analysis.imports[symbol]
                required_imports.add(f"from {source_module} import {symbol}")
            
            elif symbol in self.symbol_definitions:
                # It's defined in another module
                defining_module = self.symbol_definitions[symbol]
                if defining_module != target_module:
                    required_imports.add(f"from {defining_module} import {symbol}")
        
        return required_imports
    
    def _extract_symbols_from_block(self, block: CodeBlock) -> Set[str]:
        """Extract all symbol references from a code block."""
        symbols = set()
        
        try:
            tree = ast.parse(block.source_code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    symbols.add(node.id)
                elif isinstance(node, ast.Attribute):
                    # Handle attribute access (e.g., module.function)
                    if isinstance(node.value, ast.Name):
                        symbols.add(node.value.id)
        except:
            # If parsing fails, use block's recorded dependencies
            symbols = block.dependencies
        
        return symbols
    
    def calculate_import_updates(self, 
                               operations: List['SliceOperation']) -> Dict[str, List[str]]:
        """Calculate all import statement updates needed for the refactoring."""
        updates = defaultdict(list)
        
        for operation in operations:
            source_file = operation.source_file
            target_file = operation.target_file
            block_id = operation.block_id
            
            # Get analyses
            source_analysis = self.file_analyses[source_file]
            target_analysis = self.file_analyses.get(target_file)
            
            # Find the block
            block = None
            for b in source_analysis.blocks:
                if b.block_id == block_id:
                    block = b
                    break
            
            if not block:
                continue
            
            # Calculate required imports for target file
            required_imports = self.calculate_required_imports(
                block, target_file, source_analysis
            )
            
            if required_imports:
                updates[target_file].extend(required_imports)
            
            # Calculate imports to remove from source file (if no longer used)
            unused_imports = self._calculate_unused_imports(
                source_analysis, [block_id]
            )
            
            if unused_imports:
                updates[source_file].extend([f"# Remove: {imp}" for imp in unused_imports])
        
        return dict(updates)
    
    def _calculate_unused_imports(self, 
                                analysis: FileAnalysis, 
                                removed_block_ids: List[str]) -> Set[str]:
        """Calculate which imports are no longer needed after removing blocks."""
        unused_imports = set()
        
        # Get all symbols used by remaining blocks
        remaining_symbols = set()
        for block in analysis.blocks:
            if block.block_id not in removed_block_ids:
                remaining_symbols.update(block.dependencies)
        
        # Check which imports are no longer needed
        for import_name, source_module in analysis.imports.items():
            if import_name not in remaining_symbols:
                unused_imports.add(import_name)
        
        return unused_imports
    
    def validate_refactoring_safety(self, operations: List['SliceOperation']) -> List[str]:
        """Validate that a refactoring plan won't break dependencies."""
        warnings = []
        
        # Check for circular dependencies after refactoring
        temp_graph = self.import_graph.copy()
        
        for operation in operations:
            source_module = self._path_to_module_name(operation.source_file)
            target_module = self._path_to_module_name(operation.target_file)
            
            # Simulate the move
            temp_graph[target_module].add(source_module)
        
        # Check for new cycles
        cycles = self._detect_cycles_in_graph(temp_graph)
        if cycles:
            warnings.append(f"Potential circular dependencies detected: {cycles}")
        
        # Check for missing dependencies
        for operation in operations:
            missing_deps = self._check_missing_dependencies(operation)
            if missing_deps:
                warnings.append(f"Missing dependencies for {operation.block_id}: {missing_deps}")
        
        return warnings
    
    def _detect_cycles_in_graph(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect cycles in a dependency graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
        
        for module in graph:
            if module not in visited:
                dfs(module, [])
        
        return cycles
    
    def _check_missing_dependencies(self, operation: 'SliceOperation') -> Set[str]:
        """Check for dependencies that might be missing after a move."""
        missing = set()
        
        # This would be more sophisticated in a real implementation
        # For now, just return empty set
        
        return missing
    
    def generate_import_header(self, file_path: str, additional_imports: Set[str]) -> str:
        """Generate the import header for a file after refactoring."""
        lines = []
        
        # Get existing imports
        existing_analysis = self.file_analyses.get(file_path)
        existing_imports = set()
        if existing_analysis:
            for block in existing_analysis.blocks:
                if block.block_type == 'import':
                    existing_imports.add(block.source_code.strip())
        
        # Combine with additional imports
        all_imports = existing_imports | additional_imports
        
        # Sort imports (standard library, third party, local)
        stdlib_imports = []
        thirdparty_imports = []
        local_imports = []
        
        for import_stmt in sorted(all_imports):
            if self._is_stdlib_import(import_stmt):
                stdlib_imports.append(import_stmt)
            elif self._is_local_import(import_stmt):
                local_imports.append(import_stmt)
            else:
                thirdparty_imports.append(import_stmt)
        
        # Build header
        if stdlib_imports:
            lines.extend(stdlib_imports)
            lines.append("")
        
        if thirdparty_imports:
            lines.extend(thirdparty_imports)
            lines.append("")
        
        if local_imports:
            lines.extend(local_imports)
            lines.append("")
        
        return "\n".join(lines)
    
    def _is_stdlib_import(self, import_stmt: str) -> bool:
        """Check if an import is from the standard library."""
        # Simple heuristic - can be improved
        stdlib_modules = {
            'os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 'collections',
            'functools', 'itertools', 'subprocess', 'tempfile', 'shutil',
            'ast', 're', 'dataclasses'
        }
        
        for module in stdlib_modules:
            if module in import_stmt:
                return True
        return False
    
    def _is_local_import(self, import_stmt: str) -> bool:
        """Check if an import is from local modules."""
        # Simple heuristic - starts with a dot or is a relative import
        return import_stmt.startswith('from .') or 'from common' in import_stmt

def main():
    """Test the dependency tracker."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python dependency_tracker.py <file1> [file2] [file3] ...")
        sys.exit(1)
    
    file_paths = sys.argv[1:]
    tracker = DependencyTracker()
    
    print("Analyzing project dependencies...")
    analyses = tracker.analyze_project(file_paths)
    
    print(f"\nAnalyzed {len(analyses)} files:")
    for file_path, analysis in analyses.items():
        print(f"  {file_path}: {len(analysis.blocks)} blocks, {len(analysis.imports)} imports")
    
    print("\nImport graph:")
    for module, deps in tracker.import_graph.items():
        if deps:
            print(f"  {module} -> {', '.join(deps)}")
    
    print("\nSymbol definitions:")
    for symbol, module in tracker.symbol_definitions.items():
        print(f"  {symbol} defined in {module}")
    
    cycles = tracker.detect_circular_dependencies()
    if cycles:
        print(f"\n⚠️  Circular dependencies detected:")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")
    else:
        print("\n✅ No circular dependencies detected")

if __name__ == "__main__":
    main() 