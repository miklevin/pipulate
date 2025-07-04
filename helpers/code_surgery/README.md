# Code Surgery Tools - Surgical Python Refactoring

**Master chef tools for deterministic, idempotent code block rearrangement with military precision.**

These tools treat Python files as collections of atomic code blocks that can be safely moved without causing indentation nightmares. Perfect for breaking up monolithic files like `server.py` into smaller, focused modules.

## 🔬 The Philosophy

- **Atomic Code Blocks**: Only slice at fully outdented (top-level) boundaries
- **Deterministic Operations**: Same input always produces same output
- **Idempotent Safety**: Can run multiple times without damage
- **Git Checkpoints**: Full rollback capability via git
- **Namespace Intelligence**: Automatic import management
- **Self-Assembling Names**: Temporary files named so they could reassemble themselves

## 🧰 Tool Suite

### 1. `ast_analyzer.py` - Surgical Code Block Identification
- Uses AST parsing for precise boundary detection
- Identifies atomic code blocks (functions, classes, imports)
- Tracks dependencies and exports
- Validates slice safety

### 2. `code_slicer.py` - Master Orchestrator
- Creates refactoring plans with git checkpoints
- Manages temporary workspace (`/tmp/code_surgery`)
- Executes slice and reassemble operations
- Provides rollback capability

### 3. `dependency_tracker.py` - Import Namespace Management
- Tracks import dependencies across files
- Detects circular dependencies
- Calculates required imports for moved blocks
- Generates import update maps

### 4. `server_refactor_demo.py` - Practical Demonstration
- Shows how to refactor `server.py` into focused files
- Categorizes code blocks intelligently
- Creates comprehensive refactoring plans

## 🚀 Quick Start

### Step 1: Analyze Your File
```bash
python ast_analyzer.py server.py
```

This shows you all the atomic code blocks and their safe slice boundaries.

### Step 2: Create a Refactoring Plan
```bash
python server_refactor_demo.py
```

This analyzes `server.py` and creates a complete refactoring plan to split it into:
- `pipeline.py` - Pipulate class and workflow coordination
- `routes.py` - HTTP endpoint handlers  
- `plugin_system.py` - Plugin discovery and management
- `logging_utils.py` - Logging and display utilities
- `database.py` - Database operations

### Step 3: Execute the Plan
```bash
python code_slicer.py execute /tmp/code_surgery/plans/refactor_server_*.json
```

This performs the actual refactoring with full git safety.

### Step 4: Rollback if Needed
```bash
python code_slicer.py rollback /tmp/code_surgery/plans/refactor_server_*.json
```

This restores everything to the exact state before refactoring.

## 🛡️ Safety Features

### Git Checkpoints
- Automatic git commit before any changes
- Rollback to exact state if anything goes wrong
- Named checkpoints for easy identification

### Temporary Workspace
- All operations use `/tmp/code_surgery` workspace
- Self-assembling file names: `blocktype_filename_name_startline.py`
- No ambiguity in reassembly

### Validation
- AST parsing ensures syntactic correctness
- Dependency analysis prevents import errors
- Circular dependency detection
- Dry-run mode for safety

### Idempotency
- Same operation can be run multiple times safely
- Deterministic block IDs prevent conflicts
- Smart detection of already-completed operations

## 📁 Example: server.py Refactoring

**Before**: `server.py` (73,771 tokens - monolithic)

**After**: Focused files totaling ~129K tokens:
- `server.py` (~17K) - Core app setup
- `pipeline.py` (~20K) - Workflow coordination  
- `routes.py` (~20K) - HTTP endpoints
- `plugin_system.py` (~8K) - Plugin management
- `logging_utils.py` (~5K) - Logging utilities
- `database.py` (~3K) - Database operations
- `mcp_tools.py` (~52K) - AI assistant interface (existing)
- `common.py` (~4K) - CRUD base class (existing)

Perfect for your 130K token budget!

## 🔧 Advanced Usage

### Custom Refactoring Plans
```python
from code_slicer import CodeSlicer

slicer = CodeSlicer()
plan = slicer.create_refactoring_plan(
    source_file="large_file.py",
    target_files=["module1.py", "module2.py"],
    block_mapping={
        "function_my_func_0042": "module1.py",
        "class_MyClass_0123": "module2.py"
    }
)
```

### Dependency Analysis
```python
from dependency_tracker import DependencyTracker

tracker = DependencyTracker()
analyses = tracker.analyze_project(["file1.py", "file2.py"])
cycles = tracker.detect_circular_dependencies()
```

### Safe Boundary Validation
```python
from ast_analyzer import ASTAnalyzer

analyzer = ASTAnalyzer()
boundaries = analyzer.get_slice_boundaries("myfile.py")
is_safe = analyzer.validate_slice_safety("myfile.py", 42, 67)
```

## 🚨 Best Practices

1. **Always commit your work first** - The tools create git checkpoints, but start clean
2. **Test in a branch** - Create a feature branch before major refactoring
3. **Validate plans** - Always run the validation before executing
4. **Use dry-run mode** - Test your plans with `--dry-run` first
5. **Keep backups** - The tools create backups, but external backups are wise
6. **Test after refactoring** - Run your tests to ensure everything works

## 🐛 Troubleshooting

### "Syntax error in file"
- Check that your Python file is syntactically correct
- Ensure consistent indentation (spaces vs tabs)

### "Circular dependencies detected"
- Review the dependency graph output
- Consider restructuring imports to break cycles

### "Block not found"
- Re-run the analyzer to get current block IDs
- Block IDs change if the file is modified

### "Git operation failed"
- Ensure you're in a git repository
- Check that git is properly configured
- Commit or stash any uncommitted changes

## 📊 Token Management

The tools help manage token budgets for AI context:

```bash
# See token counts for each block
python ast_analyzer.py server.py | grep tokens

# Plan refactoring to hit target token count
python server_refactor_demo.py  # Targets 130K tokens
```

## 🎯 Use Cases

- **Breaking up monolithic files** (like your server.py problem)
- **Extracting utility modules** from large codebases
- **Reorganizing code by domain** (routes, models, utils)
- **Preparing code for AI analysis** (token budget management)
- **Modular architecture migrations** 

## 🤝 Contributing

The tools are designed to be extended:
- Add new block categorization rules in `ServerRefactorPlanner`
- Extend import analysis in `DependencyTracker`
- Add new validation rules in the safety checks

Remember: **Measure twice, cut once.** These tools give you the precision of a master chef, but like any sharp knife, use them with respect and preparation. 