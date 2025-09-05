#!/usr/bin/env python3
import asyncio
import logging
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    INVALID_PARAMS,
    INTERNAL_ERROR
)
from flightbooking import FlightDataProcessor
from typing import Optional, Any, Sequence

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize flight processor
flight_processor = FlightDataProcessor("data")

# Define available tools
TOOLS = [
    Tool(
        name="load_flight_data",
        description="Load and process flight booking CSV data",
        inputSchema={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the CSV file to load"}
            },
            "required": ["filename"]
        }
    ),
    Tool(
        name="flight_summary",
        description="Get comprehensive summary of flight data",
        inputSchema={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the loaded flight data file"}
            },
            "required": ["filename"]
        }
    ),
    Tool(
        name="cheapest_flights",
        description="Find the cheapest flights overall or for a specific route",
        inputSchema={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Name of the loaded flight data file"},
                "route": {"type": "string", "description": "Optional route in format FROM-TO"},
                "limit": {"type": "integer", "description": "Number of flights to return", "default": 10}
            },
            "required": ["filename"]
        }
    ),
    # Add other tools as needed (flight_summary, etc.)
]

class FlightBookingsServer:
    def __init__(self):
        self.server = Server("flightbookings-server")
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
        self.flight_data = None  # Initialize this as None, to be set later

    async def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """List available tools."""
        return ListToolsResult(tools=TOOLS)

    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Execute a tool call."""
        try:
            tool_name = request.params.name
            arguments = request.params.arguments or {}

            if tool_name == "load_flight_data":
                result = flight_processor.load_and_process_flights(arguments["filename"])
                if arguments["filename"] in flight_processor.loaded_datasets:
                    self.flight_data = flight_processor  # Store loaded dataset in server
                return CallToolResult(content=[TextContent(type="text", text=result)])
                
            elif tool_name == "flight_summary":
                result = flight_processor.get_flight_summary(arguments["filename"])
                return CallToolResult(content=[TextContent(type="text", text=result)])
                
            elif tool_name == "cheapest_flights":
                result = flight_processor.find_cheapest_flights(
                    arguments["filename"],
                    arguments.get("route"),
                    arguments.get("limit", 10)
                )
                return CallToolResult(content=[TextContent(type="text", text=result)])
                
            # Handle other tools similarly...
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {tool_name}")],
                    isError=True
                )

        except Exception as e:
            logger.error(f"Error in tool {tool_name}: {str(e)}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True
            )

    async def run(self):
        """Run the server."""
        try:
            logger.info("Setting up the MCP server...")

            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="flightbookings-server",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=None,
                            experimental_capabilities={},
                        ),
                    ),
                )
            logger.info("Server started successfully.")
        except Exception as e:
            logger.error(f"Error starting the server: {e}")

async def main():
    """Main function to run the FlightBookings MCP server."""
    logger.info("Starting FlightBookings MCP Server...")
    server = FlightBookingsServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
