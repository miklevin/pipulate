#!/bin/bash

# ==============================================================================
# Trifecta Derivatives Reconstruction Script
# ==============================================================================
# 
# 🏗️ WET INHERITANCE MASTERY: OOP philosophy with WET explicitness
# ═══════════════════════════════════════════════════════════════════════════════════
# BREAKTHROUGH: Deterministic template inheritance for Pipulate workflows
# PHILOSOPHY: WET (Write Everything Twice) for radical transparency + AI collaboration
# METHOD: AST-based surgical code manipulation for bulletproof reliability
# 
# REVOLUTIONARY CAPABILITY:
# • Update Botify Trifecta template → Automatic reconstruction of derivatives
# • Zero manual synchronization → Complete automation via surgical AST manipulation
# • Self-contained plugins with no runtime dependencies
# 
# This script deterministically rebuilds Parameter Buster and Link Graph 
# Visualizer plugins from the Botify Trifecta template using AST-based 
# workflow reconstruction.
#
# USAGE:
#   ./rebuild_trifecta_derivatives.sh [--dry-run] [--verbose] [--target plugin_name]
#
# OPTIONS:
#   --dry-run        Show what would be done without actually doing it
#   --verbose        Show detailed progress and debug information
#   --target NAME    Only rebuild specific plugin (parameter_buster|link_graph)
#   --help           Show this help message
#
# CRITICAL CONFIGURATION DIFFERENCES:
#   Parameter Buster: TEMPLATE_CONFIG analysis = 'Not Compliant'
#   Link Graph:       TEMPLATE_CONFIG analysis = 'Link Graph Edges'
#
# ==============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPERS_DIR="$SCRIPT_DIR/helpers"
WORKFLOW_DIR="$HELPERS_DIR/workflow"
PLUGINS_DIR="$SCRIPT_DIR/plugins"
RECONSTRUCTOR="$WORKFLOW_DIR/workflow_reconstructor.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default options
DRY_RUN=false
VERBOSE=false
TARGET=""

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
}

print_step() {
    echo -e "${BLUE}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${CYAN}ℹ️  $1${NC}"
    fi
}

show_help() {
    cat << EOF
Trifecta Derivatives Reconstruction Script

This script deterministically rebuilds Parameter Buster and Link Graph 
Visualizer plugins from the Botify Trifecta template using AST-based 
workflow reconstruction.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --dry-run        Show what would be done without actually doing it
    --verbose        Show detailed progress and debug information  
    --target NAME    Only rebuild specific plugin (parameter_buster|link_graph)
    --help           Show this help message

EXAMPLES:
    $0                                    # Rebuild both plugins
    $0 --target parameter_buster          # Rebuild only Parameter Buster
    $0 --dry-run --verbose               # Show what would be done with details
    $0 --target link_graph --verbose     # Rebuild Link Graph with verbose output

CRITICAL CONFIGURATION DIFFERENCES:
    Parameter Buster: TEMPLATE_CONFIG analysis = 'Not Compliant'
    Link Graph:       TEMPLATE_CONFIG analysis = 'Link Graph Edges'

The script uses helpers/workflow/workflow_reconstructor.py to perform AST-based
code transplantation, preserving workflow-specific methods while applying the
correct template configurations.
EOF
}

# ==============================================================================
# Validation Functions
# ==============================================================================

validate_environment() {
    print_step "Validating environment..."
    
    # Check if we're in the correct directory
    if [[ ! -f "$SCRIPT_DIR/server.py" ]]; then
        print_error "Must be run from pipulate root directory (where server.py exists)"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check if workflow_reconstructor.py exists
    if [[ ! -f "$RECONSTRUCTOR" ]]; then
        print_error "workflow_reconstructor.py not found at: $RECONSTRUCTOR"
        exit 1
    fi
    
    # Check if backup files exist
    if [[ ! -f "$PLUGINS_DIR/xx_parameter_buster.py" ]]; then
        print_error "Backup file not found: $PLUGINS_DIR/xx_parameter_buster.py"
        exit 1
    fi
    
    if [[ ! -f "$PLUGINS_DIR/xx_link_graph.py" ]]; then
        print_error "Backup file not found: $PLUGINS_DIR/xx_link_graph.py"
        exit 1
    fi
    
    # Check if template exists
    if [[ ! -f "$PLUGINS_DIR/400_botify_trifecta.py" ]]; then
        print_error "Template not found: $PLUGINS_DIR/400_botify_trifecta.py"
        exit 1
    fi
    
    print_success "Environment validation passed"
}

# ==============================================================================
# Plugin Configuration
# ==============================================================================

declare -A PLUGIN_CONFIG

# Parameter Buster Configuration
PLUGIN_CONFIG[parameter_buster_template]="400_botify_trifecta"
PLUGIN_CONFIG[parameter_buster_source]="xx_parameter_buster"
PLUGIN_CONFIG[parameter_buster_target]="110_parameter_buster"
PLUGIN_CONFIG[parameter_buster_class]="ParameterBuster"
PLUGIN_CONFIG[parameter_buster_app_name]="parameterbuster"
PLUGIN_CONFIG[parameter_buster_display_name]="Parameter Buster 🔨"
PLUGIN_CONFIG[parameter_buster_template_config]='{"analysis": "Not Compliant", "crawler": "Crawl Basic", "gsc": "GSC Performance"}'
PLUGIN_CONFIG[parameter_buster_roles]="['Botify Employee']"

# Link Graph Configuration  
PLUGIN_CONFIG[link_graph_template]="400_botify_trifecta"
PLUGIN_CONFIG[link_graph_source]="xx_link_graph"
PLUGIN_CONFIG[link_graph_target]="120_link_graph"
PLUGIN_CONFIG[link_graph_class]="LinkGraphVisualizer"
PLUGIN_CONFIG[link_graph_app_name]="link_graph_visualizer"
PLUGIN_CONFIG[link_graph_display_name]="Link Graph Visualizer 🌐"
PLUGIN_CONFIG[link_graph_template_config]='{"analysis": "Link Graph Edges", "crawler": "Crawl Basic", "gsc": "GSC Performance"}'
PLUGIN_CONFIG[link_graph_roles]="['Botify Employee']"

# ==============================================================================
# Reconstruction Functions
# ==============================================================================

reconstruct_plugin() {
    local plugin_name="$1"
    local template="${PLUGIN_CONFIG[${plugin_name}_template]}"
    local source="${PLUGIN_CONFIG[${plugin_name}_source]}"
    local target="${PLUGIN_CONFIG[${plugin_name}_target]}"
    local class_name="${PLUGIN_CONFIG[${plugin_name}_class]}"
    
    print_step "Reconstructing $plugin_name..."
    print_info "Template: $template"
    print_info "Source: $source"
    print_info "Target: $target"
    print_info "Class: $class_name"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: Would execute reconstruction command"
        return 0
    fi
    
    # Create backup of current target if it exists
    if [[ -f "$PLUGINS_DIR/${target}.py" ]]; then
        local backup_file="$PLUGINS_DIR/${target}.py.backup.$(date +%Y%m%d_%H%M%S)"
        print_info "Creating backup: $backup_file"
        cp "$PLUGINS_DIR/${target}.py" "$backup_file"
    fi
    
    # Execute reconstruction
    local cmd=(.venv/bin/python "$RECONSTRUCTOR" 
        --template "$template"
        --source "$source" 
        --target "$target"
        --new-class-name "$class_name")
    
    print_info "Executing: ${cmd[*]}"
    
    if "${cmd[@]}"; then
        print_success "$plugin_name reconstruction completed"
        return 0
    else
        print_error "$plugin_name reconstruction failed"
        return 1
    fi
}

apply_template_config() {
    local plugin_name="$1"
    local target="${PLUGIN_CONFIG[${plugin_name}_target]}"
    local template_config="${PLUGIN_CONFIG[${plugin_name}_template_config]}"
    local target_file="$PLUGINS_DIR/${target}.py"
    local updater_script="$HELPERS_DIR/workflow/update_template_config.py"
    
    print_step "Applying template configuration for $plugin_name..."
    print_info "Target file: $target_file"
    print_info "Template config: $template_config"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: Would apply template configuration"
        return 0
    fi
    
    # Use the dedicated Python script to update TEMPLATE_CONFIG
    if .venv/bin/python "$updater_script" "$target_file" "$template_config"; then
        print_success "Template configuration applied for $plugin_name"
        return 0
    else
        print_error "Failed to apply template configuration for $plugin_name"
        return 1
    fi
}

apply_roles() {
    local plugin_name="$1"
    local target="${PLUGIN_CONFIG[${plugin_name}_target]}"
    local roles="${PLUGIN_CONFIG[${plugin_name}_roles]}"
    local target_file="$PLUGINS_DIR/${target}.py"
    
    print_step "Applying roles configuration for $plugin_name..."
    print_info "Target file: $target_file"
    print_info "Roles: $roles"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: Would apply roles configuration"
        return 0
    fi
    
    # Use sed to update the ROLES line
    if sed -i "s/^ROLES = \[.*\]$/ROLES = $roles/" "$target_file"; then
        print_success "Roles configuration applied for $plugin_name"
        return 0
    else
        print_error "Failed to apply roles configuration for $plugin_name"
        return 1
    fi
}

validate_reconstruction() {
    local plugin_name="$1"
    local target="${PLUGIN_CONFIG[${plugin_name}_target]}"
    local target_file="$PLUGINS_DIR/${target}.py"
    
    print_step "Validating reconstruction for $plugin_name..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN: Would validate reconstruction"
        return 0
    fi
    
    # Check if file exists
    if [[ ! -f "$target_file" ]]; then
        print_error "Target file not found: $target_file"
        return 1
    fi
    
    # Check if file is valid Python
    if ! .venv/bin/python -m py_compile "$target_file" 2>/dev/null; then
        print_error "Target file has syntax errors: $target_file"
        return 1
    fi
    
    # Check if key attributes are present
    local required_attrs=("APP_NAME" "DISPLAY_NAME" "TEMPLATE_CONFIG" "ROLES")
    for attr in "${required_attrs[@]}"; do
        if ! grep -q "^[[:space:]]*${attr}[[:space:]]*=" "$target_file"; then
            print_error "Missing required attribute: $attr in $target_file"
            return 1
        fi
    done
    
    print_success "Validation passed for $plugin_name"
    return 0
}

# ==============================================================================
# Main Execution Functions
# ==============================================================================

reconstruct_all_plugins() {
    local plugins_to_build=()
    
    if [[ -z "$TARGET" ]]; then
        plugins_to_build=("parameter_buster" "link_graph")
    else
        case "$TARGET" in
            "parameter_buster"|"link_graph")
                plugins_to_build=("$TARGET")
                ;;
            *)
                print_error "Invalid target: $TARGET. Must be 'parameter_buster' or 'link_graph'"
                exit 1
                ;;
        esac
    fi
    
    print_header "Reconstructing Trifecta Derivatives"
    
    local success_count=0
    local total_count=${#plugins_to_build[@]}
    
    for plugin in "${plugins_to_build[@]}"; do
        print_header "Processing $plugin"
        
        if reconstruct_plugin "$plugin" && 
           apply_template_config "$plugin" && 
           apply_roles "$plugin" && 
           validate_reconstruction "$plugin"; then
            ((success_count++))
        else
            print_error "Failed to process $plugin"
        fi
        
        echo ""
    done
    
    # Summary
    print_header "Reconstruction Summary"
    print_info "Successfully processed: $success_count/$total_count plugins"
    
    if [[ $success_count -eq $total_count ]]; then
        print_success "All plugins reconstructed successfully!"
        return 0
    else
        print_error "Some plugins failed to reconstruct"
        return 1
    fi
}

# ==============================================================================
# Main Script
# ==============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --target)
                TARGET="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Show configuration
    if [[ "$VERBOSE" == true ]]; then
        print_header "Configuration"
        print_info "Script directory: $SCRIPT_DIR"
        print_info "Plugins directory: $PLUGINS_DIR"
        print_info "Reconstructor: $RECONSTRUCTOR"
        print_info "Dry run: $DRY_RUN"
        print_info "Target: ${TARGET:-all}"
        echo ""
    fi
    
    # Validate environment
    validate_environment
    
    # Execute reconstruction
    if reconstruct_all_plugins; then
        print_success "Reconstruction completed successfully!"
        exit 0
    else
        print_error "Reconstruction failed!"
        exit 1
    fi
}

# Execute main function
main "$@" 