#!/usr/bin/env python3
"""
Git MCP Server - A Model Context Protocol server for Git operations
Improved version with better error handling and timeout support
"""

import asyncio
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# MCP SDK imports
try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print("Error: mcp package not found. Install with: pip install mcp")
    sys.exit(1)

# Initialize the MCP server
app = Server("git-server")

class GitError(Exception):
    """Custom exception for Git operations"""
    pass

def run_git_command(args: List[str], cwd: Optional[str] = None, timeout: int = 30) -> str:
    """Run a git command and return the output with timeout and better error handling"""
    try:
        # Ensure we have a valid working directory
        if cwd is None:
            cwd = os.getcwd()
        
        # Convert to absolute path and validate
        cwd = os.path.abspath(cwd)
        if not os.path.exists(cwd):
            raise GitError(f"Directory does not exist: {cwd}")
        
        # Set up environment to avoid interactive prompts
        env = os.environ.copy()
        env.update({
            'GIT_TERMINAL_PROMPT': '0',  # Disable terminal prompts
            'GIT_ASKPASS': 'echo',       # Provide dummy askpass to avoid hanging
            'SSH_ASKPASS': 'echo',       # Avoid SSH prompts
            'GIT_SSH_COMMAND': 'ssh -o BatchMode=yes -o StrictHostKeyChecking=no'
        })
        
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=True,
            timeout=timeout,
            env=env
        )
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        raise GitError(f"Git command timed out after {timeout} seconds: git {' '.join(args)}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error"
        raise GitError(f"Git command failed: {error_msg}")
    except FileNotFoundError:
        raise GitError("Git is not installed or not in PATH")
    except Exception as e:
        raise GitError(f"Unexpected error: {str(e)}")

def validate_git_repo(path: str) -> bool:
    """Check if the given path is a valid Git repository"""
    try:
        run_git_command(["rev-parse", "--git-dir"], cwd=path, timeout=5)
        return True
    except GitError:
        return False

@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available Git tools"""
    return [
        types.Tool(
            name="git_status",
            description="Get the status of the Git repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional, defaults to current directory)"
                    }
                }
            }
        ),
        types.Tool(
            name="git_log",
            description="Get the Git commit history",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of commits to show (default: 10)"
                    },
                    "oneline": {
                        "type": "boolean",
                        "description": "Show one line per commit (default: false)"
                    }
                }
            }
        ),
        types.Tool(
            name="git_diff",
            description="Show changes between commits, commit and working tree, etc",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes (default: false)"
                    },
                    "file": {
                        "type": "string",
                        "description": "Show diff for specific file (optional)"
                    }
                }
            }
        ),
        types.Tool(
            name="git_add",
            description="Add files to the staging area",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to add (use '.' for all files)"
                    }
                },
                "required": ["files"]
            }
        ),
        types.Tool(
            name="git_commit",
            description="Create a new commit",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "all": {
                        "type": "boolean",
                        "description": "Commit all modified files (default: false)"
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="git_branch",
            description="List, create, or delete branches",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "list": {
                        "type": "boolean",
                        "description": "List all branches (default: true)"
                    },
                    "create": {
                        "type": "string",
                        "description": "Create a new branch with this name"
                    },
                    "delete": {
                        "type": "string",
                        "description": "Delete branch with this name"
                    }
                }
            }
        ),
        types.Tool(
            name="git_checkout",
            description="Switch branches or restore working tree files",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name to checkout"
                    },
                    "create": {
                        "type": "boolean",
                        "description": "Create new branch if it doesn't exist (default: false)"
                    }
                },
                "required": ["branch"]
            }
        ),
        types.Tool(
            name="git_push",
            description="Push commits to remote repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "remote": {
                        "type": "string",
                        "description": "Remote name (default: origin)"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to current branch)"
                    }
                }
            }
        ),
        types.Tool(
            name="git_pull",
            description="Fetch and merge changes from remote repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the Git repository (optional)"
                    },
                    "remote": {
                        "type": "string",
                        "description": "Remote name (default: origin)"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (optional, defaults to current branch)"
                    }
                }
            }
        ),
        types.Tool(
            name="git_init",
            description="Initialize a new Git repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path where to initialize the repository (optional)"
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[types.TextContent]:
    """Handle tool calls"""
    try:
        path = arguments.get("path", ".")
        
        # For init, we don't need to validate the repo exists yet
        if name != "git_init" and not validate_git_repo(path):
            return [types.TextContent(
                type="text", 
                text=f"Error: {path} is not a valid Git repository. Use git_init to create one."
            )]
        
        if name == "git_status":
            # Try porcelain format first, fall back to regular status
            try:
                output = run_git_command(["status", "--porcelain", "-b"], cwd=path)
                if not output:
                    output = "Working tree clean"
                else:
                    # Add a header for better readability
                    output = "Repository Status:\n" + output
            except GitError:
                output = run_git_command(["status"], cwd=path)
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_log":
            max_count = arguments.get("max_count", 10)
            oneline = arguments.get("oneline", False)
            
            args = ["log", f"--max-count={max_count}"]
            if oneline:
                args.append("--oneline")
            else:
                args.extend(["--pretty=format:%h - %an, %ar : %s"])
            
            output = run_git_command(args, cwd=path)
            if not output:
                output = "No commits found"
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_diff":
            staged = arguments.get("staged", False)
            file = arguments.get("file")
            
            args = ["diff"]
            if staged:
                args.append("--staged")
            if file:
                args.append(file)
            
            output = run_git_command(args, cwd=path)
            if not output:
                output = "No changes to show"
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_add":
            files = arguments["files"]
            args = ["add"] + files
            run_git_command(args, cwd=path)
            return [types.TextContent(type="text", text=f"Successfully added files: {', '.join(files)}")]
        
        elif name == "git_commit":
            message = arguments["message"]
            all_files = arguments.get("all", False)
            
            args = ["commit", "-m", message]
            if all_files:
                args.append("-a")
            
            output = run_git_command(args, cwd=path)
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_branch":
            if arguments.get("create"):
                branch_name = arguments["create"]
                run_git_command(["branch", branch_name], cwd=path)
                return [types.TextContent(type="text", text=f"Successfully created branch: {branch_name}")]
            
            elif arguments.get("delete"):
                branch_name = arguments["delete"]
                run_git_command(["branch", "-d", branch_name], cwd=path)
                return [types.TextContent(type="text", text=f"Successfully deleted branch: {branch_name}")]
            
            else:
                output = run_git_command(["branch", "-a"], cwd=path)
                if not output:
                    output = "No branches found"
                return [types.TextContent(type="text", text=output)]
        
        elif name == "git_checkout":
            branch = arguments["branch"]
            create = arguments.get("create", False)
            
            args = ["checkout"]
            if create:
                args.append("-b")
            args.append(branch)
            
            output = run_git_command(args, cwd=path)
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_push":
            remote = arguments.get("remote", "origin")
            branch = arguments.get("branch")
            
            args = ["push", remote]
            if branch:
                args.append(branch)
            
            output = run_git_command(args, cwd=path)
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_pull":
            remote = arguments.get("remote", "origin")
            branch = arguments.get("branch")
            
            args = ["pull", remote]
            if branch:
                args.append(branch)
            
            output = run_git_command(args, cwd=path)
            return [types.TextContent(type="text", text=output)]
        
        elif name == "git_init":
            output = run_git_command(["init"], cwd=path)
            return [types.TextContent(type="text", text=f"Initialized Git repository at {os.path.abspath(path)}")]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except GitError as e:
        return [types.TextContent(type="text", text=f"Git error: {str(e)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Main entry point"""
    try:
        # Run the server using stdio transport
        async with stdio_server() as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )
    except KeyboardInterrupt:
        print("\nShutting down Git MCP server...")
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())