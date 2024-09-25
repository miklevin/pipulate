import requests
import re

def parse_model_size(model_name):
    match = re.search(r'(\d+)([bm])', model_name.lower())
    if match:
        size, unit = match.groups()
        size = int(size)
        if unit == 'b':
            return size * 1000000000
        elif unit == 'm':
            return size * 1000000
    return float('inf')  # Return infinity for models we can't parse, so they're least preferred

def check_ollama(timeout=10):
    try:
        # Check available models
        print("Requesting available models...")
        models_response = requests.get("http://localhost:11434/api/tags", timeout=timeout)
        models_response.raise_for_status()
        
        models = models_response.json()['models']
        print("Available models:")
        for model in models:
            print(f"- {model['name']}")
        
        model_names = [model['name'] for model in models]
        
        # First, look for "llama3.1:latest"
        if "llama3.1:latest" in model_names:
            chosen_model = "llama3.1:latest"
        else:
            # If not found, look for other llama models with "latest" tag
            llama_latest_models = [name for name in model_names if name.startswith('llama') and name.endswith(':latest')]
            if llama_latest_models:
                chosen_model = llama_latest_models[0]
            elif "llama3.1" in model_names:
                # If no llama:latest models, use base "llama3.1"
                chosen_model = "llama3.1"
            else:
                # If no llama models, choose any model with "latest" tag
                latest_models = [name for name in model_names if name.endswith(':latest')]
                chosen_model = latest_models[0] if latest_models else model_names[0]
        
        print(f"Chosen model: {chosen_model}")
        
        # Test the chosen model
        print("Sending chat request...")
        chat_response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": chosen_model,
                "messages": [{"role": "user", "content": "Say 'Ready to pipulate!' in a clever way."}],
                "stream": False
            },
            timeout=timeout
        )
        chat_response.raise_for_status()
        
        return f"Using model: {chosen_model}\n" + chat_response.json()['message']['content']
    except requests.exceptions.Timeout:
        return f"Error: Connection to Ollama server timed out after {timeout} seconds. The server might be busy or slow to respond."
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to the Ollama server. Is it running?"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama server: {e}"

if __name__ == "__main__":
    print("Checking Ollama connectivity...")
    result = check_ollama()
    print(result)
