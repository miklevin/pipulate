#!/usr/bin/env python3
import argparse
import os
import shutil
import re
import json
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from collections import Counter, namedtuple

# --- Marker constants ---
START_WORKFLOW_SECTION_TPL = "# --- START_WORKFLOW_SECTION: {section_name} ---"
END_WORKFLOW_SECTION_TPL = "# --- END_WORKFLOW_SECTION: {section_name} ---"
SECTION_STEP_DEFINITION_START = "# --- SECTION_STEP_DEFINITION ---"
SECTION_STEP_DEFINITION_END = "# --- END_SECTION_STEP_DEFINITION ---"
SECTION_STEP_METHODS_START = "# --- SECTION_STEP_METHODS ---"
SECTION_STEP_METHODS_END = "# --- END_SECTION_STEP_METHODS ---"
SECTION_HELPER_METHODS_START = "# --- SECTION_HELPER_METHODS ---"
SECTION_HELPER_METHODS_END = "# --- END_SECTION_HELPER_METHODS ---"

MARKER_PAIRS = {
    "WORKFLOW_SECTION": (START_WORKFLOW_SECTION_TPL, END_WORKFLOW_SECTION_TPL),
    "STEP_DEFINITION": (SECTION_STEP_DEFINITION_START, SECTION_STEP_DEFINITION_END),
    "STEP_METHODS": (SECTION_STEP_METHODS_START, SECTION_STEP_METHODS_END),
    "HELPER_METHODS": (SECTION_HELPER_METHODS_START, SECTION_HELPER_METHODS_END),
}
SUB_SECTION_KEYS = ["STEP_DEFINITION", "STEP_METHODS", "HELPER_METHODS"] 

def find_pipulate_root():
    current_dir = Path(__file__).resolve().parent
    while current_dir != current_dir.parent:
        if (current_dir / "plugins").is_dir() and (current_dir / "server.py").is_file():
            return current_dir
        current_dir = current_dir.parent
    possible_roots = [Path.cwd(), Path.home() / "repos" / "pipulate", Path("/app")]
    for root in possible_roots:
        if root.exists() and (root / "plugins").is_dir() and (root / "server.py").is_file():
            return root
    raise FileNotFoundError("Could not find Pipulate project root.")

PROJECT_ROOT = find_pipulate_root()
PLUGINS_DIR = PROJECT_ROOT / "plugins"

def get_markers(marker_type_key: str, section_name: Optional[str] = None) -> Tuple[str, str]:
    start_tpl, end_tpl = MARKER_PAIRS[marker_type_key]
    start_marker = start_tpl.format(section_name=section_name) if "{section_name}" in start_tpl else start_tpl
    end_marker = end_tpl.format(section_name=section_name) if "{section_name}" in end_tpl else end_tpl
    return start_marker, end_marker

def extract_block_with_markers(content: str, marker_type_key: str, section_name: Optional[str] = None) -> Optional[str]:
    start_marker, end_marker = get_markers(marker_type_key, section_name)
    pattern_str = r"^(?P<leading_indent>\s*)" + re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\s*$"
    pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE)
    match = pattern.search(content)
    return match.group(0) if match else None

def extract_content_between_markers(block_with_markers: str, marker_type_key: str, section_name: Optional[str] = None) -> str:
    if not block_with_markers: return ""
    start_marker, end_marker = get_markers(marker_type_key, section_name)
    start_match = re.search(re.escape(start_marker) + r"(\r\n|\r|\n)", block_with_markers, re.MULTILINE)
    content_start_pos = start_match.end() if start_match else 0
    end_match = None
    for m in re.finditer(r"^\s*" + re.escape(end_marker), block_with_markers, re.MULTILINE): end_match = m
    content_end_pos = end_match.start() if end_match else len(block_with_markers)
    return block_with_markers[content_start_pos:content_end_pos].rstrip("\r\n")

def extract_workflow_section_parts(source_content: str, section_name: str, issues_list: List[str]) -> Tuple[Optional[str], Dict[str, Optional[str]], Optional[str]]:
    full_workflow_block_source = extract_block_with_markers(source_content, "WORKFLOW_SECTION", section_name)
    if not full_workflow_block_source:
        issues_list.append(f"WARNING: Source WORKFLOW_SECTION '{section_name}' not found.")
        return None, {}, ""
    start_marker_source, end_marker_source = get_markers("WORKFLOW_SECTION", section_name)
    inner_content_match_regex = re.escape(start_marker_source) + r"(\r\n|\r|\n)(?P<inner_content>.*?)(?=(?:\r\n|\r|\n)^\s*" + re.escape(end_marker_source) + ")"
    inner_content_match = re.search(inner_content_match_regex, full_workflow_block_source, re.DOTALL | re.MULTILINE)
    inner_content = inner_content_match.group("inner_content") if inner_content_match else ""
    first_sub_section_start_pos = len(inner_content) 
    for key in SUB_SECTION_KEYS:
        sub_start_marker, _ = get_markers(key)
        match = re.search(r"^\s*" + re.escape(sub_start_marker), inner_content, re.MULTILINE)
        if match: first_sub_section_start_pos = min(first_sub_section_start_pos, match.start())
    source_description_part = inner_content[:first_sub_section_start_pos]
    source_description_lines = [line.lstrip() for line in source_description_part.strip().splitlines()]
    source_description_stripped = "\n".join(source_description_lines)
    if not source_description_stripped.strip(): issues_list.append(f"INFO: No description found in source WORKFLOW_SECTION '{section_name}'.")
    sub_sections_source_blocks = {}
    for key in SUB_SECTION_KEYS:
        sub_sections_source_blocks[key] = extract_block_with_markers(inner_content, key)
        if not sub_sections_source_blocks[key]: issues_list.append(f"WARNING: Sub-section '{key}' not found in source WORKFLOW_SECTION '{section_name}'.")
    return full_workflow_block_source, sub_sections_source_blocks, source_description_stripped.strip()

def re_indent_block(block_content: str, new_base_indent: str) -> str:
    if not block_content: return ""
    block_content = block_content.strip('\r\n') 
    lines = block_content.splitlines()
    if not lines: return ""
    min_indent_val = float('inf')
    first_line_is_marker = any(m_start in lines[0] for m_key in MARKER_PAIRS for m_start,_ in [get_markers(m_key)])
    current_block_indent = len(lines[0]) - len(lines[0].lstrip()) if lines[0].strip() else 0
    if first_line_is_marker: min_indent_val = current_block_indent
    else: 
        for line in lines:
            if line.strip(): min_indent_val = min(min_indent_val, len(line) - len(line.lstrip()))
        if min_indent_val == float('inf'): min_indent_val = 0
    re_indented_lines = [new_base_indent + (line[min_indent_val:] if line.startswith(" " * min_indent_val) else line.lstrip()) if line.strip() else (new_base_indent if line.isspace() and new_base_indent.strip() == "" else "") for line in lines]
    return "\n".join(re_indented_lines) + "\n"

def get_original_step_id_from_section_name(section_name: str) -> Optional[str]:
    match = re.match(r"(step_\d+)", section_name)
    return match.group(1) if match else None

def rename_step_definition_content(content_str: str, new_base_id: str, issues_list: List[str]) -> str:
    original_content_for_compare = str(content_str)
    def replacer(match):
        step_args_str = match.group(1)
        old_id_match = re.search(r"id\s*=\s*['\"]([^'\"]*)['\"]", step_args_str)
        old_id = old_id_match.group(1) if old_id_match else "N/A"
        old_done_match = re.search(r"done\s*=\s*['\"]([^'\"]*)['\"]", step_args_str)
        old_done = old_done_match.group(1) if old_done_match else "N/A"
        old_show_match = re.search(r"show\s*=\s*['\"]([^'\"]*)['\"]", step_args_str)
        old_show = old_show_match.group(1) if old_show_match else "N/A"
        new_id_arg = f"id='{new_base_id}'"
        new_done_val = f"{new_base_id}_processed" 
        new_done_arg = f"done='{new_done_val}'"
        show_name_parts = new_base_id.split('_')
        show_name = " ".join([part.capitalize() for part in show_name_parts])
        new_show_arg = f"show='Updated {show_name} Content'"
        modified_args = step_args_str
        modified_args = re.sub(r"id\s*=\s*['\"][^'\"]*['\"]", new_id_arg, modified_args)
        modified_args = re.sub(r"done\s*=\s*['\"][^'\"]*['\"]", new_done_arg, modified_args)
        modified_args = re.sub(r"show\s*=\s*['\"][^'\"]*['\"]", new_show_arg, modified_args)
        issues_list.append(f"INFO: Renamed Step: id '{old_id}'->'{new_base_id}', done '{old_done}'->'{new_done_val}', show \"{old_show}\"->'Updated {show_name} Content'.")
        return f"Step({modified_args})"
    content_str = re.sub(r"Step\((.*?)\)", replacer, content_str, flags=re.DOTALL)
    if content_str != original_content_for_compare and original_content_for_compare.strip():
         issues_list.append(f"WARNING: `done` key in Step definition for '{new_base_id}' changed. Review dependent steps and `self.steps_indices` or `self.step_messages` in __init__.")
    return content_str

def rename_methods_content(content_str: str, original_step_id: str, new_base_id: str, issues_list: List[str]) -> str:
    if not original_step_id or not new_base_id or original_step_id == new_base_id: return content_str
    pattern = re.compile(r"(?P<keyword>async\s+def|def)\s+(?P<prefix>[\w_]*?)" + re.escape(original_step_id) + r"(?P<suffix>[\w]*?\s*\()")
    modified_content = ""
    last_end = 0
    methods_renamed_count = 0
    for match in pattern.finditer(content_str):
        methods_renamed_count +=1
        modified_content += content_str[last_end:match.start()]
        keyword, prefix, original_id_matched, suffix = match.group('keyword'), match.group('prefix'), match.group(3), match.group('suffix') 
        old_method_name = f"{prefix}{original_id_matched}{suffix.rstrip(' (')}"
        new_method_name = f"{prefix}{new_base_id}{suffix.rstrip(' (')}"
        issues_list.append(f"INFO: Renamed method: '{keyword} {old_method_name}()' -> '{keyword} {new_method_name}()'.")
        modified_content += f"{keyword} {prefix}{new_base_id}{suffix}"
        last_end = match.end()
    modified_content += content_str[last_end:]
    if methods_renamed_count > 0:
        issues_list.append(f"MANUAL REVIEW: Method names changed from '{original_step_id}' to '{new_base_id}'. Check `next_step_id` logic, UI calls (hx_get/hx_post), and internal references within transplanted methods.")
    return modified_content

def print_issues_and_exit(issues: List[str], target_file_path: Optional[Path] = None, modified_in_mem: bool = False, is_simulation: bool = False): # Default is_simulation to False
    if issues:
        header = "--- ISSUES AND REVIEW NOTES (SIMULATED) ---" if is_simulation else "--- Transplant Issues and Review Notes ---"
        print(f"\n{header}")
        for issue in issues: print(f"- {issue}")
        
        if target_file_path and modified_in_mem and not is_simulation: 
            try:
                with open(target_file_path, "a", encoding="utf-8") as f:
                    f.write("\n\n# --- SCRIPT TRANSPLANT ISSUES ---\n")
                    for issue in issues: f.write(f"# {issue}\n")
                    f.write("# --- END SCRIPT TRANSPLANT ISSUES ---\n")
                print(f"\nIssues also appended to {target_file_path}")
            except Exception as e: print(f"ERROR: Could not append issues to target file: {e}")
        elif is_simulation and modified_in_mem :
             print(f"\n(SIM_INFO: Issues would be appended to the target file: {target_file_path})")
    else: print("\nNo issues or specific review notes identified during transplant.")
    
    if any(issue.startswith("CRITICAL") for issue in issues) and not is_simulation:
        print("Critical issues found. Exiting.")
        exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Update/transplant a section in a target workflow file from a source workflow file, with renaming.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""
Examples:
  python {Path(__file__).name} --target plugins/dummy_target_workflow.py --source plugins/535_botify_trifecta.py --section step_01_botify_project_url --target_section_name_to_update step_01_dummy_section --new_base_id_for_renaming step_03
"""
    )
    parser.add_argument("--target", required=True, help="Path to the target workflow file.")
    parser.add_argument("--source", required=True, help="Path to the source workflow file.")
    parser.add_argument("--section", required=True, help="Section name in source (e.g., step_01_botify_project_url).")
    parser.add_argument("--target_section_name_to_update", required=True, help="Full name of the WORKFLOW_SECTION in the target file to be updated (e.g., step_01_dummy_section).")
    parser.add_argument("--new_base_id_for_renaming", required=True, help="New base step ID for renaming internal components (e.g., step_03).")
    parser.add_argument("--force", action='store_true', help="Skip backup.")
    
    args = parser.parse_args()
    issues_found = []
    
    # Define Step for potential eval context if workflow files rely on it being globally available
    # This is mostly for safety; ideally, workflow files manage their own imports or definitions.
    global Step
    Step = namedtuple('Step', ['id', 'done', 'show', 'refill', 'transform'], defaults=(None,))


    source_section_name_parts = args.section.split('_', 2)
    target_section_description_suffix = args.section 
    if len(source_section_name_parts) > 2 and source_section_name_parts[0].startswith("step"):
        target_section_description_suffix = source_section_name_parts[2]
    target_section_name_for_new_markers = f"{args.new_base_id_for_renaming}_{target_section_description_suffix}"

    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Attempting to update target file: {args.target}")
    print(f"Using source file: {args.source}")
    print(f"Source section name: {args.section}")
    print(f"Target section to find and update: {args.target_section_name_to_update}")
    print(f"New base_id for renaming internal content: {args.new_base_id_for_renaming}")
    print(f"WORKFLOW_SECTION markers in target will be updated to use name: {target_section_name_for_new_markers}")
    print(f"Force (no backup): {args.force}\n")

    source_file_path = PROJECT_ROOT / args.source if not Path(args.source).is_absolute() else Path(args.source)
    target_file_path = PROJECT_ROOT / args.target if not Path(args.target).is_absolute() else Path(args.target)

    if not source_file_path.exists(): issues_found.append(f"CRITICAL: Source file missing: {source_file_path}"); print_issues_and_exit(issues_found, target_file_path, False); return
    if not target_file_path.exists(): issues_found.append(f"CRITICAL: Target file missing: {target_file_path}"); print_issues_and_exit(issues_found, target_file_path, False); return

    if not args.force:
        timestamp = str(int(os.path.getmtime(target_file_path))) if target_file_path.exists() else str(int(Path.cwd().stat().st_mtime))
        backup_path = target_file_path.with_suffix(f"{target_file_path.suffix}.bak_{timestamp}")
        try: shutil.copyfile(target_file_path, backup_path); print(f"Backup created: {backup_path}")
        except Exception as e: issues_found.append(f"CRITICAL: Could not create backup: {e}"); print_issues_and_exit(issues_found, target_file_path, False); return
    else: print("Skipping backup (--force).")

    with open(source_file_path, "r", encoding="utf-8") as f: source_content = f.read()
    with open(target_file_path, "r", encoding="utf-8") as f: target_content_original = f.read()
    
    target_content_final = str(target_content_original) 

    original_step_id_from_source = get_original_step_id_from_section_name(args.section)
    if not original_step_id_from_source:
        issues_found.append(f"WARNING: Could not derive original step_ID (e.g. 'step_01') from source section name '{args.section}'. Method renaming might be incomplete.")

    _, source_sub_section_blocks, source_description_stripped = extract_workflow_section_parts(source_content, args.section, issues_found)
    if source_description_stripped is None and not any(source_sub_section_blocks.values()):
        issues_found.append(f"CRITICAL: Main WORKFLOW_SECTION '{args.section}' or its content not found in source. Aborting.")
        print_issues_and_exit(issues_found, target_file_path, False); return 
    
    if source_description_stripped: issues_found.append(f"INFO: Source Description for '{args.section}' to be used: '{source_description_stripped[:100].strip()}...'")

    renamed_source_sub_sections = {}
    for key, block_content_with_markers in source_sub_section_blocks.items():
        if not block_content_with_markers: renamed_source_sub_sections[key] = None; continue
        content_to_rename = extract_content_between_markers(block_content_with_markers, key)
        renamed_inner_content = content_to_rename
        if key == "STEP_DEFINITION":
            renamed_inner_content = rename_step_definition_content(content_to_rename, args.new_base_id_for_renaming, issues_found)
        elif key in ["STEP_METHODS", "HELPER_METHODS"] and original_step_id_from_source:
            renamed_inner_content = rename_methods_content(content_to_rename, original_step_id_from_source, args.new_base_id_for_renaming, issues_found)
        start_m, end_m = get_markers(key)
        block_indent_match = re.match(r"^\s*", block_content_with_markers); block_indent = block_indent_match.group(0) if block_indent_match else "    " 
        renamed_source_sub_sections[key] = f"{block_indent}{start_m}\n{renamed_inner_content}\n{block_indent}{end_m}\n" if renamed_inner_content.strip() else f"{block_indent}{start_m}\n{block_indent}{end_m}\n"
    
    if renamed_source_sub_sections.get("HELPER_METHODS"):
        issues_found.append(f"MANUAL REVIEW: SECTION_HELPER_METHODS transplanted. Review for potential name conflicts, dependencies, or if they should be in a shared utility.")
    
    target_start_marker_to_find, target_end_marker_to_find = get_markers("WORKFLOW_SECTION", args.target_section_name_to_update)
    target_workflow_pattern = re.compile(
        r"^(?P<overall_leading_indent>\s*)" + re.escape(target_start_marker_to_find) + r"\n" +
        r"(?P<inner_content_target>.*?)" + 
        r"^(?P=overall_leading_indent)" + re.escape(target_end_marker_to_find) + r"\s*$",
        re.DOTALL | re.MULTILINE
    )
    
    processed_content_parts = []
    last_idx = 0
    matches_found_in_target = 0

    for match in target_workflow_pattern.finditer(target_content_original):
        matches_found_in_target += 1
        issues_found.append(f"INFO: Processing Target WORKFLOW_SECTION Match #{matches_found_in_target} for '{args.target_section_name_to_update}' (will be updated to use markers for '{target_section_name_for_new_markers}')")
        processed_content_parts.append(target_content_original[last_idx:match.start()])
        target_overall_indent = match.group("overall_leading_indent")
        target_inner_original = match.group("inner_content_target")
        
        new_description_part = ""
        if source_description_stripped:
            desc_lines = source_description_stripped.splitlines()
            new_description_part = "\n".join([target_overall_indent + line for line in desc_lines]) + "\n"
            issues_found.append(f"INFO: Description for target section '{target_section_name_for_new_markers}' will be updated.")

        target_existing_sub_sections = {}
        desc_in_target_match = re.match(r"(?:^\s*#.*?\n)*", target_inner_original, re.MULTILINE)
        target_sub_content_area_original = target_inner_original[desc_in_target_match.end():] if desc_in_target_match else target_inner_original
        for key in SUB_SECTION_KEYS:
            target_existing_sub_sections[key] = extract_block_with_markers(target_sub_content_area_original, key)

        new_inner_parts_for_section = []
        if new_description_part.strip():
            new_inner_parts_for_section.append(new_description_part)
            if any(renamed_source_sub_sections.get(k) or target_existing_sub_sections.get(k) for k in SUB_SECTION_KEYS):
                 new_inner_parts_for_section.append(target_overall_indent + "\n")

        for key in SUB_SECTION_KEYS:
            source_block_renamed = renamed_source_sub_sections.get(key)
            target_block_original = target_existing_sub_sections.get(key)
            final_block_to_add_raw = None
            if source_block_renamed and source_block_renamed.strip():
                issues_found.append(f"INFO: Using '{key}' from source section '{args.section}' for target section '{target_section_name_for_new_markers}'.")
                final_block_to_add_raw = source_block_renamed
            elif target_block_original and target_block_original.strip(): 
                issues_found.append(f"INFO: Keeping existing '{key}' from target section '{args.target_section_name_to_update}' (not in source or source block empty).")
                final_block_to_add_raw = target_block_original
            if final_block_to_add_raw:
                re_indented_final_block = re_indent_block(final_block_to_add_raw, target_overall_indent + "    ")
                new_inner_parts_for_section.append(re_indented_final_block)
        
        updated_inner_content = "".join(new_inner_parts_for_section).rstrip()
        if updated_inner_content or new_description_part.strip(): updated_inner_content += "\n"

        final_target_start_marker, final_target_end_marker = get_markers("WORKFLOW_SECTION", target_section_name_for_new_markers)
        full_updated_block = (f"{target_overall_indent}{final_target_start_marker}\n"
                              f"{updated_inner_content}"
                              f"{target_overall_indent}{final_target_end_marker}\n")
        processed_content_parts.append(full_updated_block)
        last_idx = match.end()
    
    processed_content_parts.append(target_content_original[last_idx:])
    target_content_final = "".join(processed_content_parts)

    if matches_found_in_target == 0:
        issues_found.append(f"CRITICAL: Target WORKFLOW_SECTION for '{args.target_section_name_to_update}' not found in {target_file_path}. No changes made to file content.")
    elif target_content_final != target_content_original:
        issues_found.append(f"MANUAL REVIEW: Review __init__ for changes to self.steps list, self.steps_indices, self.step_messages, and route registrations due to modifications for '{target_section_name_for_new_markers}'.")
        with open(target_file_path, "w", encoding="utf-8") as f: f.write(target_content_final)
        print(f"\nTarget file {target_file_path} updated successfully.")
    else:
        issues_found.append(f"INFO: No substantive changes were made to the target file content for section '{args.target_section_name_to_update}'.")

    print_issues_and_exit(issues_found, target_file_path, target_content_final != target_content_original, is_simulation=False)

if __name__ == "__main__":
    main()
