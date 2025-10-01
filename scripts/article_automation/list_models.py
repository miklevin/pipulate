# list_models.py
import google.generativeai as genai
from pathlib import Path

# --- We'll use the same logic to get the key ---
CONFIG_DIR = Path.home() / ".config" / "articleizer"
API_KEY_FILE = CONFIG_DIR / "api_key.txt"

if not API_KEY_FILE.is_file():
    print(f"API key file not found at {API_KEY_FILE}")
    print("Please run articleizer.py once to save your key.")
    exit()

api_key = API_KEY_FILE.read_text().strip()
genai.configure(api_key=api_key)

print("--- Available Models for Generate Content ---")
for model in genai.list_models():
  if 'generateContent' in model.supported_generation_methods:
    print(model.name)
print("-----------------------------------------")