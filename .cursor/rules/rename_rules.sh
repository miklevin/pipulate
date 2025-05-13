#!/bin/bash

# Function to rename files in a directory
rename_files() {
    local dir=$1
    local prefix=$2
    cd "$dir" || exit
    
    # Rename files to use underscores and remove prefix
    for file in "$prefix"*.mdc; do
        if [ -f "$file" ]; then
            # Convert hyphens to underscores and remove prefix
            new_name=$(echo "$file" | sed "s/$prefix-//" | tr '-' '_')
            mv "$file" "$new_name"
        fi
    done
    
    cd - > /dev/null
}

# Rename files in each directory
rename_files "architecture" "architecture"
rename_files "implementation" "implementation"
rename_files "integration" "integration"
rename_files "patterns" "pattern"
rename_files "philosophy" "philosophy"

# Special case for selenium-automation.mdc in patterns
cd patterns && mv selenium-automation.mdc selenium_automation.mdc && cd -

# Special case for workflow-patterns.mdc in patterns
cd patterns && mv workflow-patterns.mdc workflow_patterns.mdc && cd -

# Special case for llm-context-sync.mdc in integration
cd integration && mv llm-context-sync.mdc llm_context_sync.mdc && cd - 