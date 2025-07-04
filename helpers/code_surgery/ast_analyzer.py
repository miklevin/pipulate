#!/usr/bin/env python3
"""
AST Analyzer - Surgical Code Block Identification

This module provides precise identification of atomic code blocks in Python files
using AST parsing. It identifies slice boundaries that respect Python's structure
and won't cause indentation nightmares.

Key principles:
- Only slice at fully outdented (top-level) boundaries
- Preserve exact whitespace and comments
- Track dependencies and imports
- Generate deterministic block IDs
"""

import ast
import os
import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class CodeBlock:
    """Represents an atomic code block that can be safely moved."""
    block_id: str
    block_type: str  # 'import', 'class', 'function', 'assignment', 'other'
    name: str  # Function/class name or description
    start_line: int
    end_line: int
    source_code: str
    imports_needed: Set[str] = field(default_factory=set)
    exports_symbols: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    
    def __post_init__(self):
        """Generate deterministic block ID if not provided."""
        if not self.block_id:
            # Create deterministic ID: type_name_startline
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', self.name.lower())
            self.block_id = f"{self.block_type}_{safe_name}_{self.start_line:04d}"

@dataclass
class FileAnalysis:
    """Complete analysis of a Python file."""
    file_path: str
    blocks: List[CodeBlock]
    imports: Dict[str, str]  # import_name -> source_module
    exports: Set[str]  # Symbols this file exports
    dependencies: Dict[str, Set[str]]  # block_id -> set of dependencies
    
class ASTAnalyzer:
    """Analyzes Python files to identify atomic code blocks."""
    
    def __init__(self):
        self.current_file = None
        self.source_lines = []
        
    def analyze_file(self, file_path: str) -> FileAnalysis:
        """Analyze a Python file and return atomic code blocks."""
        self.current_file = file_path
        
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
        self.source_lines = source_code.splitlines()
        
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")
            
        blocks = []
        imports = {}
        exports = set()
        
        # Analyze top-level nodes only (atomic boundaries)
        for node in tree.body:
            block = self._analyze_node(node)
            if block:
                blocks.append(block)
                
                # Track imports and exports
                if block.block_type == 'import':
                    imports.update(self._extract_imports(node))
                elif block.block_type in ('class', 'function', 'assignment'):
                    exports.add(block.name)
        
        # Build dependency graph
        dependencies = self._build_dependencies(blocks)
        
        return FileAnalysis(
            file_path=file_path,
            blocks=blocks,
            imports=imports,
            exports=exports,
            dependencies=dependencies
        )
    
    def _analyze_node(self, node: ast.AST) -> Optional[CodeBlock]:
        """Analyze a single AST node and create a CodeBlock if appropriate."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        # Get the exact source code for this block
        source_code = self._extract_source_lines(start_line, end_line)
        
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return CodeBlock(
                block_id="",  # Will be generated
                block_type="import",
                name=self._get_import_name(node),
                start_line=start_line,
                end_line=end_line,
                source_code=source_code,
                exports_symbols=set(self._extract_imports(node).keys())
            )
            
        elif isinstance(node, ast.ClassDef):
            decorators = [self._get_decorator_name(d) for d in node.decorator_list]
            docstring = ast.get_docstring(node)
            
            return CodeBlock(
                block_id="",
                block_type="class",
                name=node.name,
                start_line=start_line,
                end_line=end_line,
                source_code=source_code,
                decorators=decorators,
                docstring=docstring,
                exports_symbols={node.name}
            )
            
        elif isinstance(node, ast.FunctionDef):
            decorators = [self._get_decorator_name(d) for d in node.decorator_list]
            docstring = ast.get_docstring(node)
            
            return CodeBlock(
                block_id="",
                block_type="function",
                name=node.name,
                start_line=start_line,
                end_line=end_line,
                source_code=source_code,
                decorators=decorators,
                docstring=docstring,
                exports_symbols={node.name}
            )
            
        elif isinstance(node, ast.Assign):
            # Handle top-level assignments (constants, etc.)
            targets = []
            for target in node.targets:
                if isinstance(target, ast.Name):
                    targets.append(target.id)
                    
            if targets:
                name = ", ".join(targets)
                return CodeBlock(
                    block_id="",
                    block_type="assignment",
                    name=name,
                    start_line=start_line,
                    end_line=end_line,
                    source_code=source_code,
                    exports_symbols=set(targets)
                )
        
        else:
            # Other top-level code (if statements, etc.)
            return CodeBlock(
                block_id="",
                block_type="other",
                name=f"other_{start_line}",
                start_line=start_line,
                end_line=end_line,
                source_code=source_code
            )
    
    def _extract_source_lines(self, start_line: int, end_line: int) -> str:
        """Extract exact source code lines including proper whitespace."""
        # AST uses 1-based line numbers
        lines = self.source_lines[start_line-1:end_line]
        return '\n'.join(lines)
    
    def _get_import_name(self, node: ast.AST) -> str:
        """Get descriptive name for import statement."""
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            return f"import_{names[0].replace('.', '_')}"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or "relative"
            names = [alias.name for alias in node.names]
            return f"from_{module.replace('.', '_')}_import_{names[0]}"
        return "unknown_import"
    
    def _extract_imports(self, node: ast.AST) -> Dict[str, str]:
        """Extract import mapping from import node."""
        imports = {}
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = alias.name
                
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = f"{module}.{alias.name}" if module else alias.name
                
        return imports
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get string representation of decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return f"{decorator.func.value.id}.{decorator.func.attr}"
        return "unknown_decorator"
    
    def _build_dependencies(self, blocks: List[CodeBlock]) -> Dict[str, Set[str]]:
        """Build dependency graph between blocks."""
        dependencies = {}
        
        # Create symbol table
        symbol_to_block = {}
        for block in blocks:
            for symbol in block.exports_symbols:
                symbol_to_block[symbol] = block.block_id
        
        # Analyze dependencies for each block
        for block in blocks:
            block_deps = set()
            
            # Parse the block's source code to find references
            try:
                tree = ast.parse(block.source_code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        if node.id in symbol_to_block:
                            dep_block_id = symbol_to_block[node.id]
                            if dep_block_id != block.block_id:
                                block_deps.add(dep_block_id)
            except:
                # If parsing fails, assume no dependencies
                pass
            
            dependencies[block.block_id] = block_deps
        
        return dependencies
    
    def get_slice_boundaries(self, file_path: str) -> List[Tuple[int, int]]:
        """Get safe slice boundaries for a file (start_line, end_line pairs)."""
        analysis = self.analyze_file(file_path)
        boundaries = []
        
        for block in analysis.blocks:
            boundaries.append((block.start_line, block.end_line))
        
        return sorted(boundaries)
    
    def validate_slice_safety(self, file_path: str, start_line: int, end_line: int) -> bool:
        """Validate that a slice is safe (won't break indentation)."""
        boundaries = self.get_slice_boundaries(file_path)
        
        for boundary_start, boundary_end in boundaries:
            # Check if the slice aligns with block boundaries
            if start_line == boundary_start and end_line == boundary_end:
                return True
                
        return False

def main():
    """Test the AST analyzer."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python ast_analyzer.py <python_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    analyzer = ASTAnalyzer()
    
    try:
        analysis = analyzer.analyze_file(file_path)
        
        print(f"Analysis of {file_path}:")
        print(f"  Blocks found: {len(analysis.blocks)}")
        print(f"  Imports: {len(analysis.imports)}")
        print(f"  Exports: {len(analysis.exports)}")
        
        print("\nBlocks:")
        for block in analysis.blocks:
            print(f"  {block.block_id}: {block.block_type} '{block.name}' (lines {block.start_line}-{block.end_line})")
            if block.dependencies:
                print(f"    Dependencies: {block.dependencies}")
        
        print("\nSafe slice boundaries:")
        boundaries = analyzer.get_slice_boundaries(file_path)
        for start, end in boundaries:
            print(f"  Lines {start}-{end}")
            
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 