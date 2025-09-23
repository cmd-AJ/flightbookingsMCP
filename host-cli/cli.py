import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from google import genai
from fastmcp import Client as FastMCPClient

load_dotenv()
logs = []

# Inicializa Gemini
try:
    gclient = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    chat = gclient.chats.create(model="gemini-2.0-flash")
except Exception as e:
    print("Error inicializando Gemini:", e)
    sys.exit(1)

LOCAL_URL = os.getenv("LOCAL_URL", "http://localhost:8080/mcp")
REMOTE_URL = os.getenv("REMOTE_URL", "https://flightbookingU.fastmcp.app/mcp")

async def call_mcp_tool(tool: str, params: dict, url: str):
    client = FastMCPClient(url)
    async with client:
        return await client.call_tool(tool, params)

print("=== Chat CLI con Gemini + MCP ===")
print("Comandos:")
print('  :mcp <tool> {"k":"v"}          → llama al servidor local')
print('  :mcp-remote <tool> {"k":"v"}   → llama al servidor remoto\n')

while True:
    user_input = input("> ")
    if not user_input or user_input.lower() == "exit":
        break

    # --- LOCAL ---
    if user_input.startswith(":mcp "):
        try:
            parts = user_input.split(maxsplit=2)
            tool = parts[1]
            params = json.loads(parts[2]) if len(parts) > 2 else {}
            result = asyncio.run(call_mcp_tool(tool, params, LOCAL_URL))
            print("\n[MCP Local result]\n", result, "\n")
        except Exception as e:
            print("Error MCP local:", e)
        continue

    # --- REMOTO ---
    if user_input.startswith(":mcp-remote "):
        try:
            parts = user_input.split(maxsplit=2)
            tool = parts[1]
            params = json.loads(parts[2]) if len(parts) > 2 else {}
            result = asyncio.run(call_mcp_tool(tool, params, REMOTE_URL))
            print("\n[MCP Remote result]\n", result, "\n")
        except Exception as e:
            print("Error MCP remoto:", e)
        continue

    # --- Normal Gemini ---
    try:
        resp = chat.send_message(user_input)
        print("\nGemini:", resp.text, "\n")
    except Exception as e:
        print("Error con Gemini:", e)

print("=== Sesión terminada ===")
