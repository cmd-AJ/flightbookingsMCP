
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Git")


@mcp.tool()
def git_init(path: str = ".") -> Dict[str, Any]:
    """Initialize a new git repository"""
    try:
        repo_path = Path(path)
        if not repo_path.exists():
            return {"error": f"Directory not found: {path}"}

        result = subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Initialized git repository in {path}",
                "output": result.stdout.strip()
            }
        else:
            return {"error": f"Git init failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to initialize git repository: {str(e)}"}

@mcp.tool()
def git_status(repo_path: str = ".") -> Dict[str, Any]:
    """Get git status"""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "status": result.stdout,
                "repo_path": str(Path(repo_path).absolute())
            }
        else:
            return {"error": f"Git status failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to get git status: {str(e)}"}

@mcp.tool()
def git_add(file_path: str = ".", repo_path: str = ".") -> Dict[str, Any]:
    """Add files to git staging area"""
    try:
        result = subprocess.run(
            ["git", "add", file_path],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Added {file_path} to staging area"
            }
        else:
            return {"error": f"Git add failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to add files to git: {str(e)}"}

@mcp.tool()
def git_commit(message: str = "Automated commit", repo_path: str = ".") -> Dict[str, Any]:
    """Commit staged changes"""
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": f"Committed changes with message: {message}",
                "output": result.stdout.strip()
            }
        else:
            return {"error": f"Git commit failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to commit changes: {str(e)}"}

@mcp.tool()
def git_log(limit: int = 10, repo_path: str = ".") -> Dict[str, Any]:
    """Get the git commit history"""
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else ""
                    })
            
            return {
                "success": True,
                "commits": commits,
                "repo_path": str(Path(repo_path).absolute())
            }
        else:
            return {"error": f"Git log failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to get git log: {str(e)}"}

@mcp.tool()
def git_branch(repo_path: str = ".") -> Dict[str, Any]:
    """List git branches"""
    try:
        result = subprocess.run(
            ["git", "branch"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            branches = []
            current_branch = None
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    if line.startswith('* '):
                        current_branch = line[2:].strip()
                        branches.append(current_branch)
                    else:
                        branches.append(line.strip())
            
            return {
                "success": True,
                "branches": branches,
                "current_branch": current_branch,
                "repo_path": str(Path(repo_path).absolute())
            }
        else:
            return {"error": f"Git branch failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to list git branches: {str(e)}"}

@mcp.tool()
def git_diff(file_path: str = "", repo_path: str = ".") -> Dict[str, Any]:
    """Show git diff for changes"""
    try:
        cmd = ["git", "diff"]
        if file_path:
            cmd.append(file_path)
        
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "diff": result.stdout,
                "file_path": file_path,
                "repo_path": str(Path(repo_path).absolute())
            }
        else:
            return {"error": f"Git diff failed: {result.stderr}"}
    except Exception as e:
        return {"error": f"Failed to get git diff: {str(e)}"}

@mcp.tool()
def manual_git_commands(repo_path: str = ".") -> Dict[str, Any]:
    """Provide manual git commands to run in terminal"""
    return {
        "success": True,
        "message": "Here are some common git commands you can run manually:",
        "commands": [
            "git init - Initialize a new git repository",
            "git status - Check the status of your repository",
            "git add <file> - Add files to staging area",
            "git add . - Add all files to staging area",
            "git commit -m 'message' - Commit staged changes",
            "git log - View commit history",
            "git branch - List branches",
            "git diff - Show changes"
        ],
        "repo_path": str(Path(repo_path).absolute())
    }