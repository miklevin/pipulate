import requests
import re

def parse_version(version_string):
    return [int(x) if x.isdigit() else x for x in re.findall(r'\d+|\D+', version_string)]

def compare_versions(v1, v2):
    v1_parts = parse_version(v1)
    v2_parts = parse_version(v2)
    return (v1_parts > v2_parts) - (v1_parts < v2_parts)

def get_best_llama_model(models):
    llama_models = [model for model in models if model.lower().startswith('llama')]
    if not llama_models:
        return None

    # First, check for llama3.1:latest
    if "llama3.1:latest" in llama_models:
        return "llama3.1:latest"

    def key_func(model):
        # Split the model name and version
        parts = model.split(':')
        base_name = parts[0]
        version = parts[1] if len(parts) > 1 else ''

        # Extract the version number from the base name
        base_version = re.search(r'llama(\d+(?:\.\d+)*)', base_name.lower())
        base_version = base_version.group(1) if base_version else ''

        # Prioritize 'latest' tag, then base version, then additional version info
        return (-1 if version == 'latest' else 1, 
                parse_version(base_version), 
                parse_version(version))

    return min(llama_models, key=key_func)

def check_ollama(timeout=10):
    try:
        print("Requesting available models...")
        models_response = requests.get("http://localhost:11434/api/tags", timeout=timeout)
        models_response.raise_for_status()
        
        models = models_response.json()['models']
        print("Available models:")
        for model in models:
            print(f"- {model['name']}")
        
        model_names = [model['name'] for model in models]
        
        chosen_model = get_best_llama_model(model_names) or model_names[0]
        
        print(f"Chosen model: {chosen_model}")
        
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
