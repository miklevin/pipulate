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

    def key_func(model):
        # Split the model name and version
        parts = model.split(':')
        base_name = parts[0]
        version = parts[1] if len(parts) > 1 else ''

        # Extract the version number from the base name
        base_version = re.search(r'llama(\d+(?:\.\d+)*)', base_name.lower())
        base_version = base_version.group(1) if base_version else '0'

        # Prioritize based on base version, then 'latest' tag
        return (parse_version(base_version),
                1 if version == 'latest' else 0,
                parse_version(version))

    return max(llama_models, key=key_func)

def check_ollama(keyword="Pipulate", timeout=10):
    try:
        # print("Requesting available models...")
        models_response = requests.get("http://localhost:11434/api/tags", timeout=timeout)
        models_response.raise_for_status()
        
        models = models_response.json()['models']
        # print("Available models:")
        # for model in models:
        #     print(f"- {model['name']}")
        
        model_names = [model['name'] for model in models]
        
        chosen_model = get_best_llama_model(model_names) or model_names[0]
        
        # print(f"Chosen model: {chosen_model}")
        
        # print("Sending chat request...")
        chat_response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": chosen_model,
                "messages": [{"role": "user", "content": f"Say 'Ready to {keyword}!' as a short, clever one-liner."}],
                "stream": False
            },
            timeout=timeout
        )
        chat_response.raise_for_status()
        
        response_content = chat_response.json()['message']['content']
        # Remove surrounding quotes if present
        response_content = response_content.strip('"')
        
        return f"Using model {chosen_model}\n{response_content}"
    except requests.exceptions.Timeout:
        return f"Error: Connection to Ollama server timed out after {timeout} seconds. The server might be busy or slow to respond."
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to the Ollama server. Is it running?"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama server: {e}"

if __name__ == "__main__":
    import sys
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Pipulate"
    result = check_ollama(keyword)
    print(result)
