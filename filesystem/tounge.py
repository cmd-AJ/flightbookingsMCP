#!/usr/bin/env python3
"""
Important Facts MCP Server
Provides random tongue twisters with important facts about them
"""

import random
from fastmcp import FastMCP
from typing import Dict, Any

# Initialize the MCP server
mcp = FastMCP("ImportantFacts")

# Sample list of tongue twisters
tongue_twisters = [
    {"twister": "Peter Piper picked a peck of pickled peppers.", "fact": "This tongue twister uses alliteration with the repetition of the 'p' sound."},
    {"twister": "She sells seashells by the seashore.", "fact": "This is a classic tongue twister that uses the 's' sound."},
    {"twister": "How much wood would a woodchuck chuck if a woodchuck could chuck wood?", "fact": "This tongue twister plays on the repetition of the 'w' sound."},
    {"twister": "Fuzzy Wuzzy was a bear. Fuzzy Wuzzy had no hair.", "fact": "This tongue twister is playful with repetition and rhyming words."},
    {"twister": "Betty Botter bought some butter, but she said the butter’s bitter.", "fact": "This tongue twister is challenging due to the rapid transition between 'b' and 't' sounds."}
]

@mcp.tool()
def get_random_tongue_twister() -> Dict[str, Any]:
    """Get a random tongue twister with its fact"""
    try:
        # Randomly select a tongue twister
        twister_data = random.choice(tongue_twisters)
        return {
            "success": True,
            "twister": twister_data["twister"],
            "fact": twister_data["fact"]
        }
    except Exception as e:
        return {"error": f"Failed to retrieve a random tongue twister: {str(e)}"}

if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="stdio")
