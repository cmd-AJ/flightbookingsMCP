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
from main import FlightBookingsServer

async def test_cheapest_flights():
    """Test the cheapest_flights tool directly."""
    
    print("=== Direct Test of cheapest_flights Tool ===\n")
    
    # 1. Test FlightDataProcessor (Load flight data)
    print("1. Testing FlightDataProcessor...")

    # Create flight processor instance
    processor = FlightDataProcessor("data")
    
    # Ensure flights.csv exists in the "data" directory
    flights_csv = "flights.csv"
    if not os.path.exists(f"data/{flights_csv}"):
        print(f"Error: {flights_csv} not found in the data directory.")
        return
    
    # Load and process the flights data
    result = processor.load_and_process_flights(flights_csv)
    print(f"   Load result: {result}")
    
    # Ensure the dataset was loaded
    if flights_csv not in processor.loaded_datasets:
        print(f"Error: {flights_csv} was not loaded successfully.")
        return
    
    # 2. Test the server instance
    print("\n2. Testing Server Instance...")
    server = FlightBookingsServer()

    # Load the dataset into the server (ensure tools have access to the dataset)
    print("\n   Loading dataset into the server...")
    server.flight_data = processor  # Store the FlightDataProcessor instance in the server
    
    # Test list_tools directly
    print("\n   Testing ListToolsRequest...")
    from mcp.types import ListToolsRequest
    tools_request = ListToolsRequest(method="tools/list", params={})  # Explicitly provide method and params
    tools_result = await server.list_tools(tools_request)
    
    print(f"   Available tools: {len(tools_result.tools)}")
    for tool in tools_result.tools[:3]:  # Show first 3 tools
        print(f"   - {tool.name}: {tool.description}")
    
    # 3. Test tool calling directly: cheapest_flights
    print("\n3. Testing cheapest_flights tool...")
    from mcp.types import CallToolRequest, CallToolRequestParams
    
    # Prepare the parameters for the cheapest_flights tool
    params = CallToolRequestParams(
        name="cheapest_flights",
        arguments={
            "filename": flights_csv,  # Use the actual "flights.csv" file
            "limit": 5  # Limit the results to the top 5 cheapest flights
        }
    )
    
    # Call the tool
    request = CallToolRequest(method="tools/call", params=params)
    result = await server.call_tool(request)
    
    # Print the result of the cheapest_flights tool call
    print(f"   Cheapest flights result:\n{result.content[0].text}")
    
    print("\n=== Test Completed Successfully! ===")
    print("Your server components are working correctly with the `cheapest_flights` tool.")
    
if __name__ == "__main__":
    asyncio.run(test_cheapest_flights())
