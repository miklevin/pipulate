import os
import sys
import json
import yaml
import re
from datetime import datetime
import getpass
from pathlib import Path
import google.generativeai as genai
import argparse # NEW: Import argparse for command-line flags

# --- CONFIGURATION ---
OUTPUT_DIR = "/home/mike/repos/MikeLev.in/_posts"
ARTICLE_FILENAME = "article.txt"
PROMPT_FILENAME = "editing_prompt.txt"
PROMPT_PLACEHOLDER = "[INSERT FULL ARTICLE]"
# --- NEW CACHE CONFIG ---
INSTRUCTIONS_CACHE_FILE = "instructions.json" # NEW: Define a filename for the cache
# --- NEW KEY MANAGEMENT CONFIG ---
CONFIG_DIR = Path.home() / ".config" / "articleizer"
API_KEY_FILE = CONFIG_DIR / "api_key.txt"
# --------------------------------

def get_api_key():
    """
    Gets the API key by first checking a local config file, and if not found,
    securely prompting the user and offering to save it.
    """
    if API_KEY_FILE.is_file():
        print(f"Reading API key from {API_KEY_FILE}...")
        return API_KEY_FILE.read_text().strip()

    print("Google API Key not found.")
    print("Please go to https://aistudio.google.com/app/apikey to get one.")
    key = getpass.getpass("Enter your Google API Key: ")

    save_key_choice = input(f"Do you want to save this key to {API_KEY_FILE} for future use? (y/n): ").lower()
    if save_key_choice == 'y':
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            API_KEY_FILE.write_text(key)
            API_KEY_FILE.chmod(0o600)
            print(f"✅ Key saved securely.")
        except Exception as e:
            print(f"⚠️ Could not save API key. Error: {e}")
    return key

def create_jekyll_post(article_content, instructions):
    print("Formatting final Jekyll post...")

    editing_instr = instructions.get("editing_instructions", {})
    analysis_content = instructions.get("book_analysis_content", {})
    yaml_updates = editing_instr.get("yaml_updates", {})

    # 1. Build the Jekyll YAML front matter
    new_yaml_data = {
        'title': yaml_updates.get("title"),
        'permalink': yaml_updates.get("permalink"),
        'description': analysis_content.get("authors_imprint"),
        'meta_description': yaml_updates.get("description"),
        'meta_keywords': yaml_updates.get("keywords"),
        'layout': 'post',
        'sort_order': 1
    }
    final_yaml_block = f"---\n{yaml.dump(new_yaml_data, Dumper=yaml.SafeDumper, sort_keys=False, default_flow_style=False)}---"

    # 2. Get the raw article body and add a header
    article_body = article_content.strip()
    article_body = f"## Technical Journal Entry Begins\n\n{article_body}"

    # 3. Insert subheadings
    subheadings = editing_instr.get("insert_subheadings", [])
    for item in reversed(subheadings):
        snippet = item.get("after_text_snippet", "")
        subheading = item.get("subheading", "## Missing Subheading")
        if not snippet:
            print(f"Warning: Skipping subheading '{subheading}' due to missing snippet.")
            continue

        # Clean the snippet: remove leading/trailing whitespace and ellipses.
        clean_snippet = snippet.strip().strip('...')
        # Create the regex pattern from the CLEANED snippet.
        pattern_text = re.escape(clean_snippet).replace(r'\\ ', r'\\s+')

        match = re.search(pattern_text, article_body, re.IGNORECASE)
        if match:
            insertion_point = article_body.find('\n', match.end())
            if insertion_point == -1:
                insertion_point = len(article_body)
            article_body = (
                article_body[:insertion_point] +
                f"\n\n{subheading}" +
                article_body[insertion_point:]
            )
        else:
            print(f"Warning: Snippet not found for subheading '{subheading}': '{snippet}'")

    # 4. Prepend the "Curious Reader" intro
    prepend_text = editing_instr.get("prepend_to_article_body", "")
    if prepend_text:
        intro_section = f"## Setting the Stage: Context for the Curious Book Reader\n\n{prepend_text}\n\n---"
        article_body = f"{intro_section}\n\n{article_body}"

    # 5. Build the Book Analysis section
    analysis_markdown = "\n## Book Analysis\n"
    if 'ai_editorial_take' in analysis_content:
        analysis_markdown += f"\n### Ai Editorial Take\n{analysis_content['ai_editorial_take']}\n"
    for key, value in analysis_content.items():
        if key in ['authors_imprint', 'ai_editorial_take']:
            continue
        title = key.replace('_', ' ').title()
        analysis_markdown += f"\n### {title}\n"
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    analysis_markdown += f"* **Title Option:** {item.get('title', 'N/A')}\n"
                    analysis_markdown += f"  * **Filename:** `{item.get('filename', 'N/A')}`\n"
                    analysis_markdown += f"  * **Rationale:** {item.get('rationale', 'N/A')}\n"
                else:
                    analysis_markdown += f"- {item}\n"
        elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    analysis_markdown += f"- **{sub_key.replace('_', ' ').title()}:**\n"
                    if isinstance(sub_value, list):
                        for point in sub_value:
                            analysis_markdown += f"  - {point}\n"
                    else:
                        analysis_markdown += f"  - {sub_value}\n"
        else:
            analysis_markdown += f"{value}\n"

    # 6. Assemble final document
    final_content = f"{final_yaml_block}\n\n{article_body}\n\n---\n{analysis_markdown}"

    # 7. Generate filename and save
    current_date = datetime.now().strftime('%Y-%m-%d')
    slug = "untitled-article"
    title_brainstorm = analysis_content.get("title_brainstorm", [])
    if title_brainstorm and title_brainstorm[0].get("filename"):
        slug = os.path.splitext(title_brainstorm[0]["filename"])[0]

    output_filename = f"{current_date}-{slug}.md"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"✨ Success! Article saved to: {output_path}")

def main():
    # NEW: Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Process an article with the Gemini API and format it for Jekyll.")
    parser.add_argument(
        '-l', '--local',
        action='store_true',
        help=f"Use local '{INSTRUCTIONS_CACHE_FILE}' cache instead of calling the API."
    )
    args = parser.parse_args()

    # Step 1: Load the base article text (needed in both modes)
    if not os.path.exists(ARTICLE_FILENAME):
        print(f"Error: Article file '{ARTICLE_FILENAME}' not found.")
        return
    with open(ARTICLE_FILENAME, 'r', encoding='utf-8') as f:
        article_text = f.read()

    instructions = None

    # NEW: Main logic branches based on the --local flag
    if args.local:
        print(f"Attempting to use local cache file: {INSTRUCTIONS_CACHE_FILE}")
        if not os.path.exists(INSTRUCTIONS_CACHE_FILE):
            print(f"Error: Cache file not found. Run without --local to create it.")
            return
        try:
            with open(INSTRUCTIONS_CACHE_FILE, 'r', encoding='utf-8') as f:
                instructions = json.load(f)
            print("Successfully loaded instructions from local cache.")
        except json.JSONDecodeError:
            print("Error: Could not parse the local instructions cache file. It may be corrupt.")
            return
    else:
        # This block contains the original API call logic
        api_key = get_api_key()
        if not api_key:
            print("API Key not provided. Exiting.")
            return
        genai.configure(api_key=api_key)

        if not os.path.exists(PROMPT_FILENAME):
            print(f"Error: Prompt file '{PROMPT_FILENAME}' not found.")
            return
        with open(PROMPT_FILENAME, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        full_prompt = prompt_template.replace(PROMPT_PLACEHOLDER, article_text)

        print("Calling the Gemini API directly... (This may take a moment)")
        try:
            model = genai.GenerativeModel('gemini-2.5-pro') # Make sure this model name is correct
            response = model.generate_content(full_prompt)
            gemini_output = response.text
            print("Successfully received response from API.")
        except Exception as e:
            print(f"\nAn error occurred while calling the API: {e}")
            return

        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', gemini_output)
            json_str = json_match.group(1) if json_match else gemini_output
            instructions = json.loads(json_str)
            print("Successfully parsed JSON instructions.")
            
            # NEW: Save the successful instructions to the cache file
            with open(INSTRUCTIONS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(instructions, f, indent=4)
            print(f"✅ Instructions saved to '{INSTRUCTIONS_CACHE_FILE}' for future use.")

        except json.JSONDecodeError:
            print("\nError: Failed to parse JSON from API output.")
            print("--- API Raw Output ---\n" + gemini_output)
            return

    # Final step: If we have instructions (from API or cache), format the post.
    if instructions:
        create_jekyll_post(article_text, instructions)

if __name__ == '__main__':
    main()
