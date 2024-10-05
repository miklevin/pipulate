import requests
import re

def parse_version(version_string):
    return [int(x) if x.isdigit() else x for x in re.findall(r'\d+|\D+', version_string)]

def get_best_llama_model(models):
    llama_models = [model for model in models if model.lower().startswith('llama')]
    if not llama_models:
        return None

    def key_func(model):
        parts = model.split(':')
        base_name = parts[0]
        version = parts[1] if len(parts) > 1 else ''
        base_version = re.search(r'llama(\d+(?:\.\d+)*)', base_name.lower())
        base_version = base_version.group(1) if base_version else '0'
        return (parse_version(base_version),
                1 if version == 'latest' else 0,
                parse_version(version))

    return max(llama_models, key=key_func)

def get_available_models():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        response.raise_for_status()
        return [model['name'] for model in response.json()['models']]
    except requests.exceptions.RequestException:
        return []

def get_best_model():
    available_models = get_available_models()
    return get_best_llama_model(available_models) or (available_models[0] if available_models else "llama2")
