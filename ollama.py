import requests
import json
from config_reader import config
import asyncio

ollama_url = config.ollama_token.get_secret_value() + "/api/generate"

headers = {"Content-Type": "application/json"}

async def OllamaAnswer(message, prompt = None):
    try:
        data = {
            "model": "gpt-oss:20b",
            "prompt": prompt or "Here's user's message: " + message + ". Give a short response.",
            "stream": False,
            "options": {
                "num_thread": 8,
                "num_ctx": 2024
            }
        }
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(ollama_url, headers=headers, data=json.dumps(data))
        )
        response.raise_for_status() 
        result = response.json()
        return result['response']
    except requests.exceptions.RequestException as e:
        return "Ошибка подключения"