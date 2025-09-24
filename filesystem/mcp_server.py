
import os
import subprocess
from pathlib import Path
from fastmcp import FastMCP
import sys 
# Create the MCP server
mcp = FastMCP("filesystem-git-server")
import logging

# =============================================================================
# FILESYSTEM TOOLS
# =============================================================================

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read the contents of a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"File content:\n{content}"
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except PermissionError:
        return f"Error: Permission denied to read '{file_path}'"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def write_file(file_path: str, content: str) -> str:
    """Write content to a file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{file_path}'"
    except PermissionError:
        return f"Error: Permission denied to write to '{file_path}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@mcp.tool()
def list_directory(directory_path: str = ".") -> str:
    """List the contents of a directory"""
    try:
        path = Path(directory_path)
        if not path.exists():
            return f"Error: Directory '{directory_path}' does not exist"
        
        items = []
        for item in sorted(path.iterdir()):
            item_type = "📁" if item.is_dir() else "📄"
            size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
            items.append(f"{item_type} {item.name}{size}")
        
        return f"Contents of '{directory_path}':\n" + "\n".join(items)
    except PermissionError:
        return f"Error: Permission denied to access '{directory_path}'"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@mcp.tool()
def create_directory(directory_path: str) -> str:
    """Create a new directory"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return f"Successfully created directory '{directory_path}'"
    except PermissionError:
        return f"Error: Permission denied to create '{directory_path}'"
    except Exception as e:
        return f"Error creating directory: {str(e)}"

@mcp.tool()
def delete_file(file_path: str) -> str:
    """Delete a file"""
    try:
        os.remove(file_path)
        return f"Successfully deleted '{file_path}'"
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except PermissionError:
        return f"Error: Permission denied to delete '{file_path}'"
    except Exception as e:
        return f"Error deleting file: {str(e)}"

# =============================================================================
# GIT TOOLS
# =============================================================================
def run_git_command(cmd, repo_path="."):
    """Run a git command safely (no pager, no prompts)."""
    try:
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return False, f"Not a git repository: {repo_path}"

        full_cmd = ["git", "--no-pager"] + cmd
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        result = subprocess.run(
            full_cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env=env
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except Exception as e:
        return False, f"Error: {e}"


@mcp.tool()
def git_init(repo_path: str = ".") -> str:
    """Initialize a new git repository"""
    success, output = run_git_command(["init"], repo_path)
    
    if not success:
        return f"Error initializing git repository: {output}"
    
    return f"Successfully initialized git repository in '{repo_path}'\n{output}"

@mcp.tool()
def git_status(repo_path: str = ".") -> str:
    ok, out = run_git_command(["status", "--short", "--untracked-files=all"], repo_path)
    if not ok:
        return f"Error: {out}"
    return "Repository is clean" if not out else f"Git status:\n{out}"

@mcp.tool()
def git_log(repo_path: str = ".", limit: int = 10) -> str:
    """Get the git commit history"""
    success, output = run_git_command(["log", f"--max-count={limit}", "--oneline", "--decorate"], repo_path)
    
    if not success:
        return f"Error getting git log: {output}"
    
    return f"Recent commits (last {limit}):\n{output}"

@mcp.tool()
def git_branch(repo_path: str = ".") -> str:
    """List git branches"""
    success, output = run_git_command(["branch", "-v"], repo_path)
    
    if not success:
        return f"Error getting git branches: {output}"
    
    return f"Git branches:\n{output}"

@mcp.tool()
def git_diff(repo_path: str = ".", file_path: str = "") -> str:
    """Show git diff for changes"""
    cmd = ["diff"]
    if file_path:
        cmd.append(file_path)
    
    success, output = run_git_command(cmd, repo_path)
    
    if not success:
        return f"Error getting git diff: {output}"
    
    if not output.strip():
        return "No changes to show"
    
    return f"Git diff:\n{output}"

@mcp.tool()
def git_add(repo_path: str = ".", file_path: str = ".") -> str:
    """Add files to git staging area"""
    success, output = run_git_command(["add", file_path], repo_path)
    
    if not success:
        return f"Error adding files to git: {output}"
    
    return f"Successfully added '{file_path}' to staging area"

@mcp.tool()
def git_commit(repo_path: str = ".", message: str = "Automated commit") -> str:
    """Commit staged changes"""
    success, output = run_git_command(["commit", "-m", message], repo_path)
    
    if not success:
        # Check if it's because there's nothing to commit
        if "nothing to commit" in output.lower():
            return "Nothing to commit - working tree clean"
        return f"Error committing changes: {output}"
    
    return f"Successfully committed with message: '{message}'\n{output}"

@mcp.tool()
def manual_git_commands(repo_path: str = ".") -> str:
    """Provide manual git commands to run in terminal"""
    readme_path = os.path.join(repo_path, "README.md")
    
    commands = f"""
Since git operations through MCP might have permission issues, here are the manual commands to run:

1. Open Command Prompt or Terminal
2. Navigate to your project:
   cd "{repo_path}"

3. Add the README file:
   git add README.md

4. Commit the changes:
   git commit -m "Add comprehensive README documentation"

5. Check status:
   git status

6. Push to remote (if you have one set up):
   git push origin master

Alternatively, you can use Git GUI or your IDE's git integration.
"""
    return commands

# =============================================================================
# RUN THE SERVER
# =============================================================================

if __name__ == "__main__":
    # Loguea a stderr (no uses print a stdout)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logging.info("Starting filesystem-git MCP server…")
    try:
        mcp.run()
    except Exception as e:
        logging.exception("Failed to start server: %s", e)