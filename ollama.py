import requests
import json
from config_reader import config

ollama_url = config.ollama_token.get_secret_value()+"/api/generate"

headers = {"Content-Type": "application/json"}

def OllamaAnswer(message):
    try:
        data = {
        "model": "gpt-oss:20b",
        "prompt": "Here's user's message: " + message + ". Give a short response.",
        "stream": False,
        "options": {
            "num_thread": 8,
            "num_ctx": 2024
            }
        }
        response = requests.post(ollama_url, headers=headers, data=json.dumps(data))
        response.raise_for_status() 
        result = response.json()
        return result['response']
    except requests.exceptions.RequestException as e:
        return "Ошибка подключения"