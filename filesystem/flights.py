#!/usr/bin/env python3

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastmcp import FastMCP
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import pandas as pd

# Create the MCP server
mcp = FastMCP("mongodb-flight-server")

load_dotenv()

# MongoDB connection configuration  
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "flight_bookings") 
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "flights")

def get_mongo_client():
    """Create and return MongoDB client connection"""
    try:
        client = MongoClient(MONGO_URI)
        
        # Test connection
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        raise Exception(f"Failed to connect to MongoDB: {str(e)}")

def get_collection():
    """Get the flights collection"""
    client = get_mongo_client()
    db = client[MONGO_DATABASE]
    return db[MONGO_COLLECTION]

# =============================================================================
# BASIC MONGODB OPERATIONS
# =============================================================================

def _test_connection():
    """Internal function to test MongoDB connection"""
    try:
        client = get_mongo_client()
        db = client[MONGO_DATABASE]
        collection = db[MONGO_COLLECTION]
        
        # Get basic stats
        doc_count = collection.count_documents({})
        
        # Get sample document
        sample = collection.find_one()
        
        result = {
            "status": "Connected successfully", 
            "database": MONGO_DATABASE,
            "collection": MONGO_COLLECTION,
            "total_documents": doc_count,
            "sample_fields": list(sample.keys()) if sample else []
        }
        
        return f"MongoDB Connection Test:\n{json.dumps(result, indent=2)}"
        
    except Exception as e:
        return f"MongoDB connection failed: {str(e)}"

@mcp.tool()
def test_mongodb_connection() -> str:
    """Test MongoDB connection and show database info"""
    return _test_connection()

@mcp.tool()
def get_database_stats() -> str:
    """Get comprehensive database statistics"""
    try:
        collection = get_collection()
        
        # Basic counts
        total_flights = collection.count_documents({})
        
        # Airline distribution
        airline_stats = list(collection.aggregate([
            {"$group": {"_id": "$Airline", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        
        # Class type distribution  
        class_stats = list(collection.aggregate([
            {"$group": {"_id": "$class_type", "count": {"$sum": 1}}}
        ]))
        
        # Route popularity (From -> To)
        route_stats = list(collection.aggregate([
            {"$group": {"_id": {"from": "$From", "to": "$To"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        
        # Price statistics
        price_stats = list(collection.aggregate([
            {"$group": {
                "_id": None,
                "avg_price": {"$avg": "$Flight_price"},
                "min_price": {"$min": "$Flight_price"},
                "max_price": {"$max": "$Flight_price"}
            }}
        ]))
        
        stats = {
            "total_flights": total_flights,
            "top_airlines": airline_stats,
            "class_distribution": class_stats,
            "popular_routes": [f"{r['_id']['from']} → {r['_id']['to']} ({r['count']})" for r in route_stats],
            "price_stats": price_stats[0] if price_stats else {}
        }
        
        return f"Database Statistics:\n{json.dumps(stats, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error getting database stats: {str(e)}"

# =============================================================================
# FLIGHT SEARCH OPERATIONS
# =============================================================================

@mcp.tool()
def search_flights(
    from_city: str = "",
    to_city: str = "",
    airline: str = "",
    class_type: str = "",
    max_price: float = 0,
    min_price: float = 0,
    max_stops: int = -1,
    limit: int = 10
) -> str:
    """Search flights with multiple filters"""
    try:
        collection = get_collection()
        
        # Build query
        query = {}
        
        if from_city:
            query["From"] = {"$regex": from_city, "$options": "i"}
        if to_city:
            query["To"] = {"$regex": to_city, "$options": "i"}
        if airline:
            query["Airline"] = {"$regex": airline, "$options": "i"}
        if class_type:
            query["class_type"] = {"$regex": class_type, "$options": "i"}
        if max_price > 0:
            query["Flight_price"] = {"$lte": max_price}
        if min_price > 0:
            if "Flight_price" in query:
                query["Flight_price"]["$gte"] = min_price
            else:
                query["Flight_price"] = {"$gte": min_price}
        if max_stops >= 0:
            query["Stops"] = {"$lte": max_stops}
        
        # Execute search
        flights = list(collection.find(query).limit(limit))
        
        # Format results
        if not flights:
            return f"No flights found matching criteria: {json.dumps(query, indent=2)}"
        
        results = []
        for flight in flights:
            flight["_id"] = str(flight["_id"])  # Convert ObjectId to string
            results.append({
                "airline": flight.get("Airline", "N/A"),
                "route": f"{flight.get('From', 'N/A')} → {flight.get('To', 'N/A')}",
                "date": flight.get("Date", "N/A"),
                "departure": flight.get("Time_from", "N/A"),
                "arrival": flight.get("Time_to", "N/A"),
                "duration": flight.get("Flight_Duration", "N/A"),
                "stops": flight.get("Stops", "N/A"),
                "class": flight.get("class_type", "N/A"),
                "price": flight.get("Flight_price", "N/A")
            })
        
        return f"Found {len(results)} flights:\n{json.dumps(results, indent=2)}"
        
    except Exception as e:
        return f"Error searching flights: {str(e)}"

@mcp.tool()
def search_by_route(from_city: str, to_city: str, limit: int = 20) -> str:
    """Search flights for a specific route"""
    try:
        collection = get_collection()
        
        query = {
            "From": {"$regex": from_city, "$options": "i"},
            "To": {"$regex": to_city, "$options": "i"}
        }
        
        flights = list(collection.find(query).sort("Flight_price", 1).limit(limit))
        
        if not flights:
            return f"No flights found for route: {from_city} → {to_city}"
        
        results = []
        for flight in flights:
            results.append({
                "airline": flight.get("Airline"),
                "date": flight.get("Date"),
                "departure": flight.get("Time_from"),
                "arrival": flight.get("Time_to"),
                "duration": flight.get("Flight_Duration"),
                "stops": flight.get("Stops"),
                "class": flight.get("class_type"),
                "price": f"${flight.get('Flight_price', 0):,.2f}"
            })
        
        return f"Flights from {from_city} to {to_city} (sorted by price):\n{json.dumps(results, indent=2)}"
        
    except Exception as e:
        return f"Error searching route: {str(e)}"

@mcp.tool()
def search_cheapest_flights(limit: int = 10, max_stops: int = 2) -> str:
    """Find the cheapest flights with optional stop limit"""
    try:
        collection = get_collection()
        
        query = {}
        if max_stops >= 0:
            query["Stops"] = {"$lte": max_stops}
        
        flights = list(collection.find(query).sort("Flight_price", 1).limit(limit))
        
        results = []
        for flight in flights:
            results.append({
                "route": f"{flight.get('From')} → {flight.get('To')}",
                "airline": flight.get("Airline"),
                "price": f"${flight.get('Flight_price', 0):,.2f}",
                "stops": flight.get("Stops"),
                "duration": flight.get("Flight_Duration"),
                "class": flight.get("class_type")
            })
        
        return f"Cheapest {limit} flights:\n{json.dumps(results, indent=2)}"
        
    except Exception as e:
        return f"Error finding cheapest flights: {str(e)}"

# =============================================================================
# ANALYTICS AND AGGREGATIONS
# =============================================================================

@mcp.tool()
def airline_analysis(airline: str = "") -> str:
    """Analyze flights by airline"""
    try:
        collection = get_collection()
        
        if airline:
            # Specific airline analysis
            query = {"Airline": {"$regex": airline, "$options": "i"}}
            flights = list(collection.find(query))
            
            if not flights:
                return f"No flights found for airline: {airline}"
            
            total_flights = len(flights)
            avg_price = sum(f.get("Flight_price", 0) for f in flights) / total_flights
            routes = set(f"{f.get('From')} → {f.get('To')}" for f in flights)
            
            result = {
                "airline": airline,
                "total_flights": total_flights,
                "average_price": f"${avg_price:.2f}",
                "unique_routes": len(routes),
                "sample_routes": list(routes)[:10]
            }
        else:
            # All airlines comparison
            pipeline = [
                {"$group": {
                    "_id": "$Airline",
                    "flight_count": {"$sum": 1},
                    "avg_price": {"$avg": "$Flight_price"},
                    "min_price": {"$min": "$Flight_price"},
                    "max_price": {"$max": "$Flight_price"}
                }},
                {"$sort": {"flight_count": -1}}
            ]
            
            result = list(collection.aggregate(pipeline))
            
        return f"Airline Analysis:\n{json.dumps(result, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error in airline analysis: {str(e)}"

@mcp.tool()
def route_analysis(limit: int = 15) -> str:
    """Analyze most popular routes and their pricing"""
    try:
        collection = get_collection()
        
        pipeline = [
            {"$group": {
                "_id": {"from": "$From", "to": "$To"},
                "flight_count": {"$sum": 1},
                "avg_price": {"$avg": "$Flight_price"},
                "min_price": {"$min": "$Flight_price"},
                "max_price": {"$max": "$Flight_price"},
                "airlines": {"$addToSet": "$Airline"}
            }},
            {"$sort": {"flight_count": -1}},
            {"$limit": limit}
        ]
        
        routes = list(collection.aggregate(pipeline))
        
        results = []
        for route in routes:
            results.append({
                "route": f"{route['_id']['from']} → {route['_id']['to']}",
                "flights": route["flight_count"],
                "avg_price": f"${route['avg_price']:.2f}",
                "price_range": f"${route['min_price']:.2f} - ${route['max_price']:.2f}",
                "airlines": len(route["airlines"])
            })
        
        return f"Top {limit} Routes Analysis:\n{json.dumps(results, indent=2)}"
        
    except Exception as e:
        return f"Error in route analysis: {str(e)}"

@mcp.tool()
def price_distribution_analysis() -> str:
    """Analyze price distribution across different segments"""
    try:
        collection = get_collection()
        
        # Price ranges
        price_ranges = [
            {"$match": {"Flight_price": {"$lte": 200}}},
            {"$match": {"Flight_price": {"$gt": 200, "$lte": 500}}},
            {"$match": {"Flight_price": {"$gt": 500, "$lte": 1000}}},
            {"$match": {"Flight_price": {"$gt": 1000}}}
        ]
        
        range_labels = ["Budget ($0-200)", "Economy ($200-500)", "Premium ($500-1000)", "Luxury ($1000+)"]
        
        results = []
        for i, price_range in enumerate(price_ranges):
            count = collection.count_documents(price_range["$match"])
            results.append({
                "category": range_labels[i],
                "flight_count": count
            })
        
        # Class type distribution
        class_pipeline = [
            {"$group": {
                "_id": "$class_type",
                "count": {"$sum": 1},
                "avg_price": {"$avg": "$Flight_price"}
            }},
            {"$sort": {"avg_price": 1}}
        ]
        
        class_dist = list(collection.aggregate(class_pipeline))
        
        analysis = {
            "price_ranges": results,
            "class_distribution": class_dist
        }
        
        return f"Price Distribution Analysis:\n{json.dumps(analysis, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error in price analysis: {str(e)}"

# =============================================================================
# DATA EXPORT OPERATIONS
# =============================================================================

@mcp.tool()
def export_flights_to_csv(
    query_filter: str = "{}",
    filename: str = "flights_export.csv",
    limit: int = 1000
) -> str:
    """Export flights to CSV file with optional filtering"""
    try:
        collection = get_collection()
        
        # Parse query filter
        try:
            query = json.loads(query_filter)
        except json.JSONDecodeError:
            query = {}
        
        # Get flights
        flights = list(collection.find(query).limit(limit))
        
        if not flights:
            return f"No flights found matching filter: {query_filter}"
        
        # Convert to DataFrame
        df = pd.DataFrame(flights)
        
        # Remove MongoDB ObjectId and convert to string if present
        if '_id' in df.columns:
            df['_id'] = df['_id'].astype(str)
        
        # Save to CSV
        df.to_csv(filename, index=False)
        
        return f"Successfully exported {len(flights)} flights to {filename}"
        
    except Exception as e:
        return f"Error exporting flights: {str(e)}"

@mcp.tool()
def get_sample_flights(count: int = 5) -> str:
    """Get sample flights for testing/preview"""
    try:
        collection = get_collection()
        
        # Get random sample
        pipeline = [{"$sample": {"size": count}}]
        flights = list(collection.aggregate(pipeline))
        
        # Clean up ObjectId
        for flight in flights:
            flight["_id"] = str(flight["_id"])
        
        return f"Sample flights ({count}):\n{json.dumps(flights, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error getting sample flights: {str(e)}"

# =============================================================================
# CONFIGURATION AND SETUP
# =============================================================================

@mcp.tool()
def show_server_config() -> str:
    """Show current MongoDB server configuration"""
    config_display = {
        "mongo_uri": MONGO_URI.replace(MONGO_URI.split('@')[0].split('://')[1] + '@', '****@') if '@' in MONGO_URI else MONGO_URI,
        "database": MONGO_DATABASE,
        "collection": MONGO_COLLECTION
    }
    
    return f"MongoDB Server Configuration:\n{json.dumps(config_display, indent=2)}"

# =============================================================================
# RUN THE SERVER
# =============================================================================

if __name__ == "__main__":
    print("Starting MongoDB Flight Bookings MCP server...")
    print(f"Database: {MONGO_DATABASE}")
    print(f"Collection: {MONGO_COLLECTION}")
    
    try:
        # Test connection on startup using internal function
        test_result = _test_connection()
        print("Connection test:", test_result[:100] + "..." if len(test_result) > 100 else test_result)
        
        mcp.run()
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()