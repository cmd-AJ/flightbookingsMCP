import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class FlightDataProcessor:
    def __init__(self, data_directory: str = "data"):
        self.data_directory = Path(data_directory)
        self.loaded_datasets: Dict[str, pd.DataFrame] = {}
        self.data_directory.mkdir(exist_ok=True)
        
        # Airport code mappings for major cities
        self.airport_cities = {
            'BOS': 'Boston', 'ORD': 'Chicago', 'LAX': 'Los Angeles',
            'JFK': 'New York', 'LGA': 'New York', 'EWR': 'Newark',
            'DFW': 'Dallas', 'ATL': 'Atlanta', 'DEN': 'Denver',
            'SEA': 'Seattle', 'SFO': 'San Francisco', 'MIA': 'Miami',
            'PHX': 'Phoenix', 'LAS': 'Las Vegas', 'MCO': 'Orlando'
        }
    
    def load_and_process_flights(self, filename: str) -> str:
        """Load flight data CSV and perform initial processing."""
        try:
            filepath = self.data_directory / filename
            if not filepath.exists():
                return f"File {filename} not found in {self.data_directory}"
            
            df = pd.read_csv(filepath)
            
            # Process flight data
            df = self._process_flight_data(df)
            
            self.loaded_datasets[filename] = df
            
            return f"Successfully loaded {filename}: {len(df)} flights, {len(df.columns)} fields"
        except Exception as e:
            return f"Error loading {filename}: {str(e)}"
    
    def _process_flight_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean flight data."""
        df_processed = df.copy()
        
        # Convert date to datetime
        df_processed['Date'] = pd.to_datetime(df_processed['Date'])
        
        # Extract price as numeric value
        df_processed['Price_Numeric'] = df_processed['Flight_price'].str.replace('$', '').str.replace(',', '').astype(float)
        
        # Parse flight duration to minutes
        df_processed['Duration_Minutes'] = df_processed['Flight_Duration'].apply(self._parse_duration)
        
        # Extract number of stops
        df_processed['Stops_Numeric'] = df_processed['Stops'].apply(self._parse_stops)
        
        # Add day of week
        df_processed['Day_of_Week'] = df_processed['Date'].dt.day_name()
        
        # Add month name
        df_processed['Month'] = df_processed['Date'].dt.month_name()
        
        # Add route (From-To)
        df_processed['Route'] = df_processed['From'] + '-' + df_processed['To']
        
        # Add city names if available
        df_processed['From_City'] = df_processed['From'].map(self.airport_cities).fillna(df_processed['From'])
        df_processed['To_City'] = df_processed['To'].map(self.airport_cities).fillna(df_processed['To'])
        
        return df_processed
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse flight duration string to minutes."""
        try:
            hours = 0
            minutes = 0
            
            # Extract hours
            hour_match = re.search(r'(\d+)h', duration_str)
            if hour_match:
                hours = int(hour_match.group(1))
            
            # Extract minutes
            min_match = re.search(r'(\d+)m', duration_str)
            if min_match:
                minutes = int(min_match.group(1))
            
            return hours * 60 + minutes
        except:
            return 0
    
    def _parse_stops(self, stops_str: str) -> int:
        """Parse stops string to numeric value."""
        if 'nonstop' in stops_str.lower():
            return 0
        elif '1 stop' in stops_str:
            return 1
        elif '2 stop' in stops_str:
            return 2
        else:
            # Extract number if present
            numbers = re.findall(r'\d+', stops_str)
            return int(numbers[0]) if numbers else 0
    
    def get_flight_summary(self, filename: str) -> str:
        """Get comprehensive flight data summary."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        summary = []
        
        summary.append(f"Flight Data Summary for {filename}")
        summary.append("=" * 50)
        
        # Basic stats
        summary.append(f"Total flights: {len(df):,}")
        summary.append(f"Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
        summary.append(f"Airlines: {df['Airline'].nunique()} ({', '.join(df['Airline'].unique()[:5])}...)")
        summary.append(f"Routes: {df['Route'].nunique()} unique routes")
        summary.append(f"Average price: ${df['Price_Numeric'].mean():.2f}")
        summary.append(f"Price range: ${df['Price_Numeric'].min():.2f} - ${df['Price_Numeric'].max():.2f}")
        
        return "\n".join(summary)
    
    def find_cheapest_flights(self, filename: str, route: Optional[str] = None, limit: int = 10) -> str:
        """Find cheapest flights overall or for specific route."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        
        if route:
            filtered_df = df[df['Route'].str.upper() == route.upper()]
            if filtered_df.empty:
                return f"No flights found for route {route}"
        else:
            filtered_df = df
        
        cheapest = filtered_df.nsmallest(limit, 'Price_Numeric')
        
        result = [f"Cheapest {limit} flights" + (f" for route {route}" if route else "")]
        result.append("-" * 50)
        
        for _, flight in cheapest.iterrows():
            result.append(f"{flight['Airline']}: {flight['From']}-{flight['To']} on {flight['Date'].strftime('%Y-%m-%d')}")
            result.append(f"  Price: ${flight['Price_Numeric']:.2f}, Duration: {flight['Flight_Duration']}, Stops: {flight['Stops']}")
            result.append("")
        
        return "\n".join(result)
    
    def analyze_airline_performance(self, filename: str) -> str:
        """Analyze airline performance metrics."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        
        airline_stats = df.groupby('Airline').agg({
            'Price_Numeric': ['mean', 'min', 'max', 'count'],
            'Duration_Minutes': 'mean',
            'Stops_Numeric': 'mean'
        }).round(2)
        
        result = ["Airline Performance Analysis"]
        result.append("=" * 50)
        
        for airline in airline_stats.index:
            stats = airline_stats.loc[airline]
            result.append(f"\n{airline}:")
            result.append(f"  Flights: {stats[('Price_Numeric', 'count')]:.0f}")
            result.append(f"  Avg Price: ${stats[('Price_Numeric', 'mean')]:.2f}")
            result.append(f"  Price Range: ${stats[('Price_Numeric', 'min')]:.2f} - ${stats[('Price_Numeric', 'max')]:.2f}")
            result.append(f"  Avg Duration: {stats[('Duration_Minutes', 'mean')]:.0f} minutes")
            result.append(f"  Avg Stops: {stats[('Stops_Numeric', 'mean')]:.1f}")
        
        return "\n".join(result)
    
    def route_analysis(self, filename: str, top_n: int = 10) -> str:
        """Analyze most popular routes and their characteristics."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        
        route_stats = df.groupby('Route').agg({
            'Price_Numeric': ['mean', 'min', 'max', 'count'],
            'Duration_Minutes': 'mean',
            'Airline': 'nunique'
        }).round(2)
        
        # Sort by flight count
        route_stats = route_stats.sort_values(('Price_Numeric', 'count'), ascending=False).head(top_n)
        
        result = [f"Top {top_n} Routes Analysis"]
        result.append("=" * 50)
        
        for route in route_stats.index:
            stats = route_stats.loc[route]
            result.append(f"\n{route}:")
            result.append(f"  Flights: {stats[('Price_Numeric', 'count')]:.0f}")
            result.append(f"  Airlines: {stats[('Airline', 'nunique')]:.0f}")
            result.append(f"  Avg Price: ${stats[('Price_Numeric', 'mean')]:.2f}")
            result.append(f"  Price Range: ${stats[('Price_Numeric', 'min')]:.2f} - ${stats[('Price_Numeric', 'max')]:.2f}")
            result.append(f"  Avg Duration: {stats[('Duration_Minutes', 'mean')]:.0f} minutes")
        
        return "\n".join(result)
    
    def price_trends_by_day(self, filename: str) -> str:
        """Analyze price trends by day of week."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_stats = df.groupby('Day_of_Week')['Price_Numeric'].agg(['mean', 'count']).reindex(day_order)
        
        result = ["Price Trends by Day of Week"]
        result.append("=" * 40)
        
        for day in day_order:
            if day in day_stats.index:
                avg_price = day_stats.loc[day, 'mean']
                flight_count = day_stats.loc[day, 'count']
                result.append(f"{day}: ${avg_price:.2f} avg ({flight_count} flights)")
        
        # Find cheapest and most expensive days
        cheapest_day = day_stats['mean'].idxmin()
        most_expensive_day = day_stats['mean'].idxmax()
        
        result.append(f"\nCheapest day: {cheapest_day} (${day_stats.loc[cheapest_day, 'mean']:.2f})")
        result.append(f"Most expensive day: {most_expensive_day} (${day_stats.loc[most_expensive_day, 'mean']:.2f})")
        
        return "\n".join(result)
    
    def find_flight_deals(self, filename: str, max_price: float, max_stops: int = 2) -> str:
        """Find flight deals under specified criteria."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        
        deals = df[
            (df['Price_Numeric'] <= max_price) & 
            (df['Stops_Numeric'] <= max_stops)
        ].sort_values('Price_Numeric')
        
        if deals.empty:
            return f"No deals found under ${max_price} with {max_stops} or fewer stops."
        
        result = [f"Flight Deals (≤${max_price}, ≤{max_stops} stops)"]
        result.append("=" * 50)
        
        for _, deal in deals.head(15).iterrows():
            result.append(f"{deal['Route']} - {deal['Airline']}")
            result.append(f"  ${deal['Price_Numeric']:.2f} | {deal['Flight_Duration']} | {deal['Stops']} | {deal['Date'].strftime('%Y-%m-%d')}")
            result.append("")
        
        return "\n".join(result)
    
    def duration_vs_price_analysis(self, filename: str) -> str:
        """Analyze relationship between flight duration and price."""
        if filename not in self.loaded_datasets:
            return f"Dataset {filename} not loaded."
        
        df = self.loaded_datasets[filename]
        
        # Create duration bins
        df['Duration_Category'] = pd.cut(df['Duration_Minutes'], 
                                       bins=[0, 120, 300, 480, float('inf')],
                                       labels=['Short (<2h)', 'Medium (2-5h)', 'Long (5-8h)', 'Very Long (>8h)'])
        
        duration_stats = df.groupby('Duration_Category')['Price_Numeric'].agg(['mean', 'count', 'std']).round(2)
        
        result = ["Duration vs Price Analysis"]
        result.append("=" * 40)
        
        for category in duration_stats.index:
            stats = duration_stats.loc[category]
            result.append(f"\n{category}:")
            result.append(f"  Flights: {stats['count']:.0f}")
            result.append(f"  Avg Price: ${stats['mean']:.2f}")
            result.append(f"  Price Std Dev: ${stats['std']:.2f}")
        
        # Correlation analysis
        correlation = df['Duration_Minutes'].corr(df['Price_Numeric'])
        result.append(f"\nDuration-Price Correlation: {correlation:.3f}")
        
        if correlation > 0.3:
            result.append("Strong positive correlation - longer flights tend to be more expensive")
        elif correlation < -0.3:
            result.append("Strong negative correlation - longer flights tend to be cheaper")
        else:
            result.append("Weak correlation between duration and price")
        
        return "\n".join(result)