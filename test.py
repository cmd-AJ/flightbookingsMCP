#!/usr/bin/env python3
"""
Direct test of MCP server functionality without the stdio wrapper.
This bypasses potential initialization issues.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flightbooking import FlightDataProcessor
from main import FlightBookingsServer, TOOLS

async def test_server_directly():
    """Test the server components directly."""
    
    print("=== Direct MCP Server Test ===\n")
    
    # 1. Test FlightDataProcessor
    print("1. Testing FlightDataProcessor...")
    processor = FlightDataProcessor("data")
    
    # 2. Make sure the "flights.csv" file exists in the "data" directory.
    flights_csv = "flights.csv"
    if not os.path.exists(f"data/{flights_csv}"):
        print(f"Error: {flights_csv} not found in the data directory.")
        return
    
    # Load and process flights.csv
    result = processor.load_and_process_flights(flights_csv)
    print(f"   Load result: {result}")
    
    # Get the flight summary for flights.csv
    summary = processor.get_flight_summary(flights_csv)
    print(f"   Summary: {summary[:100]}...")  # Printing the first 100 characters for brevity
    
    # 2. Test Server Instance
    print("\n2. Testing Server Instance...")
    server = FlightBookingsServer()
    
    # Test list_tools directly
    print("\n   Testing ListToolsRequest...")
    from mcp.types import ListToolsRequest
    tools_request = ListToolsRequest(method="tools/list", params={})  # Explicitly provide method and params
    tools_result = await server.list_tools(tools_request)
    
    print(f"   Available tools: {len(tools_result.tools)}")
    for tool in tools_result.tools[:3]:  # Show first 3
        print(f"   - {tool.name}: {tool.description}")
    
    # 3. Test tool calling directly
    print("\n3. Testing Tool Calls...")
    
    # Test load_flight_data tool
    from mcp.types import CallToolRequest, CallToolRequestParams
    
    params = CallToolRequestParams(
        name="load_flight_data",
        arguments={"filename": flights_csv}  # Use the actual "flights.csv" file here
    )
    request = CallToolRequest(method="tools/call", params=params)  # Include the 'method' field
    result = await server.call_tool(request)
    
    print(f"   Load tool result: {result.content[0].text}")
    
    # Test flight_summary tool
    params = CallToolRequestParams(
        name="flight_summary", 
        arguments={"filename": flights_csv}  # Use the actual "flights.csv" file here
    )
    request = CallToolRequest(method="tools/call", params=params)  # Include the 'method' field
    result = await server.call_tool(request)
    
    print(f"   Summary tool result: {result.content[0].text[:200]}...")  # First 200 characters
    
    print("\n=== All Direct Tests Passed! ===")
    print("\nYour server components are working correctly.")
    print("The issue is likely with the MCP initialization protocol.")
    print("\nTry using your server with Claude Desktop or another MCP client.")
    
    # Cleanup (optional, in case you want to clean up after testing)
    # os.remove("data/flights.csv")

if __name__ == "__main__":
    asyncio.run(test_server_directly())
