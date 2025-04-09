import os
import requests
import json
import logging
import argparse
import random
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ollama_iteration.log"),
        logging.StreamHandler()
    ]
)

# Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OUTPUT_FILE = "ollama_responses.json"

def check_ollama_status():
    """Check if Ollama is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def call_ollama(prompt, model="michaelborck/refuled"):
    """
    Simple function to call Ollama API.
    
    Args:
        prompt (str): The prompt to send to Ollama
        model (str): Model name to use
        
    Returns:
        str: Response from Ollama or None if failed
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['response'].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error communicating with Ollama: {e}")
        return None

def load_existing_responses():
    """Load previous responses if any."""
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load existing responses: {e}")
    return {}

def save_responses(responses):
    """Save responses to file."""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(responses, f, indent=2, ensure_ascii=False)
        logging.info(f"Saved responses to {OUTPUT_FILE}")
    except Exception as e:
        logging.error(f"Failed to save responses: {e}")

def read_file_content(file_path):
    """Read content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read file {file_path}: {e}")
        return None

def find_files(directory, pattern=None, limit=None, random_order=False, recursive=False):
    """Find files in a directory matching a pattern.
    
    Args:
        directory (str): Directory to search
        pattern (str): Pattern to match in filenames
        limit (int): Maximum number of files to return
        random_order (bool): Whether to randomize file order
        recursive (bool): Whether to search recursively in subdirectories
        
    Returns:
        list: List of file paths
    """
    all_files = []
    
    if recursive:
        # Recursive mode - search through all subdirectories
        for root, _, files in os.walk(directory):
            for file in files:
                if not pattern or pattern in file:
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)
    else:
        # Flat mode - only search in the specified directory
        try:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and (not pattern or pattern in file):
                    all_files.append(file_path)
        except Exception as e:
            logging.error(f"Error listing directory {directory}: {e}")
    
    if random_order:
        random.shuffle(all_files)
        
    if limit and limit < len(all_files):
        all_files = all_files[:limit]
        
    return all_files

def iterate_prompts(prompts, model="michaelborck/refuled", limit=None, random_order=False):
    """
    Process a list of prompts with Ollama.
    
    Args:
        prompts (list): List of prompts to process
        model (str): Model to use
        limit (int): Max number of prompts to process
        random_order (bool): Whether to randomize prompt order
    
    Returns:
        dict: Responses for each prompt
    """
    responses = load_existing_responses()
    
    # Randomize if requested
    if random_order:
        logging.info("Randomizing prompt order")
        random.shuffle(prompts)
    
    # Apply limit if specified
    if limit and limit < len(prompts):
        prompts = prompts[:limit]
    
    total = len(prompts)
    processed = 0
    skipped = 0
    
    logging.info(f"Using model: {model}")
    
    for i, prompt in enumerate(prompts):
        prompt_id = f"prompt_{i+1}"
        
        logging.info(f"Processing prompt {i+1}/{total}: {prompt[:50]}...")
        
        # Call Ollama
        logging.info(f"Calling model {model} for prompt {i+1}")
        response = call_ollama(prompt, model)
        
        if response:
            responses[prompt_id] = {
                "prompt": prompt,
                "response": response,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
            processed += 1
            
            # Print response
            print(f"\n{'='*80}")
            print(f"Prompt {i+1}/{total}")
            print(f"{'='*80}")
            print(f"Prompt sent to {model}:\n{'-'*40}\n{prompt}\n{'-'*40}")
            print(f"Response:\n{response}")
            print(f"{'='*80}")
            
            # Save after each successful call to preserve progress
            save_responses(responses)
        else:
            logging.warning(f"Failed to get response for prompt {i+1} with model {model}")
            skipped += 1
    
    logging.info(f"Processing complete: {processed}/{total} prompts processed, {skipped} skipped using model {model}")
    return responses

def process_files_with_prompt(files, prompt_template, model="michaelborck/refuled", is_direct_prompt=False, output_file=OUTPUT_FILE):
    """
    Process files using a prompt template that includes file content.
    
    Args:
        files (list): List of file paths to process
        prompt_template (str): Prompt template to use, use {content} placeholder for file content
        model (str): Model to use
        is_direct_prompt (bool): If True, the prompt will be used directly without formatting
        output_file (str): Output file to save responses to
    
    Returns:
        dict: Responses for each file
    """
    responses = load_existing_responses()
    
    total = len(files)
    processed = 0
    skipped = 0
    
    logging.info(f"Using model: {model}")
    
    for i, file_path in enumerate(files):
        file_id = os.path.basename(file_path)
        
        logging.info(f"Processing file {i+1}/{total}: {file_path}")
        
        # Read file content
        content = read_file_content(file_path)
        if not content:
            logging.warning(f"Skipping file {file_path}: Failed to read content")
            skipped += 1
            continue
            
        # Create prompt with file content or use direct prompt
        if is_direct_prompt:
            # Use direct prompt but still include content
            prompt = f"{prompt_template}\n\n{content}"
            logging.info("Using direct prompt with appended file content")
        else:
            prompt = prompt_template.format(content=content, filename=file_id)
        
        # Call Ollama
        logging.info(f"Calling model {model} for file {file_id}")
        response = call_ollama(prompt, model)
        
        if response:
            responses[file_id] = {
                "file_path": file_path,
                "prompt": prompt,
                "response": response,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
            processed += 1
            
            # Print response
            print(f"\n{'='*80}")
            print(f"File {i+1}/{total}: {file_path}")
            print(f"{'='*80}")
            # Display the prompt (truncated if too long)
            max_prompt_display_length = 500
            if len(prompt) > max_prompt_display_length:
                displayed_prompt = prompt[:max_prompt_display_length] + "... [truncated]"
            else:
                displayed_prompt = prompt
            print(f"Prompt sent to {model}:\n{'-'*40}\n{displayed_prompt}\n{'-'*40}")
            print(f"Response:\n{response}")
            
            # Display reproduction command
            print(f"\n{'*'*40}")
            if is_direct_prompt:
                # For direct prompt, just escape any double quotes
                escaped_prompt = prompt_template.replace('"', '\\"')
                cmd = f"python iterate_ollama.py --dir \"{os.path.dirname(file_path)}\" --filter \"{file_id}\" --prompt \"{escaped_prompt}\" --model \"{model}\""
            else:
                # For template mode, we need to escape the template for shell use
                # 1. Escape double quotes
                escaped_template = prompt_template.replace('"', '\\"')
                # 2. Replace actual newlines with the escape sequence \n
                escaped_template = escaped_template.replace('\n', '\\n')
                
                cmd = f"python iterate_ollama.py --dir \"{os.path.dirname(file_path)}\" --filter \"{file_id}\" --template \"{escaped_template}\" --model \"{model}\""
            
            if output_file != "ollama_responses.json":
                cmd += f" --output \"{output_file}\""
                
            print(f"To reproduce with this exact file (non-random):")
            print(cmd)
            print(f"{'*'*40}")
            print(f"{'='*80}")
            
            # Save after each successful call to preserve progress
            save_responses(responses)
        else:
            logging.warning(f"Failed to get response for file {file_path} with model {model}")
            skipped += 1
    
    logging.info(f"Processing complete: {processed}/{total} files processed, {skipped} skipped using model {model}")
    return responses

def read_prompt_file(file_path):
    """Read a prompt template from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read prompt file {file_path}: {e}")
        return None

def test_template_format():
    """Test function to validate template formatting and escaping."""
    test_template = "This is a template\nwith newlines\nand \"quotes\""
    
    # For the command line, we escape quotes and replace newlines with \n
    escaped = test_template.replace('"', '\\"').replace('\n', '\\n')
    print(f"Original template:\n{test_template}")
    print(f"Escaped for command line: {escaped}")
    
    # Create a shell-compatible command
    cmd = f'python iterate_ollama.py --template "{escaped}"'
    print(f"Command: {cmd}")
    
    # In Python, when this command runs through subprocess, argparse will get
    # the escaped string with literal \n, which needs to be converted back
    # This simulates what happens in the script when the command is executed
    template_arg = escaped
    # Convert the escape sequences to their actual characters
    import codecs
    try:
        # Use unicode_escape to convert \n to newlines, etc.
        reconstructed = codecs.decode(template_arg.encode(), 'unicode_escape')
        print(f"Reconstructed template:\n{reconstructed}")
        print(f"Matches original: {reconstructed == test_template}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Process prompts with Ollama")
    parser.add_argument("--file", type=str, help="File containing prompts (one per line)")
    parser.add_argument("--prompt", type=str, help="Single prompt to process. When used with --dir, the prompt is used directly and content is appended")
    parser.add_argument("--model", type=str, default="michaelborck/refuled", help="Model to use")
    parser.add_argument("--limit", type=int, help="Limit processing to this many prompts or files")
    parser.add_argument("--random", action="store_true", help="Process in random order")
    parser.add_argument("--dir", type=str, help="Directory containing files to process")
    parser.add_argument("--filter", type=str, help="Filter for files in directory (e.g. '*.md')")
    parser.add_argument("--template", type=str, help="Prompt template for processing files. Use {content} placeholder for file content and {filename} for filename")
    parser.add_argument("--template-file", type=str, help="File containing the prompt template to use")
    parser.add_argument("--output", type=str, help="Custom output file for responses (default: ollama_responses.json)")
    parser.add_argument("--recursive", action="store_true", help="Recursively search directories")
    args = parser.parse_args()
    
    # Set custom output file if specified
    global OUTPUT_FILE
    if args.output:
        OUTPUT_FILE = args.output
    
    # Check if Ollama is running
    if not check_ollama_status():
        logging.error("Ollama is not running. Please start Ollama and try again.")
        sys.exit(1)
    
    # Process directory of files
    if args.dir:
        # Check for prompt vs template options
        if args.prompt:
            # Use direct prompt
            template = args.prompt
            is_direct_prompt = True
            logging.info(f"Using direct prompt from command line with model {args.model}")
        elif args.template_file:
            # Use template from file
            template = read_prompt_file(args.template_file)
            is_direct_prompt = False
            if not template:
                logging.error(f"Could not read template from file {args.template_file}")
                sys.exit(1)
            logging.info(f"Using prompt template from file: {args.template_file} with model {args.model}")
        elif args.template:
            # Use template from command line
            template = args.template
            is_direct_prompt = False
            logging.info(f"Using prompt template from command line argument with model {args.model}")
        else:
            # Default template if none provided
            template = "Label this content:\n\n{content}"
            is_direct_prompt = False
            logging.info(f"Using default template with model {args.model}")
            
        files = find_files(args.dir, args.filter, args.limit, args.random, args.recursive)
        
        if not files:
            logging.error(f"No files found in {args.dir}")
            sys.exit(1)
            
        logging.info(f"Found {len(files)} files to process")
        process_files_with_prompt(files, template, args.model, is_direct_prompt, OUTPUT_FILE)
        return
    
    # Regular prompt processing
    prompts = []
    
    # Load prompts from file if specified
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
            logging.info(f"Loaded {len(prompts)} prompts from {args.file}")
        except Exception as e:
            logging.error(f"Failed to load prompts from file: {e}")
            sys.exit(1)
    # Use single prompt if specified
    elif args.prompt:
        prompts = [args.prompt]
        logging.info("Using single prompt from command line argument")
    # Check if prompt is provided via template file
    elif args.template_file:
        prompt = read_prompt_file(args.template_file)
        if not prompt:
            logging.error(f"Could not read prompt from file {args.template_file}")
            sys.exit(1)
        prompts = [prompt]
        logging.info(f"Using prompt from file: {args.template_file}")
    # Use fallback prompt if nothing specified
    else:
        prompts = ["Label this content."]
        logging.info("No prompts specified, using fallback prompt")
    
    # Process prompts
    iterate_prompts(prompts, args.model, args.limit, args.random)

if __name__ == "__main__":
    # Uncomment to test template formatting
    # test_template_format()
    # exit(0)
    main() 