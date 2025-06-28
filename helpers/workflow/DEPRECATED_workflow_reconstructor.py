# DEPRECATED: workflow_reconstructor.py
# =====================================
# 
# This file has been REPLACED by workflow_reconstructor_ast.py
# 
# DEPRECATION DATE: 2025-01-15
# REPLACEMENT: workflow_reconstructor_ast.py
# 
# REASON FOR DEPRECATION:
# The original string-based approach suffered from:
# - Indentation errors and syntax fragility
# - Complex string manipulation that was error-prone
# - Inability to handle complex Python syntax correctly
# - Manual intervention required for route registrations
# 
# SUPERIOR REPLACEMENT:
# workflow_reconstructor_ast.py provides:
# ✅ AST-based manipulation for syntactically perfect code generation
# ✅ Intelligent pattern matching for automatic custom route detection
# ✅ Deterministic, reproducible workflow reconstruction
# ✅ Zero manual intervention required
# ✅ Complete automation without AI dependency
# 
# MIGRATION GUIDE:
# Old command:
#   python workflow_reconstructor.py --template trifecta --existing 110_parameter_buster.py --suffix 2
# 
# New command:
#   python workflow_reconstructor_ast.py --template 400_botify_trifecta --source 110_parameter_buster --suffix 2
# 
# See: WORKFLOW_RECONSTRUCTION_GUIDE.md for complete documentation
# 
# This file will be permanently removed in a future cleanup.

# The original file content has been preserved in git history.
# To access the old implementation, use: git show HEAD~20:helpers/workflow/workflow_reconstructor.py 