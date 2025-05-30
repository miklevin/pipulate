#!/usr/bin/env python3
"""
Atomic Transplantation Engine

Performs deterministic code transplantation between workflows using the marker system
created by atomic_transplantation_marker_tool.py. Uses simple .split() and .join()
operations for reliable, token-efficient transplantation.

Usage Examples:
    # Transplant specific section between files
    python helpers/cleanup/atomic_transplantation_engine.py transplant \
        plugins/535_botify_trifecta.py \
        plugins/045_parameter_buster_new.py \
        --section "steps_01_04_botify_data_collection"
    
    # Extract section for inspection
    python helpers/cleanup/atomic_transplantation_engine.py extract \
        plugins/535_botify_trifecta.py \
        --section "steps_01_04_botify_data_collection"
    
    # Validate markers in a file
    python helpers/cleanup/atomic_transplantation_engine.py validate \
        plugins/045_parameter_buster_new.py \
        --section "steps_01_04_botify_data_collection"

Features:
- Deterministic split/join operations (no regex complexity)
- Automatic backup creation before modifications
- Comprehensive validation of marker integrity
- Token-efficient single-operation transplantation
- Detailed logging for transparency
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import shutil
from datetime import datetime


class AtomicTransplantationEngine:
    """Engine for performing atomic code transplantation using marker boundaries."""
    
    def __init__(self, verbose: bool = True, backup: bool = True):
        self.verbose = verbose
        self.backup = backup
    
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(message)
    
    def read_file(self, file_path: str) -> str:
        """Read file content as string."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to read {file_path}: {str(e)}")
    
    def write_file(self, file_path: str, content: str):
        """Write content to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise Exception(f"Failed to write {file_path}: {str(e)}")
    
    def create_backup(self, file_path: str) -> str:
        """Create timestamped backup of file."""
        if not self.backup:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        
        try:
            shutil.copy2(file_path, backup_path)
            self.log(f"📋 Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def get_section_markers(self, section_name: str) -> Tuple[str, str]:
        """Get start and end markers for a section."""
        start_marker = f"# --- START_WORKFLOW_SECTION: {section_name} ---"
        end_marker = f"# --- END_WORKFLOW_SECTION: {section_name} ---"
        return start_marker, end_marker
    
    def extract_atomic_section(self, content: str, section_name: str) -> Tuple[str, bool]:
        """Extract an atomic section from file content.
        
        Returns:
            Tuple[str, bool]: (extracted_section_content, success)
        """
        start_marker, end_marker = self.get_section_markers(section_name)
        
        lines = content.split('\n')
        section_lines = []
        in_section = False
        
        for line in lines:
            if line.strip() == start_marker:
                in_section = True
                section_lines.append(line)
                continue
            elif line.strip() == end_marker:
                if in_section:
                    section_lines.append(line)
                    break
                else:
                    self.log(f"ERROR: Found end marker without corresponding start marker")
                    return "", False
            elif in_section:
                section_lines.append(line)
        
        if not section_lines:
            self.log(f"ERROR: No section found with name '{section_name}'")
            return "", False
        
        if not in_section or lines[-1] != end_marker:
            # Check if we ended properly
            if section_lines and section_lines[-1].strip() != end_marker:
                self.log(f"ERROR: Section '{section_name}' not properly closed")
                return "", False
        
        extracted_content = '\n'.join(section_lines)
        
        # Light-touch dependency analysis
        dependencies = self.analyze_section_dependencies(extracted_content)
        if dependencies:
            self.log(f"📋 DEPENDENCY ANALYSIS for section '{section_name}':")
            for dep_type, items in dependencies.items():
                if items:
                    self.log(f"   {dep_type}: {', '.join(items)}")
        
        return extracted_content, True
    
    def analyze_section_dependencies(self, section_content: str) -> Dict[str, List[str]]:
        """Light-touch analysis to detect potential dependencies in transplanted code.
        
        Returns:
            Dict with dependency types as keys and lists of detected items as values
        """
        dependencies = {
            "Constants/Variables": [],
            "External Functions": [],
            "Template References": [],
            "File Paths": [],
            "Potential Issues": []
        }
        
        lines = section_content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            # Detect undefined constants (common pattern: UPPERCASE_NAMES)
            import re
            
            # Look for references to constants that aren't defined in the section
            const_pattern = r'\b[A-Z][A-Z_]+[A-Z]\b'
            constants = re.findall(const_pattern, stripped)
            for const in constants:
                if const not in ['API', 'URL', 'HTTP', 'GET', 'POST', 'JSON', 'CSV', 'HTML', 'ID']:  # Common abbreviations
                    if f"{const} =" not in section_content:  # Not defined in section
                        dependencies["Constants/Variables"].append(const)
            
            # Detect template references
            if 'template' in stripped.lower() and ('QUERY_TEMPLATES' in stripped or 'TEMPLATE_CONFIG' in stripped):
                dependencies["Template References"].append(stripped[:50] + "..." if len(stripped) > 50 else stripped)
            
            # Detect file path patterns
            if any(pattern in stripped for pattern in ['.txt', '.csv', '.json', 'TOKEN_FILE', 'botify_token']):
                dependencies["File Paths"].append(stripped[:50] + "..." if len(stripped) > 50 else stripped)
            
            # Detect function calls that might be external
            func_pattern = r'self\.([a-z_]+)\('
            functions = re.findall(func_pattern, stripped)
            for func in functions:
                if func not in ['log', 'get', 'set', 'add', 'read', 'write']:  # Common methods
                    dependencies["External Functions"].append(func)
        
        # Deduplicate lists
        for key in dependencies:
            dependencies[key] = list(set(dependencies[key]))[:5]  # Limit to 5 items per category
        
        return dependencies
    
    def replace_atomic_section(self, target_content: str, new_section_content: str, section_name: str) -> Tuple[str, bool]:
        """
        Replace atomic section in target content using split/join methodology.
        
        Returns:
            Tuple of (new_content, success)
        """
        start_marker, end_marker = self.get_section_markers(section_name)
        
        # Split on start marker
        start_parts = target_content.split(start_marker)
        if len(start_parts) != 2:
            return target_content, False
        
        # Split the second part on end marker
        end_parts = start_parts[1].split(end_marker)
        if len(end_parts) < 2:
            # Try generic end marker as fallback
            generic_end = "# --- END_WORKFLOW_SECTION ---"
            end_parts = start_parts[1].split(generic_end)
            if len(end_parts) >= 2:
                # Replace section with new content, maintaining generic end marker
                new_content = start_parts[0] + new_section_content.replace(end_marker, generic_end) + generic_end.join(end_parts[1:])
                return new_content, True
            return target_content, False
        
        # Reconstruct with new section content
        new_content = start_parts[0] + new_section_content + end_marker.join(end_parts[1:])
        return new_content, True
    
    def validate_section_markers(self, content: str, section_name: str) -> Tuple[bool, List[str]]:
        """
        Validate that a file has complete atomic section markers.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        start_marker, end_marker = self.get_section_markers(section_name)
        
        # Check for start marker
        if start_marker not in content:
            errors.append(f"Missing start marker: {start_marker}")
        
        # Check for end marker or generic end marker
        generic_end = "# --- END_WORKFLOW_SECTION ---"
        if end_marker not in content and generic_end not in content:
            errors.append(f"Missing end marker: {end_marker} or {generic_end}")
        
        # Check for required sub-markers
        required_markers = [
            "# --- SECTION_STEP_DEFINITION ---",
            "# --- END_SECTION_STEP_DEFINITION ---",
            "# --- SECTION_STEP_METHODS ---",
            "# --- END_SECTION_STEP_METHODS ---"
        ]
        
        for marker in required_markers:
            if marker not in content:
                errors.append(f"Missing required marker: {marker}")
        
        return len(errors) == 0, errors
    
    def transplant_section(self, source_file: str, target_file: str, section_name: str) -> bool:
        """
        Transplant atomic section from source file to target file.
        
        Returns:
            True if successful, False otherwise
        """
        self.log(f"🔬 Starting atomic transplantation:")
        self.log(f"   Source: {source_file}")
        self.log(f"   Target: {target_file}")
        self.log(f"   Section: {section_name}")
        
        # Validate files exist
        if not os.path.exists(source_file):
            self.log(f"❌ Source file not found: {source_file}")
            return False
        
        if not os.path.exists(target_file):
            self.log(f"❌ Target file not found: {target_file}")
            return False
        
        try:
            # Read source file
            self.log(f"📖 Reading source file...")
            source_content = self.read_file(source_file)
            
            # Extract atomic section from source
            self.log(f"🧬 Extracting atomic section...")
            section_content, extract_success = self.extract_atomic_section(source_content, section_name)
            
            if not extract_success:
                self.log(f"❌ Failed to extract section '{section_name}' from source file")
                return False
            
            self.log(f"✅ Successfully extracted {len(section_content)} characters")
            
            # Read target file
            self.log(f"📖 Reading target file...")
            target_content = self.read_file(target_file)
            
            # Validate target has the section markers
            self.log(f"🔍 Validating target file markers...")
            is_valid, errors = self.validate_section_markers(target_content, section_name)
            
            if not is_valid:
                self.log(f"❌ Target file validation failed:")
                for error in errors:
                    self.log(f"   - {error}")
                return False
            
            self.log(f"✅ Target file markers validated")
            
            # Create backup
            backup_path = self.create_backup(target_file)
            
            # Replace section in target
            self.log(f"🔄 Replacing atomic section in target...")
            new_target_content, replace_success = self.replace_atomic_section(target_content, section_content, section_name)
            
            if not replace_success:
                self.log(f"❌ Failed to replace section in target file")
                return False
            
            # Write updated target file
            self.log(f"💾 Writing updated target file...")
            self.write_file(target_file, new_target_content)
            
            self.log(f"🎉 Atomic transplantation completed successfully!")
            self.log(f"   📊 Section size: {len(section_content)} characters")
            if backup_path:
                self.log(f"   📋 Backup created: {backup_path}")
            
            # Generate post-transplantation summary
            self.generate_post_transplant_summary(section_content, section_name, target_file)
            
            return True
            
        except Exception as e:
            self.log(f"💥 Transplantation failed: {str(e)}")
            return False
    
    def extract_section_for_inspection(self, source_file: str, section_name: str) -> bool:
        """Extract and display atomic section for inspection."""
        self.log(f"🔍 Extracting section '{section_name}' from {source_file}")
        
        if not os.path.exists(source_file):
            self.log(f"❌ File not found: {source_file}")
            return False
        
        try:
            content = self.read_file(source_file)
            section_content, success = self.extract_atomic_section(content, section_name)
            
            if not success:
                self.log(f"❌ Failed to extract section '{section_name}'")
                return False
            
            self.log(f"✅ Successfully extracted section ({len(section_content)} characters):")
            self.log("=" * 80)
            print(section_content)
            self.log("=" * 80)
            
            return True
            
        except Exception as e:
            self.log(f"💥 Extraction failed: {str(e)}")
            return False
    
    def validate_file_markers(self, file_path: str, section_name: str) -> bool:
        """Validate that a file has complete markers for a section."""
        self.log(f"🔍 Validating markers in {file_path} for section '{section_name}'")
        
        if not os.path.exists(file_path):
            self.log(f"❌ File not found: {file_path}")
            return False
        
        try:
            content = self.read_file(file_path)
            is_valid, errors = self.validate_section_markers(content, section_name)
            
            if is_valid:
                self.log(f"✅ All required markers found and valid")
                return True
            else:
                self.log(f"❌ Validation failed:")
                for error in errors:
                    self.log(f"   - {error}")
                return False
                
        except Exception as e:
            self.log(f"💥 Validation failed: {str(e)}")
            return False

    def generate_post_transplant_summary(self, section_content: str, section_name: str, target_file: str):
        """Generate a comprehensive summary for follow-up LLMs about post-transplantation tasks.
        
        This method provides clear guidance about potential issues and required follow-up
        actions that LLMs should check after an atomic transplantation.
        """
        self.log("")
        self.log("=" * 80)
        self.log("🤖 POST-TRANSPLANTATION GUIDANCE FOR FOLLOW-UP LLMs")
        self.log("=" * 80)
        
        # Analyze dependencies again for comprehensive summary
        dependencies = self.analyze_section_dependencies(section_content)
        
        # Check for common issues
        common_issues = []
        if 'TOKEN_FILE' in section_content and 'TOKEN_FILE =' not in section_content:
            common_issues.append("TOKEN_FILE variable may need to be defined locally in methods")
        
        if 'QUERY_TEMPLATES' in section_content:
            common_issues.append("QUERY_TEMPLATES class attribute may need to be added")
            
        if 'UI_CONSTANTS' in section_content:
            common_issues.append("UI_CONSTANTS class attribute may need to be added")
            
        if 'TEMPLATE_CONFIG' in section_content:
            common_issues.append("TEMPLATE_CONFIG class attribute may need to be added")
        
        self.log(f"📁 TARGET FILE: {target_file}")
        self.log(f"🧬 SECTION TRANSPLANTED: {section_name}")
        self.log("")
        
        if any(dependencies.values()) or common_issues:
            self.log("⚠️  FOLLOW-UP TASKS FOR LLMs:")
            self.log("")
            
            if common_issues:
                self.log("🔧 LIKELY MISSING DEPENDENCIES:")
                for issue in common_issues:
                    self.log(f"   • {issue}")
                self.log("")
            
            if dependencies["Constants/Variables"]:
                self.log("📋 CONSTANTS TO VERIFY:")
                for const in dependencies["Constants/Variables"]:
                    self.log(f"   • {const} - Check if defined in target file")
                self.log("")
            
            if dependencies["Template References"]:
                self.log("🎯 TEMPLATE DEPENDENCIES:")
                for ref in dependencies["Template References"]:
                    self.log(f"   • {ref}")
                self.log("")
            
            if dependencies["File Paths"]:
                self.log("📄 FILE PATH REFERENCES:")
                for path in dependencies["File Paths"]:
                    self.log(f"   • {path}")
                self.log("")
                
            self.log("🧪 RECOMMENDED CHECKS:")
            self.log("   1. Test server startup - check for NameError or AttributeError")
            self.log("   2. Verify all class attributes are defined (QUERY_TEMPLATES, etc.)")
            self.log("   3. Check that file path constants are properly scoped")
            self.log("   4. Test workflow functionality in browser")
            self.log("   5. Look for any missing imports or utility functions")
            
        else:
            self.log("✅ NO OBVIOUS DEPENDENCY ISSUES DETECTED")
            self.log("   • The transplanted section appears self-contained")
            self.log("   • Still recommended to test server startup and functionality")
        
        self.log("")
        self.log("🔗 ATOMIC TRANSPLANTATION COMPLETE")
        self.log("=" * 80)


def main():
    """Main entry point with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Atomic Transplantation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Transplant command
    transplant_cmd = subparsers.add_parser(
        'transplant',
        help='Transplant atomic section from source to target file'
    )
    transplant_cmd.add_argument('source', help='Source file path')
    transplant_cmd.add_argument('target', help='Target file path')
    transplant_cmd.add_argument('--section', required=True, help='Section name to transplant')
    transplant_cmd.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    
    # Extract command
    extract_cmd = subparsers.add_parser(
        'extract',
        help='Extract and display atomic section from file'
    )
    extract_cmd.add_argument('file', help='File path')
    extract_cmd.add_argument('--section', required=True, help='Section name to extract')
    
    # Validate command
    validate_cmd = subparsers.add_parser(
        'validate',
        help='Validate atomic section markers in file'
    )
    validate_cmd.add_argument('file', help='File path')
    validate_cmd.add_argument('--section', required=True, help='Section name to validate')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create engine instance
    engine = AtomicTransplantationEngine(
        verbose=True,
        backup=not getattr(args, 'no_backup', False)
    )
    
    # Execute command
    try:
        if args.command == 'transplant':
            success = engine.transplant_section(args.source, args.target, args.section)
            sys.exit(0 if success else 1)
        
        elif args.command == 'extract':
            success = engine.extract_section_for_inspection(args.file, args.section)
            sys.exit(0 if success else 1)
        
        elif args.command == 'validate':
            success = engine.validate_file_markers(args.file, args.section)
            sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 