import requests
import json

def chat_with_ollama(model, messages):
    url = "http://localhost:11434/api/chat"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    
    if response.status_code == 200:
        return response.json()['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

# Example usage
model = "llama3.1"  # or whatever model you have installed
conversation = [
    {"role": "user", "content": "What is the capital of France?"},
]

while True:
    response = chat_with_ollama(model, conversation)
    print("Assistant:", response)
    
    conversation.append({"role": "assistant", "content": response})
    
    user_input = input("You: ")
    if user_input.lower() in ['quit', 'exit', 'bye']:
        break
    
    conversation.append({"role": "user", "content": user_input})

print("Conversation ended.")
