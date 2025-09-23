import os
import sys
import json
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai
from fastmcp import Client as FastMCPClient

# =========================
# CONFIG
# =========================
load_dotenv()
logs = []

LOCAL_URL = os.getenv("LOCAL_URL", "http://localhost:8080/mcp")
REMOTE_URL = os.getenv("REMOTE_URL", "https://flightbookingU.fastmcp.app/mcp")

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
        genai.protos.FunctionDeclaration(
        name="call_mcp_remote",
        description="Call a tool on the REMOTE MCP server (flight booking).",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "tool_name": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    enum=[t.name for t in remote_tools],
                    description="The tool name to call."
                ),
                "params": genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    description="Parameters for the tool call. "
                                "For example, 'search_cheapest_flights' only accepts {limit, max_stops}."
                )
            },
            required=["tool_name"]
        )
    )
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
print("=== Chat CLI with Gemini + MCP Function Calling ===")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("> ")
    if not user_input or user_input.lower() == "exit":
        break

    try:
        resp = chat.send_message(user_input)

        handled = False
        for part in resp.candidates[0].content.parts:
            if part.function_call:
                fn = part.function_call
                tool_name_from_gemini = fn.args.get("tool_name")
                params_from_gemini = fn.args.get("params", {})

                print(f"[Gemini → {fn.name}] tool={tool_name_from_gemini} params={params_from_gemini}")

                if fn.name == "call_mcp_local":
                    url = LOCAL_URL
                elif fn.name == "call_mcp_remote":
                    url = REMOTE_URL
                else:
                    print(f"Unknown function: {fn.name}")
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
                print("\nGemini (after tool):", followup.text, "\n")
                handled = True
                break

        if not handled:
            print("\nGemini:", resp.text, "\n")

    except Exception as e:
        print(f"Error with Gemini: {e}")

print("=== Session ended ===")
