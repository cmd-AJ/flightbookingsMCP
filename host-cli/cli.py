import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import Client as FastMCPClient
from colorama import Fore, Style, init
import anthropic

init(autoreset=True)
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# =========================
# Chat Log Manager
# =========================
class ChatLogManager:
    def __init__(self, logs_directory="chat_logs"):
        self.logs_dir = Path(logs_directory)
        self.logs_dir.mkdir(exist_ok=True)
        self.current_session_file = None
        
    def create_new_session(self, session_name=None):
        """Create a new chat session file."""
        if not session_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"chat_{timestamp}"
        
        self.current_session_file = self.logs_dir / f"{session_name}.json"
        
        # Initialize with metadata
        session_data = {
            "session_name": session_name,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "message_count": 0,
            "history": []
        }
        
        self.save_session_data(session_data)
        return session_name
    
    def load_session(self, session_name):
        """Load an existing chat session."""
        session_file = self.logs_dir / f"{session_name}.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_name} not found")
        
        self.current_session_file = session_file
        with open(session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_session_data(self, session_data):
        """Save session data to current session file."""
        if not self.current_session_file:
            raise ValueError("No active session")
        
        session_data["last_updated"] = datetime.now().isoformat()
        session_data["message_count"] = len(session_data["history"])
        
        with open(self.current_session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    
    def append_message(self, role, content, metadata=None):
        """Append a message to the current session."""
        if not self.current_session_file:
            raise ValueError("No active session")
        
        # Load current data
        session_data = self.load_current_session()
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        session_data["history"].append(message)
        self.save_session_data(session_data)
    
    def load_current_session(self):
        """Load current session data."""
        if not self.current_session_file or not self.current_session_file.exists():
            raise ValueError("No active session or session file missing")
        
        with open(self.current_session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_sessions(self):
        """List all available chat sessions."""
        sessions = []
        for file_path in self.logs_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append({
                        "name": data.get("session_name", file_path.stem),
                        "created_at": data.get("created_at", "Unknown"),
                        "last_updated": data.get("last_updated", "Unknown"),
                        "message_count": data.get("message_count", 0),
                        "file": file_path.name
                    })
            except (json.JSONDecodeError, KeyError):
                # Skip invalid files
                continue
        
        return sorted(sessions, key=lambda x: x["last_updated"], reverse=True)
    
    def delete_session(self, session_name):
        """Delete a chat session."""
        session_file = self.logs_dir / f"{session_name}.json"
        if session_file.exists():
            session_file.unlink()
            return True
        return False
    
    def export_session(self, session_name, format="txt"):
        """Export session to different formats."""
        session_data = self.load_session(session_name)
        
        if format == "txt":
            output_file = self.logs_dir / f"{session_name}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Chat Session: {session_data['session_name']}\n")
                f.write(f"Created: {session_data['created_at']}\n")
                f.write(f"Messages: {session_data['message_count']}\n")
                f.write("=" * 50 + "\n\n")
                
                for msg in session_data['history']:
                    timestamp = msg.get('timestamp', '')
                    role = msg['role'].upper()
                    content = msg['content']
                    
                    if isinstance(content, list):
                        # Handle complex content (tool calls, etc.)
                        content_str = json.dumps(content, indent=2)
                    else:
                        content_str = str(content)
                    
                    f.write(f"[{timestamp}] {role}: {content_str}\n\n")
        
        return output_file

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

def print_session_info(session_name, message_count):
    print(Fore.CYAN + f"[SESSION: {session_name}] Messages: {message_count}")

# =========================
# Session Management Commands
# =========================
def handle_session_commands(command_parts, log_manager):
    """Handle session-related commands."""
    if len(command_parts) < 2:
        print_info("Session commands: /session new [name], /session load <name>, /session list, /session delete <name>, /session export <name>")
        return False
    
    action = command_parts[1].lower()
    
    try:
        if action == "new":
            session_name = command_parts[2] if len(command_parts) > 2 else None
            new_session = log_manager.create_new_session(session_name)
            print_info(f"Created new session: {new_session}")
            return True
            
        elif action == "load":
            if len(command_parts) < 3:
                print_error("Please specify session name: /session load <name>")
                return False
            session_name = command_parts[2]
            session_data = log_manager.load_session(session_name)
            print_info(f"Loaded session: {session_name} ({session_data['message_count']} messages)")
            # Return the history for the main loop to use
            return session_data['history']
            
        elif action == "list":
            sessions = log_manager.list_sessions()
            if not sessions:
                print_info("No chat sessions found.")
                return False
                
            print_heading("Available Chat Sessions")
            for session in sessions:
                created = datetime.fromisoformat(session['created_at']).strftime("%Y-%m-%d %H:%M")
                updated = datetime.fromisoformat(session['last_updated']).strftime("%Y-%m-%d %H:%M")
                print(f"{Fore.YELLOW}{session['name']:<20} {Fore.WHITE}Created: {created} Updated: {updated} Messages: {session['message_count']}")
            return False
            
        elif action == "delete":
            if len(command_parts) < 3:
                print_error("Please specify session name: /session delete <name>")
                return False
            session_name = command_parts[2]
            if log_manager.delete_session(session_name):
                print_info(f"Deleted session: {session_name}")
            else:
                print_error(f"Session not found: {session_name}")
            return False
            
        elif action == "export":
            if len(command_parts) < 3:
                print_error("Please specify session name: /session export <name>")
                return False
            session_name = command_parts[2]
            output_file = log_manager.export_session(session_name, "txt")
            print_info(f"Exported session to: {output_file}")
            return False
            
        else:
            print_error(f"Unknown session command: {action}")
            return False
            
    except Exception as e:
        print_error(f"Session command failed: {e}")
        return False

# =========================
# Setup MCP Manager
# =========================
async def setup_mcp():
    manager = MCPManager()
    # Updated paths - filesystem server should be in same directory
    await manager.add_server("local", "../filesystem/mcp_server.py")
    await manager.add_server("tounge", "../filesystem/tounge.py")
    await manager.add_server("serving", "../filesystem/git_server.py")
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
        log_manager = ChatLogManager()
        
        # Create initial session
        initial_session = log_manager.create_new_session()
        
        # DEBUG: Print tool schemas to see what parameters are expected
        manager.debug_tool_schemas()  # Add this line for debugging
        
        tools = manager.get_tools_for_claude()
        
        print_heading("Chat CLI with Claude + MCP + JSON Logs")
        print_info(f"Loaded {len(tools)} tools from MCP servers")
        print_info(f"Active session: {initial_session}")
        print_info("Commands: 'exit', 'debug', '/session new|load|list|delete|export'\n")

        history = []

        while True:
            # Show session info
            try:
                current_session = log_manager.load_current_session()
                print_session_info(current_session['session_name'], current_session['message_count'])
            except:
                pass
                
            user_input = input(Fore.WHITE + "You: ")
            if not user_input or user_input.lower() == "exit":
                print_info("Session ended")
                break
            elif user_input.lower() == "debug":
                manager.debug_tool_schemas()
                continue
            elif user_input.startswith("/session"):
                result = handle_session_commands(user_input.split(), log_manager)
                if isinstance(result, list):  # Loading session returned history
                    history = result
                    # Convert from log format to Claude format
                    claude_history = []
                    for msg in history:
                        claude_history.append({
                            "role": msg["role"], 
                            "content": msg["content"]
                        })
                    history = claude_history
                continue

            # Log user message
            log_manager.append_message("user", user_input)
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
                    log_manager.append_message("assistant", assistant_content, {"has_tool_calls": True})
                    
                    # Add tool results as user message
                    history.append({"role": "user", "content": tool_results})
                    log_manager.append_message("user", tool_results, {"tool_results": True})

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
                    log_manager.append_message("assistant", text_response)

                if not handled:
                    text_reply = "".join([p.text for p in resp.content if p.type == "text"])
                    print(Fore.BLUE + f"Claude: {text_reply}\n")
                    history.append({"role": "assistant", "content": text_reply})
                    log_manager.append_message("assistant", text_reply)

            except Exception as e:
                print_error(f"Error with Claude: {e}")
                log_manager.append_message("system", f"Error: {str(e)}", {"error": True})
                # Continue the loop instead of crashing
                continue
                
    except Exception as e:
        print_error(f"Failed to setup MCP manager: {e}")
        print_info("Make sure the filesystem MCP server is properly set up")

if __name__ == "__main__":
    asyncio.run(main())