import os
from dotenv import load_dotenv
from google import genai

load_dotenv(dotenv_path="backend/.env")
api_key = os.getenv("GEMINI_API_KEY")

print("Initializing Client...")
client = genai.Client(api_key=api_key)

print("\n--- AVAILABLE MODELS ---")
try:
    for model in client.models.list():
        print(f"- {model.name}")
except Exception as e:
    print(f"Failed to list models: {e}")