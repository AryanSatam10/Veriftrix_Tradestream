import os
from dotenv import load_dotenv
from google import genai

# Load your API key from the backend folder
load_dotenv(dotenv_path="backend/.env")
api_key = os.getenv("GEMINI_API_KEY")

print("Initializing Client...")
client = genai.Client(api_key=api_key)

print("\n--- AVAILABLE MODELS ---")
try:
    # Ask Google directly what models are available to you
    for model in client.models.list():
        # Only print models that actually support generating content
        if 'generateContent' in model.supported_generation_methods:
            print(f"- {model.name}")
except Exception as e:
    print(f"Failed to list models: {e}")