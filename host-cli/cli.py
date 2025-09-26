import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from fastmcp import Client as FastMCPClient
from colorama import Fore, Style, init
import anthropic

init(autoreset=True)
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# =========================
# MCP Manager
# =========================
class MCPManager:
    def __init__(self):
        self.servers = {}   # {alias: {"url": str}}
        self.tools = []     # merged tools with server alias

    async def add_server(self, alias: str, target: str):
        """Register an MCP server (auto-detect http or stdio)."""
        self.servers[alias] = {"url": target}
        client = FastMCPClient(target)   # no transport arg
        async with client:
            tools = await client.list_tools()
            for t in tools:
                # Modify the schema to match what Claude expects
                modified_schema = self._modify_tool_schema(t.name, getattr(t, "input_schema", {"type": "object"}))
                
                self.tools.append({
                    "server": alias,
                    "name": t.name,
                    "description": t.description,
                    "input_schema": modified_schema  # Use modified schema
                })

    def _modify_tool_schema(self, tool_name: str, original_schema: dict) -> dict:
        """Modify tool schemas to match what Claude expects to send."""
        
        # Define schema modifications for specific tools
        schema_modifications = {
            # Flight booking tools - add common parameters Claude might use
            'search_cheapest_flights': {
                'type': 'object',
                'properties': {
                    'origin': {'type': 'string', 'description': 'Origin airport code'},
                    'destination': {'type': 'string', 'description': 'Destination airport code'},
                    'limit': {'type': 'integer', 'description': 'Number of results', 'default': 10},
                    'max_stops': {'type': 'integer', 'description': 'Maximum stops', 'default': 2}
                }
            },
            'search_flights': {
                'type': 'object', 
                'properties': {
                    'origin': {'type': 'string', 'description': 'Origin city'},
                    'destination': {'type': 'string', 'description': 'Destination city'},
                    'from_city': {'type': 'string', 'description': 'From city'},
                    'to_city': {'type': 'string', 'description': 'To city'},
                    'limit': {'type': 'integer', 'description': 'Number of results', 'default': 10},
                    'max_price': {'type': 'number', 'description': 'Maximum price', 'default': 0},
                    'min_price': {'type': 'number', 'description': 'Minimum price', 'default': 0},
                    'airline': {'type': 'string', 'description': 'Airline filter', 'default': ''},
                    'class_type': {'type': 'string', 'description': 'Class type filter', 'default': ''},
                    'max_stops': {'type': 'integer', 'description': 'Maximum stops', 'default': -1}
                }
            },
            # Git tools - Claude expects 'directory' parameter
            'git_init': {
                'type': 'object',
                'properties': {
                    'directory': {'type': 'string', 'description': 'Directory to initialize git repo in', 'default': '.'}
                }
            },
            'git_add': {
                'type': 'object',
                'properties': {
                    'directory': {'type': 'string', 'description': 'Repository directory', 'default': '.'},
                    'file_path': {'type': 'string', 'description': 'File to add', 'default': '.'}
                }
            },
            'git_commit': {
                'type': 'object',
                'properties': {
                    'directory': {'type': 'string', 'description': 'Repository directory', 'default': '.'},
                    'message': {'type': 'string', 'description': 'Commit message', 'default': 'Automated commit'}
                }
            },
            'git_status': {
                'type': 'object',
                'properties': {
                    'directory': {'type': 'string', 'description': 'Repository directory', 'default': '.'}
                }
            },
            # File operations - Claude expects 'path' parameter
            'create_directory': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Directory path to create'}
                }
            },
            'read_file': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'File path to read'}
                }
            },
            'write_file': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'File path to write'},
                    'content': {'type': 'string', 'description': 'Content to write'}
                }
            },
            'list_directory': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Directory path to list', 'default': '.'}
                }
            }
        }
        
        return schema_modifications.get(tool_name, original_schema)

    def debug_tool_schemas(self):
        """Print all tool schemas for debugging."""
        print(Fore.CYAN + "\n=== DEBUGGING TOOL SCHEMAS ===")
        for tool in self.tools:
            print(f"\n{Fore.YELLOW}=== {tool['server']}_{tool['name']} ===")
            print(f"{Fore.WHITE}Description: {tool['description']}")
            print(f"{Fore.MAGENTA}Schema: {json.dumps(tool['input_schema'], indent=2)}")
        print(Fore.CYAN + "\n=== END SCHEMAS DEBUG ===\n")

    async def call_tool(self, server_alias: str, tool_name: str, params: dict):
        """Route a tool call to the correct MCP server."""
        server = self.servers.get(server_alias)
        if not server:
            raise ValueError(f"No such MCP server: {server_alias}")
        
        # Apply parameter mapping if needed
        mapped_params = self._map_parameters(tool_name, params)
        
        client = FastMCPClient(server["url"])  # auto-detect again
        async with client:
            return await client.call_tool(tool_name, mapped_params)
        
    def _map_parameters(self, tool_name: str, params: dict) -> dict:
        """Map parameters to match MCP server expectations."""
        # Define parameter mappings for specific tools
        parameter_mappings = {
            # File operations
            'create_directory': {'path': 'directory_path'},
            'write_file': {'path': 'file_path'},
            'read_file': {'path': 'file_path'},
            'delete_file': {'path': 'file_path'},
            'list_directory': {'path': 'directory_path'},
            
            # Git commands - map Claude's 'directory' to server's 'repo_path'
            'git_init': {'directory': 'repo_path'},
            'git_add': {'directory': 'repo_path'},
            'git_commit': {'directory': 'repo_path'},
            'git_status': {'directory': 'repo_path'},
            'git_log': {'directory': 'repo_path'},
            'git_branch': {'directory': 'repo_path'},
            'git_diff': {'directory': 'repo_path'},
            
            # Flight search - map common parameters
            'search_cheapest_flights': {
                'origin': 'from_city',
                'destination': 'to_city'
            },
            'search_flights': {
                'origin': 'from_city', 
                'destination': 'to_city'
            }
        }
        
        mapping = parameter_mappings.get(tool_name, {})
        mapped_params = {}
        
        for key, value in params.items():
            # Use mapped parameter name if it exists, otherwise use original
            mapped_key = mapping.get(key, key)
            if mapped_key is not None:  # Only add if mapping isn't explicitly None
                mapped_params[mapped_key] = value
            
        return mapped_params

    def get_tools_for_claude(self):
        """Format tools into Claude's schema with server prefix."""
        tools_for_claude = []
        for t in self.tools:
            # Use underscore instead of double colon to comply with Claude's naming pattern
            claude_tool_name = f"{t['server']}_{t['name']}"
            tools_for_claude.append({
                "name": claude_tool_name,
                "description": f"[{t['server']}] {t['description']}",  # Add server context to description
                "input_schema": t["input_schema"]
            })
        return tools_for_claude

    def parse_tool_name(self, claude_tool_name: str):
        """Parse Claude tool name back to server alias and original tool name."""
        # Find the first underscore to split server alias from tool name
        parts = claude_tool_name.split('_', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        # Fallback: assume it's just the tool name with no server prefix
        return None, claude_tool_name

# =========================
# CLI Helpers
# =========================
def print_heading(heading: str):
    print(Fore.CYAN + Style.BRIGHT + f"=== {heading} ===")

def print_error(message: str):
    print(Fore.RED + f"[ERROR] {message}")

def print_info(message: str):
    print(Fore.GREEN + f"[INFO] {message}")

def print_function_call(tool_name, params):
    print(Fore.YELLOW + f"[Claude → {tool_name}] Params: {params}")

def print_tool_result(result):
    print(Fore.MAGENTA + f"[TOOL RESULT] {result}")

# =========================
# Setup MCP Manager
# =========================
async def setup_mcp():
    manager = MCPManager()
    # Updated paths - filesystem server should be in same directory
    await manager.add_server("local", "../filesystem/mcp_server.py")

    await manager.add_server("git", "../Repository/servers/src/git/mcp_server.py")
    
    # await manager.add_server("game", "../filesystem/mcp_server.py")

    await manager.add_server("game", "../Repository/MCP_VIDEOGAMES_REC_INFO/server/mcp_server.py")

    await manager.add_server("jpgame", "../Repository/MCP_VideogameStats_Server/games/server.py")

    # Optional: comment out the remote server if you don't have access
    await manager.add_server("remote", "https://flightbookingU.fastmcp.app/mcp")


    return manager

# =========================
# Main Loop
# =========================
async def main():
    try:
        manager = await setup_mcp()
        
        # DEBUG: Print tool schemas to see what parameters are expected
        manager.debug_tool_schemas()  # Add this line for debugging
        
        tools = manager.get_tools_for_claude()
        
        print_heading("Chat CLI with Claude + MCPManager")
        print_info(f"Loaded {len(tools)} tools from MCP servers")
        print_info("Type 'exit' to quit, 'debug' to see tool schemas again.\n")

        history = []

        while True:
            user_input = input(Fore.WHITE + "You: ")
            if not user_input or user_input.lower() == "exit":
                print_info("Session ended")
                break
            elif user_input.lower() == "debug":
                manager.debug_tool_schemas()
                continue

            history.append({"role": "user", "content": user_input})

            try:
                resp = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    tools=tools,
                    messages=history
                )

                handled = False
                assistant_content = []
                tool_results = []
                
                # Process all content parts
                for part in resp.content:
                    if part.type == "text":
                        assistant_content.append(part)
                    elif part.type == "tool_use":
                        assistant_content.append(part)
                        
                        # Parse server alias and tool name from Claude's tool name
                        server_alias, tool_name = manager.parse_tool_name(part.name)
                        params = part.input

                        print_function_call(part.name, params)

                        if server_alias:
                            raw_result = await manager.call_tool(server_alias, tool_name, params)
                        else:
                            print_error(f"Could not parse server alias from tool name: {part.name}")
                            continue
                        
                        # Extract the actual result from the CallToolResult object
                        if hasattr(raw_result, 'content') and raw_result.content:
                            # Get the first content item (usually TextContent)
                            first_content = raw_result.content[0]
                            if hasattr(first_content, 'text'):
                                try:
                                    # Try to parse as JSON first
                                    tool_result = json.loads(first_content.text)
                                except json.JSONDecodeError:
                                    # If not JSON, use as plain text
                                    tool_result = {"response": first_content.text}
                            else:
                                tool_result = {"response": str(first_content)}
                        elif hasattr(raw_result, 'data') and raw_result.data:
                            # Use the structured data if available
                            tool_result = raw_result.data
                        else:
                            # Fallback to string representation
                            tool_result = {"response": str(raw_result)}

                        print_tool_result(tool_result)
                        
                        # Collect tool result for batch processing
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": part.id,
                            "content": json.dumps(tool_result)
                        })
                        handled = True

                # If we had tool calls, process them
                if handled:
                    # Add assistant message with tool calls
                    history.append({"role": "assistant", "content": assistant_content})
                    
                    # Add tool results as user message
                    history.append({"role": "user", "content": tool_results})

                    # Get Claude's final response
                    followup = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        tools=tools,
                        messages=history
                    )
                    
                    # Extract text response
                    text_response = "".join([p.text for p in followup.content if p.type == "text"])
                    
                    # Handle empty responses
                    if not text_response.strip():
                        text_response = "Task completed successfully."
                    
                    print(Fore.BLUE + f"Claude: {text_response}\n")
                    history.append({"role": "assistant", "content": text_response})

                if not handled:
                    text_reply = "".join([p.text for p in resp.content if p.type == "text"])
                    print(Fore.BLUE + f"Claude: {text_reply}\n")
                    history.append({"role": "assistant", "content": text_reply})

            except Exception as e:
                print_error(f"Error with Claude: {e}")
                # Continue the loop instead of crashing
                continue
                
    except Exception as e:
        print_error(f"Failed to setup MCP manager: {e}")
        print_info("Make sure the filesystem MCP server is properly set up")

if __name__ == "__main__":
    asyncio.run(main())