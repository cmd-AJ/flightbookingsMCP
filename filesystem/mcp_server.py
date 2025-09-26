#!/usr/bin/env python3
"""
Filesystem MCP Server
Provides file system operations
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Filesystem")

@mcp.tool()
def read_file(file_path: str) -> Dict[str, Any]:
    """Read the contents of a file"""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "file_path": str(path.absolute())
        }
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}

@mcp.tool()
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file"""
    try:
        path = Path(file_path)
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"Successfully wrote to {file_path}",
            "file_path": str(path.absolute())
        }
    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}

@mcp.tool()
def list_directory(directory_path: str = ".") -> Dict[str, Any]:
    """List the contents of a directory"""
    try:
        path = Path(directory_path)
        if not path.exists():
            return {"error": f"Directory not found: {directory_path}"}
        
        if not path.is_dir():
            return {"error": f"Path is not a directory: {directory_path}"}
        
        items = []
        for item in path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str(item.absolute())
            })
        
        return {
            "success": True,
            "directory": str(path.absolute()),
            "items": items
        }
    except Exception as e:
        return {"error": f"Failed to list directory: {str(e)}"}

@mcp.tool()
def create_directory(directory_path: str) -> Dict[str, Any]:
    """Create a new directory"""
    try:
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "message": f"Successfully created directory: {directory_path}",
            "directory_path": str(path.absolute())
        }
    except Exception as e:
        return {"error": f"Failed to create directory: {str(e)}"}

@mcp.tool()
def delete_file(file_path: str) -> Dict[str, Any]:
    """Delete a file"""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        
        path.unlink()
        
        return {
            "success": True,
            "message": f"Successfully deleted file: {file_path}"
        }
    except Exception as e:
        return {"error": f"Failed to delete file: {str(e)}"}



if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="stdio")