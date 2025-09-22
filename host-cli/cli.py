import os
from google import genai
from dotenv import load_dotenv
import json
from fastmcp import MCPClient
import asyncio

# Load environment variables from a .env file
load_dotenv()

logs = []

# Instantiate the client and pass the API key explicitly
try:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print("Error:", e)
    print("Please make sure you have a valid GOOGLE_API_KEY set in your environment variables.")
    exit()


# Start a chat session
chat = client.chats.create(model="gemini-2.0-flash")

print("=== Chat CLI con Gemini (Python) ===")
print("Escribe 'exit' para salir.\n")

while True:
    user_input = input("> ")
    if not user_input or user_input.lower() == "exit":
        break

    try:
        resp = chat.send_message(user_input)
        text = resp.text
        print("\nGemini:", text, "\n")
        logs.append({"user": user_input, "assistant": text})

        # al final de la sesión guardas un array JSON
        with open("chat_log.json", "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2) 
    except Exception as e:
        print("Error:", e)