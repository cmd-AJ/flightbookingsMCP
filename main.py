#!/usr/bin/env python3
import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from flightbooking import FlightDataProcessor
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server and flight processor
mcp = FastMCP("flightbookings-server")
flight_processor = FlightDataProcessor("data")

@mcp.tool()
async def load_flight_data(filename: str) -> str:
    """Load and process flight booking CSV data.
    
    Args:
        filename: Name of the CSV file to load (e.g., 'flights.csv')
    """
    return flight_processor.load_and_process_flights(filename)

@mcp.tool()
async def flight_summary(filename: str) -> str:
    """Get comprehensive summary of flight data.
    
    Args:
        filename: Name of the loaded flight data file
    """
    return flight_processor.get_flight_summary(filename)

@mcp.tool()
async def cheapest_flights(filename: str, route: Optional[str] = None, limit: int = 10) -> str:
    """Find the cheapest flights overall or for a specific route.
    
    Args:
        filename: Name of the loaded flight data file
        route: Optional route in format "FROM-TO" (e.g., "BOS-ORD")
        limit: Number of cheapest flights to return
    """
    return flight_processor.find_cheapest_flights(filename, route, limit)

@mcp.tool()
async def airline_performance(filename: str) -> str:
    """Analyze performance metrics for all airlines.
    
    Args:
        filename: Name of the loaded flight data file
    """
    return flight_processor.analyze_airline_performance(filename)

@mcp.tool()
async def route_analysis(filename: str, top_n: int = 10) -> str:
    """Analyze most popular routes and their characteristics.
    
    Args:
        filename: Name of the loaded flight data file
        top_n: Number of top routes to analyze
    """
    return flight_processor.route_analysis(filename, top_n)

@mcp.tool()
async def price_trends_by_day(filename: str) -> str:
    """Analyze flight price trends by day of the week.
    
    Args:
        filename: Name of the loaded flight data file
    """
    return flight_processor.price_trends_by_day(filename)

@mcp.tool()
async def find_deals(filename: str, max_price: float, max_stops: int = 2) -> str:
    """Find flight deals under specified price and stops criteria.
    
    Args:
        filename: Name of the loaded flight data file
        max_price: Maximum price for deals
        max_stops: Maximum number of stops allowed
    """
    return flight_processor.find_flight_deals(filename, max_price, max_stops)

@mcp.tool()
async def duration_price_analysis(filename: str) -> str:
    """Analyze relationship between flight duration and pricing.
    
    Args:
        filename: Name of the loaded flight data file
    """
    return flight_processor.duration_vs_price_analysis(filename)

@mcp.tool()
async def search_flights(filename: str, from_airport: str, to_airport: str, max_price: Optional[float] = None) -> str:
    """Search for flights between specific airports with optional price limit.
    
    Args:
        filename: Name of the loaded flight data file
        from_airport: Origin airport code (e.g., "BOS")
        to_airport: Destination airport code (e.g., "ORD")
        max_price: Optional maximum price filter
    """
    if filename not in flight_processor.loaded_datasets:
        return f"Dataset {filename} not loaded."
    
    try:
        df = flight_processor.loaded_datasets[filename]
        
        # Filter flights
        results = df[
            (df['From'].str.upper() == from_airport.upper()) &
            (df['To'].str.upper() == to_airport.upper())
        ]
        
        if max_price:
            results = results[results['Price_Numeric'] <= max_price]
        
        if results.empty:
            return f"No flights found from {from_airport} to {to_airport}" + (f" under ${max_price}" if max_price else "")
        
        # Sort by price
        results = results.sort_values('Price_Numeric')
        
        output = [f"Flights from {from_airport} to {to_airport}" + (f" (≤${max_price})" if max_price else "")]
        output.append("=" * 50)
        
        for _, flight in results.head(20).iterrows():
            output.append(f"{flight['Airline']} - ${flight['Price_Numeric']:.2f}")
            output.append(f"  Date: {flight['Date'].strftime('%Y-%m-%d')} ({flight['Day_of_Week']})")
            output.append(f"  Duration: {flight['Flight_Duration']} | Stops: {flight['Stops']}")
            output.append(f"  Times: {flight['Time_from']} → {flight['Time_to']}")
            output.append("")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error searching flights: {str(e)}"

@mcp.tool()
async def class_comparison(filename: str) -> str:
    """Compare flight prices across different class types.
    
    Args:
        filename: Name of the loaded flight data file
    """
    if filename not in flight_processor.loaded_datasets:
        return f"Dataset {filename} not loaded."
    
    try:
        df = flight_processor.loaded_datasets[filename]
        
        class_stats = df.groupby('class_type')['Price_Numeric'].agg(['count', 'mean', 'min', 'max', 'std']).round(2)
        
        result = ["Flight Class Price Comparison"]
        result.append("=" * 40)
        
        for class_type in class_stats.index:
            stats = class_stats.loc[class_type]
            result.append(f"\n{class_type}:")
            result.append(f"  Flights: {stats['count']:.0f}")
            result.append(f"  Avg Price: ${stats['mean']:.2f}")
            result.append(f"  Price Range: ${stats['min']:.2f} - ${stats['max']:.2f}")
            result.append(f"  Price Std Dev: ${stats['std']:.2f}")
        
        return "\n".join(result)
    except Exception as e:
        return f"Error analyzing class comparison: {str(e)}"

async def main():
    """Main function to run the FlightBookings MCP server."""
    logger.info("Starting FlightBookings MCP Server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream, 
            write_stream, 
            InitializationOptions(
                server_name="flightbookings-server",
                server_version="1.0.0",
                capabilities=mcp.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())