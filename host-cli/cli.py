# host-cli/cli.py
import os
import sys
import json
import asyncio
import pathlib
from dotenv import load_dotenv
from google import genai

# Cliente oficial MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
logs = []

# Inicializa Gemini
try:
    gclient = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    chat = gclient.chats.create(model="gemini-2.0-flash")
except Exception as e:
    print("Error inicializando Gemini:", e)
    sys.exit(1)

# Ruta ABSOLUTA al servidor MCP (está en ../filesystem/mcp_server.py)
SERVER_PATH = pathlib.Path(__file__).resolve().parent.parent / "filesystem" / "mcp_server.py"
SERVER_PATH = SERVER_PATH.resolve()
if not SERVER_PATH.exists():
    print(f"Error: no se encontró el servidor MCP en {SERVER_PATH}")
    sys.exit(1)

async def call_mcp_tool(tool: str, params: dict):
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        cwd=str(SERVER_PATH.parent),
        env={
            "AIRTRAIN_NO_TELEMETRY": "1",  # silencia telemetría
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            return await session.call_tool(tool, params)

print("=== Chat CLI con Gemini + MCP ===")
print("Escribe 'exit' para salir.")
print("Comandos MCP:")
print('  :mcp <tool> {"k":"v"}')
print('  Ej.: :mcp list_directory {"directory_path":"."}\n')

while True:
    user_input = input("> ")
    if not user_input or user_input.lower() == "exit":
        break

    # --- Comando MCP ---
    if user_input.startswith(":mcp"):
        try:
            parts = user_input.split(maxsplit=2)
            if len(parts) < 2:
                print("Uso: :mcp tool {json_params}")
                continue
            tool = parts[1]
            params = json.loads(parts[2]) if len(parts) > 2 else {}
            result = asyncio.run(call_mcp_tool(tool, params))
            print("\n[MCP result]\n", result, "\n")
            logs.append({"user": user_input, "mcp_result": result})
        except json.JSONDecodeError:
            print('JSON inválido. Ejemplo: :mcp list_directory {"directory_path":"."}')
        except Exception as e:
            print("Error al invocar MCP:", e)
        # guarda log y sigue
        with open("chat_log.json", "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        continue

    # --- Flujo normal con Gemini ---
    try:
        resp = chat.send_message(user_input)
        text = resp.text
        print("\nGemini:", text, "\n")
        logs.append({"user": user_input, "assistant": text})
    except Exception as e:
        print("Error con Gemini:", e)

    # --- Guardar logs ---
    try:
        with open("chat_log.json", "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error guardando logs:", e)

print("=== Sesión terminada ===")
