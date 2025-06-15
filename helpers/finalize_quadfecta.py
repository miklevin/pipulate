# helpers/finalize_quadfecta.py
import re
from pathlib import Path

def get_method_body(content: str, method_name: str) -> str:
    """Extracts the full text of an async method."""
    # This pattern captures the method from its definition to the point where the indentation level decreases.
    pattern = re.compile(
        rf"^(\s*)async def {method_name}\(self, request\):.*?\n([\s\S]*?)(?=\n\1\S)",
        re.MULTILINE
    )
    match = pattern.search(content)
    return match.group(0) if match else ""

def run_finalization():
    """
    This script automates the final updates to the newly created
    425_botify_quadfecta.py workflow file.
    """
    target_file = Path("plugins/425_botify_quadfecta.py")

    if not target_file.is_file():
        print(f"❌ ERROR: Target file not found at {target_file}")
        return

    print(f"🚀 Starting finalization of {target_file}...")
    content = target_file.read_text()
    original_content = content

    # --- 1. Update the self.steps list ---
    print("   - Updating self.steps list for Quadfecta...")
    new_steps_list = """
        crawl_template = self.get_configured_template('crawl')
        gsc_template = self.get_configured_template('gsc')
        ga_template = self.get_configured_template('ga')

        steps = [
            Step(id='step_01', done='botify_project', show='1. Botify Project URL', refill=True),
            Step(id='step_02', done='analysis_selection', show=f'2. Download Crawl: {crawl_template}', refill=False),
            Step(id='step_03', done='weblogs_check', show='3. Download Web Logs', refill=False),
            Step(id='step_04', done='search_console_check', show=f'4. Download GSC: {gsc_template}', refill=False),
            Step(id='step_05', done='ga_check', show=f'5. Download GA: {ga_template}', refill=False)
        ]
"""
    # This regex is more robust, looking for the __init__ method's steps list
    content, count = re.subn(
        r"crawl_template = self\.get_configured_template\('crawl'\)[\s\S]*?self\.steps_indices = \{step\.id: i for i, step in enumerate\(steps\)\}",
        f"{new_steps_list.strip()}\n\n        # --- STEPS_LIST_INSERTION_POINT ---\n        steps.append(Step(id='finalize', done='finalized', show='Finalize', refill=False))\n        self.steps = steps\n        self.steps_indices = {{step.id: i for i, step in enumerate(steps)}}",
        content,
        count=1,
        flags=re.MULTILINE
    )
    if count == 0:
        print("   - ⚠️  Could not replace the `steps` list automatically. Please check the `__init__` method.")

    # --- 2. Update the TOGGLE_CONFIG Dictionary ---
    print("   - Updating TOGGLE_CONFIG for step_05...")
    step_04_toggle_config = r"'step_04':\s*{[^}]+},"
    match = re.search(step_04_toggle_config, content)
    if match:
        step_04_block = match.group(0)
        step_05_block = step_04_block.replace("'step_04'", "'step_05'")
        step_05_block = step_05_block.replace("'search_console_check'", "'ga_check'")
        step_05_block = step_05_block.replace("'has_search_console'", "'has_ga'")
        step_05_block = step_05_block.replace("Search Console", "Google Analytics")
        content = content.replace(step_04_block, step_04_block + '\n' + step_05_block)
    else:
        print("   - ⚠️  Could not find TOGGLE_CONFIG for step_04 to duplicate.")

    # --- 3. Replace placeholder step_05 methods ---
    print("   - Replacing placeholder step_05 methods...")
    step_04_code = get_method_body(content, "step_04")
    step_04_submit_code = get_method_body(content, "step_04_submit")
    step_04_complete_code = get_method_body(content, "step_04_complete")
    
    if step_04_code and step_04_submit_code and step_04_complete_code:
        full_step_04_logic = step_04_code + "\n" + step_04_submit_code + "\n" + step_04_complete_code
        
        # Adapt for step 05
        step_05_logic = full_step_04_logic.replace("step_04", "step_05")
        step_05_logic = step_05_logic.replace("search_console_check", "ga_check")
        step_05_logic = step_05_logic.replace("has_search_console", "has_ga")
        step_05_logic = step_05_logic.replace("Search Console", "Google Analytics")
        step_05_logic = step_05_logic.replace("gsc.csv", "ga.csv")
        step_05_logic = step_05_logic.replace("gsc_data", "ga_data")
        step_05_logic = step_05_logic.replace("'gsc'", "'ga'")

        placeholder_regex = r"# --- START_SWAPPABLE_STEP: step_0\d ---[\s\S]*?# --- END_SWAPPABLE_STEP: step_0\d ---"
        content = re.sub(placeholder_regex, step_05_logic, content, count=1)
        print("   - Successfully replaced placeholder methods.")
    else:
        print("❌ ERROR: Could not find all necessary step_04 methods to copy.")

    # --- 4. Final write to file ---
    if content != original_content:
        target_file.write_text(content)
        print("✅ Finalization complete. Your Quadfecta workflow should now be free of syntax errors.")
    else:
        print("No changes were made. Please check the script and the target file.")


if __name__ == "__main__":
    run_finalization()