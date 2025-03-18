#!/usr/bin/env python3

import tiktoken
from pathlib import Path
import sys

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count the number of tokens in a text string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def format_number(num: int) -> str:
    """Format a number with commas and calculate cost."""
    # GPT-4 costs approximately $0.03 per 1K tokens
    cost = (num / 1000) * 0.03
    return f"{num:,} tokens (≈${cost:.2f} at GPT-4 rates)"

def main():
    # Get the current directory
    current_dir = Path(__file__).parent
    
    # Find all Python files
    python_files = list(current_dir.glob("*.py"))
    
    print(f"\nAnalyzing Python files in: {current_dir}\n")
    
    total_tokens = 0
    file_tokens = {}
    
    # Process each file
    for file_path in python_files:
        try:
            content = file_path.read_text(encoding='utf-8')
            tokens = count_tokens(content)
            file_tokens[file_path.name] = tokens
            total_tokens += tokens
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    # Print results in a table format
    print("Token Count by File:")
    print("-" * 50)
    print(f"{'File':<30} {'Tokens':<20}")
    print("-" * 50)
    
    # Sort files by token count
    for file_name, tokens in sorted(file_tokens.items(), key=lambda x: x[1], reverse=True):
        print(f"{file_name:<30} {format_number(tokens):<20}")
    
    print("-" * 50)
    print(f"Total:{' '*24} {format_number(total_tokens)}")

if __name__ == "__main__":
    try:
        import tiktoken
    except ImportError:
        print("\nError: tiktoken package not found.")
        print("Please install it using:")
        print("pip install tiktoken\n")
        sys.exit(1)
        
    main()