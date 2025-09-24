import os
import sys
import json
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
from fastmcp import Client as FastMCPClient
from colorama import Fore, Back, Style, init

init(autoreset=True)

# =========================
# CONFIG
# =========================
load_dotenv()
logs = []

LOCAL_URL = os.getenv("LOCAL_URL", "http://127.0.0.1:8000")
REMOTE_URL = os.getenv("REMOTE_URL", "https://flightbookingU.fastmcp.app/mcp")

# File path for the chat log
CHAT_LOG_FILE = "chat_log.json"

def print_heading(heading: str):
    print(Fore.CYAN + Style.BRIGHT + f"=== {heading} ===")

def print_error(message: str):
    print(Fore.RED + f"[ERROR] {message}")

def print_info(message: str):
    print(Fore.GREEN + f"[INFO] {message}")

def print_function_call(tool_name, params):
    print(Fore.YELLOW + f"[Gemini → {tool_name}] Params: {params}")

def print_tool_result(result):
    print(Fore.MAGENTA + f"[TOOL RESULT] {result}")

async def get_mcp_tools(url: str):
    """List available MCP tools from server."""
    client = FastMCPClient(url)
    async with client:
        return await client.list_tools()

async def call_mcp_tool(tool: str, params: dict, url: str):
    """Call an MCP server tool (local or remote)."""
    client = FastMCPClient(url)
    async with client:
        return await client.call_tool(tool, params)

def load_chat_log():
    """Load chat log from file."""
    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'r') as file:
            return json.load(file)
    return []

def save_chat_log(logs):
    """Save chat log to file."""
    with open(CHAT_LOG_FILE, 'w') as file:
        json.dump(logs, file, indent=4)

# =========================
# Load MCP tools dynamically
# =========================
print("Fetching tool lists from MCP servers...")
local_tools = asyncio.run(get_mcp_tools(LOCAL_URL))
remote_tools = asyncio.run(get_mcp_tools(REMOTE_URL))

# Gemini tool schemas with tool names from MCP

tools = [
    genai.protos.FunctionDeclaration(
        name="call_mcp_local",
        description="Call a tool on the LOCAL MCP server (filesystem/git).",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "tool_name": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    enum=[t.name for t in local_tools],
                    description="The tool name to call on the local server."
                ),
                "params": genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    description="Parameters for the tool call"
                )
            },
            required=["tool_name"]
        )
    ),
]

print("Local tools:", [t.name for t in local_tools])
print("Remote tools:", [t.name for t in remote_tools])

# =========================
# Init Gemini
# =========================
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash", tools=tools)
    chat = model.start_chat()
except Exception as e:
    print(f"Error initializing Gemini: {e}")
    sys.exit(1)

# =========================
# CLI Loop
# =========================
print_heading("Chat CLI with Gemini + MCP Function Calling")
print_info("Type 'exit' to quit.\n")

# Load chat log before starting
chat_log = load_chat_log()
for entry in chat_log:
    print(Fore.WHITE + f"You: {entry['user_input']}")
    print(Fore.BLUE + f"Gemini: {entry['gemini_response']}")

while True:
    user_input = input(Fore.WHITE + "You: ")
    if not user_input or user_input.lower() == "exit":
        print_info("Session ended")
        break

    try:
        resp = chat.send_message(user_input)

        handled = False
        for part in resp.candidates[0].content.parts:
            if part.function_call:
                fn = part.function_call
                tool_name_from_gemini = fn.args.get("tool_name")
                params_from_gemini = fn.args.get("params", {})

                print_function_call(tool_name_from_gemini, params_from_gemini)

                # Determine whether to call local or remote MCP
                if fn.name == "call_mcp_local":
                    url = LOCAL_URL
                elif fn.name == "call_mcp_remote":
                    url = REMOTE_URL
                else:
                    print_error(f"Unknown function: {fn.name}")
                    continue

                # Call MCP tool
                tool_result = asyncio.run(call_mcp_tool(tool_name_from_gemini, params_from_gemini, url))

                if not isinstance(tool_result, dict):
                    tool_result = {"response": str(tool_result)}

                # Send back result
                followup = chat.send_message({
                    "function_response": {
                        "name": fn.name,
                        "response": tool_result
                    }
                })
                print_tool_result(followup.text)
                handled = True
                break

        if not handled:
            print(Fore.BLUE + f"Gemini: {resp.text}\n")

        # Save chat log
        chat_log.append({
            "user_input": user_input,
            "gemini_response": resp.text
        })
        save_chat_log(chat_log)

    except Exception as e:
        print_error(f"Error with Gemini: {e}")
