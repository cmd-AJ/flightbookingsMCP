import os
import sys
import json
import asyncio
import subprocess
from dotenv import load_dotenv
from fastmcp import Client as FastMCPClient
from colorama import Fore, Style, init
import anthropic

init(autoreset=True)
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# =========================
# Enhanced MCP Manager with Multiple Transport Support
# =========================
class MCPManager:
    def __init__(self):
        self.servers = {}   # {alias: {"type": "http|stdio|npx", "config": {...}}}
        self.tools = []     # merged tools with server alias

    async def add_http_server(self, alias: str, url: str):
        """Add HTTP-based MCP server (like your flight booking server)."""
        self.servers[alias] = {"type": "http", "config": {"url": url}}
        await self._load_tools_from_server(alias, url)

    async def add_python_stdio_server(self, alias: str, python_script_path: str, work_dir: str = "."):
        """Add Python-based stdio MCP server."""
        self.servers[alias] = {
            "type": "stdio", 
            "config": {
                "command": "python",
                "args": [python_script_path],
                "cwd": work_dir
            }
        }
        # For stdio servers, we need to use subprocess communication
        await self._load_tools_from_stdio_server(alias, python_script_path, work_dir)

    async def add_npx_server(self, alias: str, package_name: str, *args, work_dir: str = "."):
        """Add NPX-based MCP server (like the official filesystem server)."""
        self.servers[alias] = {
            "type": "npx",
            "config": {
                "command": "npx",
                "args": [package_name] + list(args),
                "cwd": work_dir
            }
        }
        await self._load_tools_from_npx_server(alias, package_name, args, work_dir)

    async def _load_tools_from_server(self, alias: str, url: str):
        """Load tools from HTTP server using FastMCP."""
        try:
            client = FastMCPClient(url)
            async with client:
                tools = await client.list_tools()
                for t in tools:
                    modified_schema = self._modify_tool_schema(t.name, getattr(t, "input_schema", {"type": "object"}))
                    self.tools.append({
                        "server": alias,
                        "name": t.name,
                        "description": t.description,
                        "input_schema": modified_schema
                    })
                print_info(f"Loaded {len(tools)} tools from HTTP server '{alias}'")
        except Exception as e:
            print_error(f"Failed to load tools from {alias}: {e}")

    async def _load_tools_from_stdio_server(self, alias: str, script_path: str, work_dir: str):
        """Load tools from Python stdio server."""
        # For stdio servers, we need a different approach
        # This is a placeholder - you'll need to implement MCP stdio communication
        print_info(f"STDIO server '{alias}' registered (tools will be discovered on first use)")
        
        # Add some common filesystem/git tools manually for now
        common_tools = [
            {"name": "read_file", "description": "Read file contents"},
            {"name": "write_file", "description": "Write file contents"},
            {"name": "list_directory", "description": "List directory contents"},
            {"name": "create_directory", "description": "Create directory"},
            {"name": "git_init", "description": "Initialize git repository"},
            {"name": "git_add", "description": "Add files to git"},
            {"name": "git_commit", "description": "Commit changes"},
            {"name": "git_status", "description": "Get git status"}
        ]
        
        for tool in common_tools:
            modified_schema = self._modify_tool_schema(tool["name"], {"type": "object"})
            self.tools.append({
                "server": alias,
                "name": tool["name"], 
                "description": tool["description"],
                "input_schema": modified_schema
            })

    async def _load_tools_from_npx_server(self, alias: str, package_name: str, args: tuple, work_dir: str):
        """Load tools from NPX server."""
        print_info(f"NPX server '{alias}' registered with package '{package_name}'")
        
        # For the official filesystem server, add known tools
        if "server-filesystem" in package_name:
            filesystem_tools = [
                {"name": "read_file", "description": "Read the contents of a file"},
                {"name": "write_file", "description": "Write content to a file"}, 
                {"name": "list_directory", "description": "List the contents of a directory"},
                {"name": "create_directory", "description": "Create a new directory"},
                {"name": "delete_file", "description": "Delete a file"},
                {"name": "git_init", "description": "Initialize a new git repository"},
                {"name": "git_status", "description": "Get git status"},
                {"name": "git_add", "description": "Add files to git staging area"},
                {"name": "git_commit", "description": "Commit staged changes"},
                {"name": "git_log", "description": "Get the git commit history"},
                {"name": "git_branch", "description": "List git branches"},
                {"name": "git_diff", "description": "Show git diff for changes"}
            ]
            
            for tool in filesystem_tools:
                modified_schema = self._modify_tool_schema(tool["name"], {"type": "object"})
                self.tools.append({
                    "server": alias,
                    "name": tool["name"],
                    "description": tool["description"], 
                    "input_schema": modified_schema
                })

    async def call_tool(self, server_alias: str, tool_name: str, params: dict):
        """Route tool call to appropriate server type."""
        server = self.servers.get(server_alias)
        if not server:
            raise ValueError(f"No such MCP server: {server_alias}")

        mapped_params = self._map_parameters(tool_name, params)
        
        if server["type"] == "http":
            return await self._call_http_tool(server["config"]["url"], tool_name, mapped_params)
        elif server["type"] == "stdio":
            return await self._call_stdio_tool(server["config"], tool_name, mapped_params)
        elif server["type"] == "npx":
            return await self._call_npx_tool(server["config"], tool_name, mapped_params)
        else:
            raise ValueError(f"Unsupported server type: {server['type']}")

    async def _call_http_tool(self, url: str, tool_name: str, params: dict):
        """Call tool on HTTP server."""
        client = FastMCPClient(url)
        async with client:
            return await client.call_tool(tool_name, params)

    async def _call_stdio_tool(self, config: dict, tool_name: str, params: dict):
        """Call tool on stdio server."""
        # This is a simplified implementation
        # In a real implementation, you'd maintain persistent stdio connections
        try:
            cmd = [config["command"]] + config["args"] + ["--tool", tool_name]
            
            # Convert params to command line arguments
            for key, value in params.items():
                cmd.extend([f"--{key}", str(value)])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=config["cwd"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Mock response format
                return type('MockResult', (), {
                    'content': [type('MockContent', (), {'text': stdout.decode()})()]
                })()
            else:
                raise Exception(f"Tool execution failed: {stderr.decode()}")
                
        except Exception as e:
            raise Exception(f"STDIO tool call failed: {e}")

    async def _call_npx_tool(self, config: dict, tool_name: str, params: dict):
        """Call tool on NPX server."""
        try:
            # Build command for NPX server
            cmd = config["args"].copy()  # Start with base npx command
            
            # Add tool-specific logic here
            if tool_name == "read_file":
                file_path = params.get("file_path") or params.get("path")
                if file_path:
                    # Simple file read using cat (this is a fallback)
                    process = await asyncio.create_subprocess_exec(
                        "cat", file_path,
                        cwd=config["cwd"],
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    if process.returncode == 0:
                        return type('MockResult', (), {
                            'content': [type('MockContent', (), {'text': stdout.decode()})()]
                        })()
            
            elif tool_name == "git_init":
                repo_path = params.get("repo_path") or params.get("path") or "."
                process = await asyncio.create_subprocess_exec(
                    "git", "init",
                    cwd=os.path.join(config["cwd"], repo_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                result_text = stdout.decode() + stderr.decode()
                return type('MockResult', (), {
                    'content': [type('MockContent', (), {'text': result_text})()]
                })()
            
            # Add more tool implementations as needed
            raise Exception(f"Tool '{tool_name}' not implemented for NPX server")
            
        except Exception as e:
            raise Exception(f"NPX tool call failed: {e}")

    def _modify_tool_schema(self, tool_name: str, original_schema: dict) -> dict:
        """Modify tool schemas to match what Claude expects to send."""
        schema_modifications = {
            # Flight booking tools
            'search_cheapest_flights': {
                'type': 'object',
                'properties': {
                    'origin': {'type': 'string', 'description': 'Origin airport code'},
                    'destination': {'type': 'string', 'description': 'Destination airport code'},
                    'limit': {'type': 'integer', 'description': 'Number of results', 'default': 10},
                    'max_stops': {'type': 'integer', 'description': 'Maximum stops', 'default': 2}
                }
            },
            # File operations
            'read_file': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'File path to read'}
                },
                'required': ['path']
            },
            'write_file': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'File path to write'},
                    'content': {'type': 'string', 'description': 'Content to write'}
                },
                'required': ['path', 'content']
            },
            'list_directory': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Directory path to list', 'default': '.'}
                }
            },
            'create_directory': {
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Directory path to create'}
                },
                'required': ['path']
            },
            # Git operations
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
            }
        }
        
        return schema_modifications.get(tool_name, original_schema)

    def _map_parameters(self, tool_name: str, params: dict) -> dict:
        """Map parameters to match server expectations."""
        parameter_mappings = {
            # File operations - NPX filesystem server expects these names
            'read_file': {'path': 'file_path'},
            'write_file': {'path': 'file_path'},
            'list_directory': {'path': 'directory_path'}, 
            'create_directory': {'path': 'directory_path'},
            
            # Git operations - map directory to repo_path
            'git_init': {'directory': 'path'},
            'git_add': {'directory': 'repo_path'},
            'git_commit': {'directory': 'repo_path'},
            
            # Flight search
            'search_cheapest_flights': {'origin': 'from_city', 'destination': 'to_city'}
        }
        
        mapping = parameter_mappings.get(tool_name, {})
        mapped_params = {}
        
        for key, value in params.items():
            mapped_key = mapping.get(key, key)
            if mapped_key is not None:
                mapped_params[mapped_key] = value
        
        return mapped_params

    def debug_tool_schemas(self):
        """Print all tool schemas for debugging."""
        print(Fore.CYAN + "\n=== DEBUGGING TOOL SCHEMAS ===")
        for tool in self.tools:
            print(f"\n{Fore.YELLOW}=== {tool['server']}_{tool['name']} ===")
            print(f"{Fore.WHITE}Description: {tool['description']}")
            print(f"{Fore.MAGENTA}Schema: {json.dumps(tool['input_schema'], indent=2)}")
        print(Fore.CYAN + "\n=== END SCHEMAS DEBUG ===\n")

    def get_tools_for_claude(self):
        """Format tools into Claude's schema with server prefix."""
        tools_for_claude = []
        for t in self.tools:
            claude_tool_name = f"{t['server']}_{t['name']}"
            tools_for_claude.append({
                "name": claude_tool_name,
                "description": f"[{t['server']}] {t['description']}",
                "input_schema": t["input_schema"]
            })
        return tools_for_claude

    def parse_tool_name(self, claude_tool_name: str):
        """Parse Claude tool name back to server alias and original tool name."""
        parts = claude_tool_name.split('_', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
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
# Setup MCP Manager with Multiple Server Types
# =========================
async def setup_mcp():
    manager = MCPManager()
    
    # Add HTTP server (your flight booking server)
    await manager.add_http_server("remote", "https://flightbookingU.fastmcp.app/mcp")
    
    # Add NPX-based official filesystem server
    # First install it: npm install -g @modelcontextprotocol/server-filesystem
    await manager.add_npx_server("fs", "@modelcontextprotocol/server-filesystem", "/Users/youruser/allowed-directory")
    
    # Add Python stdio server (your custom server)
    # await manager.add_python_stdio_server("local", "../filesystem/mcp_server.py")
    
    return manager

# =========================
# Main Loop (same as before)
# =========================
async def main():
    try:
        print_info("Setting up MCP servers...")
        manager = await setup_mcp()
        
        manager.debug_tool_schemas()
        
        tools = manager.get_tools_for_claude()
        
        print_heading("Enhanced MCP Client with Multiple Server Support")
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
                
                for part in resp.content:
                    if part.type == "text":
                        assistant_content.append(part)
                    elif part.type == "tool_use":
                        assistant_content.append(part)
                        
                        server_alias, tool_name = manager.parse_tool_name(part.name)
                        params = part.input

                        print_function_call(part.name, params)

                        if server_alias:
                            raw_result = await manager.call_tool(server_alias, tool_name, params)
                        else:
                            print_error(f"Could not parse server alias from tool name: {part.name}")
                            continue
                        
                        # Extract result
                        if hasattr(raw_result, 'content') and raw_result.content:
                            first_content = raw_result.content[0]
                            if hasattr(first_content, 'text'):
                                try:
                                    tool_result = json.loads(first_content.text)
                                except json.JSONDecodeError:
                                    tool_result = {"response": first_content.text}
                            else:
                                tool_result = {"response": str(first_content)}
                        else:
                            tool_result = {"response": str(raw_result)}

                        print_tool_result(tool_result)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": part.id,
                            "content": json.dumps(tool_result)
                        })
                        handled = True

                if handled:
                    history.append({"role": "assistant", "content": assistant_content})
                    history.append({"role": "user", "content": tool_results})

                    followup = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        tools=tools,
                        messages=history
                    )
                    
                    text_response = "".join([p.text for p in followup.content if p.type == "text"])
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
                continue
                
    except Exception as e:
        print_error(f"Failed to setup MCP manager: {e}")

if __name__ == "__main__":
    asyncio.run(main())