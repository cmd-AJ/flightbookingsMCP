import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from fastmcp import FastMCP
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import pandas as pd

# Create the MCP server
mcp = FastMCP("mongodb-flight-server")

load_dotenv()

# MongoDB connection configuration  
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "flight_bookings") 
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "flights")

# =============================================================================
# CONNECTION HELPERS
# =============================================================================
def get_mongo_client():
    """Create and return MongoDB client connection"""
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')
    return client

def get_collection():
    client = get_mongo_client()
    return client[MONGO_DATABASE][MONGO_COLLECTION]

# =============================================================================
# PARAMETER NORMALIZATION
# =============================================================================
def normalize_flight_params(params: dict) -> dict:
    """Normalize aliases like origin/destination/from/to into from_city/to_city."""
    aliases = {
        "origin": "from_city",
        "from": "from_city",
        "departure": "from_city",
        "departure_city": "from_city",

        "destination": "to_city",
        "to": "to_city",
        "arrival": "to_city",
        "arrival_city": "to_city",
    }
    normalized = {}
    for k, v in params.items():
        target_key = aliases.get(k, k)
        normalized[target_key] = v
    return normalized

# =============================================================================
# BASIC OPS
# =============================================================================
@mcp.tool()
def test_mongodb_connection() -> str:
    """Test MongoDB connection and show database info"""
    try:
        collection = get_collection()
        doc_count = collection.count_documents({})
        sample = collection.find_one()
        return json.dumps({
            "status": "Connected successfully", 
            "database": MONGO_DATABASE,
            "collection": MONGO_COLLECTION,
            "total_documents": doc_count,
            "sample_fields": list(sample.keys()) if sample else []
        }, indent=2)
    except Exception as e:
        return f"MongoDB connection failed: {str(e)}"

# =============================================================================
# FLIGHT SEARCH
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
    limit: int = 10,
    **kwargs
) -> str:
    """Search flights with multiple filters (accepts origin/destination aliases)."""
    try:
        params = normalize_flight_params({**locals(), **kwargs})
        from_city = params.get("from_city", "")
        to_city = params.get("to_city", "")

        query = {}
        if from_city: query["From"] = {"$regex": from_city, "$options": "i"}
        if to_city: query["To"] = {"$regex": to_city, "$options": "i"}
        if params.get("airline"): query["Airline"] = {"$regex": params["airline"], "$options": "i"}
        if params.get("class_type"): query["class_type"] = {"$regex": params["class_type"], "$options": "i"}
        if params.get("max_price", 0) > 0: query.setdefault("Flight_price", {})["$lte"] = params["max_price"]
        if params.get("min_price", 0) > 0: query.setdefault("Flight_price", {})["$gte"] = params["min_price"]
        if params.get("max_stops", -1) >= 0: query["Stops"] = {"$lte": params["max_stops"]}

        flights = list(get_collection().find(query).limit(int(params.get("limit", 10))))
        if not flights:
            return f"No flights found matching criteria: {json.dumps(query, indent=2)}"

        results = [{
            "airline": f.get("Airline", "N/A"),
            "route": f"{f.get('From', 'N/A')} → {f.get('To', 'N/A')}",
            "date": f.get("Date", "N/A"),
            "departure": f.get("Time_from", "N/A"),
            "arrival": f.get("Time_to", "N/A"),
            "duration": f.get("Flight_Duration", "N/A"),
            "stops": f.get("Stops", "N/A"),
            "class": f.get("class_type", "N/A"),
            "price": f.get("Flight_price", "N/A")
        } for f in flights]

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching flights: {str(e)}"

@mcp.tool()
def search_by_route(from_city: str = "", to_city: str = "", limit: int = 20, **kwargs) -> str:
    """Search flights for a specific route (accepts origin/destination aliases)."""
    try:
        params = normalize_flight_params({**locals(), **kwargs})
        from_city = params.get("from_city", "")
        to_city = params.get("to_city", "")

        query = {"From": {"$regex": from_city, "$options": "i"},
                 "To": {"$regex": to_city, "$options": "i"}}

        flights = list(get_collection().find(query).sort("Flight_price", 1).limit(int(params.get("limit", 20))))
        if not flights:
            return f"No flights found for route: {from_city} → {to_city}"

        results = [{
            "airline": f.get("Airline"),
            "date": f.get("Date"),
            "departure": f.get("Time_from"),
            "arrival": f.get("Time_to"),
            "duration": f.get("Flight_Duration"),
            "stops": f.get("Stops"),
            "class": f.get("class_type"),
            "price": f"${f.get('Flight_price', 0):,.2f}"
        } for f in flights]

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching route: {str(e)}"

@mcp.tool()
def search_cheapest_flights(
    origin: str = "",
    destination: str = "",
    limit: int = 10,
    max_stops: int = 2,
    **kwargs
) -> str:
    """Find the cheapest flights, optionally filtered by origin/destination aliases."""
    try:
        params = normalize_flight_params({**locals(), **kwargs})
        from_city = params.get("from_city", "")
        to_city = params.get("to_city", "")

        query = {}
        if params.get("max_stops", 2) >= 0: query["Stops"] = {"$lte": int(params["max_stops"])}
        if from_city: query["From"] = {"$regex": from_city, "$options": "i"}
        if to_city: query["To"] = {"$regex": to_city, "$options": "i"}

        flights = list(get_collection().find(query).sort("Flight_price", 1).limit(int(params.get("limit", 10))))
        if not flights:
            return f"No cheap flights found for {from_city} → {to_city}"

        results = [{
            "route": f"{f.get('From')} → {f.get('To')}",
            "airline": f.get("Airline"),
            "price": f"${f.get('Flight_price', 0):,.2f}",
            "stops": f.get("Stops"),
            "duration": f.get("Flight_Duration"),
            "class": f.get("class_type")
        } for f in flights]

        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error finding cheapest flights: {str(e)}"

# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    print("Starting MongoDB Flight Bookings MCP server...")
    try:
        print(test_mongodb_connection())
        mcp.run()
    except Exception as e:
        print(f"Error starting server: {e}")
