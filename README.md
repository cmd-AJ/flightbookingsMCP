# Flight Bookings System

A comprehensive flight booking management system built for handling flight reservations, passenger management, and booking operations.

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Configuration](#configuration)

## 🚀 Overview

This Flight Bookings System provides a complete solution for managing flight reservations, including passenger information, flight schedules, seat management, and booking confirmations. The system is designed to handle multiple airlines, routes, and booking scenarios.

## 📁 Project Structure

```
flightbookings/
├── data/                   # Data files and database
├── filesystem/             # File management utilities
│   └── mcp_server.py      # MCP server for file operations
        mcp_serverhttp.py      # implementado para localhost
├── host-cli/              # Command line interface
├── src/                   # Source code (main application)
├── tests/                 # Test files
├── docs/                  # Documentation
├── config/                # Configuration files
└── README.md             # This file
```

## ✨ Features

- **Flight Management**
  - Add, update, and delete flight schedules
  - Manage multiple airlines and aircraft types
  - Route and destination management

- **Booking System**
  - Real-time seat availability
  - Passenger information management
  - Booking confirmation and ticketing
  - Payment processing integration

- **Search & Filtering**
  - Search flights by destination, date, and time
  - Filter by price, airline, and flight duration
  - Advanced search with multiple criteria

- **User Management**
  - Customer registration and authentication
  - Admin panel for system management
  - Role-based access control

- **Reporting**
  - Booking reports and analytics
  - Revenue tracking
  - Flight occupancy statistics

## 🔧 Prerequisites

Before running this project, ensure you have the following installed:

- Python 3.8 or higher
- Git
- Virtual environment (venv or conda)
- Database system (SQLite/PostgreSQL/MySQL)

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/flightbookings.git
   cd flightbookings
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## 🖥️ Usage

### Starting the Application

```bash
# Development server
python mcp_server.py

#Utilizado para conexion y handshakes de http
python mcp_serverhttp.py 

python mcp_server.py


### Command Line Interface

```bash
# Using the CLI tool
cd host-cli
python cli.py 


```

## 📚 API Documentation

### Authentication
All API endpoints require authentication except for public flight search.

```bash
# Get access token
POST /api/auth/login
{
    "username": "your_username",
    "password": "your_password"
}
```

### Flight Endpoints

```bash
# Search flights
GET /api/flights/search?from=NYC&to=LON&date=2024-12-25

# Get flight details
GET /api/flights/{flight_id}

# Create new flight (Admin only)
POST /api/flights/
```

### Booking Endpoints

```bash
# Create booking
POST /api/bookings/
{
    "flight_id": 123,
    "passenger_details": {...},
    "seat_preference": "window"
}

# Get booking details
GET /api/bookings/{booking_id}

# Cancel booking
DELETE /api/bookings/{booking_id}
```

## 🗄️ Database Schema

### Core Tables

- **flights**: Flight schedules and details
- **bookings**: Customer bookings and reservations
- **passengers**: Passenger information
- **airlines**: Airline information
- **aircraft**: Aircraft types and configurations
- **airports**: Airport codes and details

### Relationships

```sql
flights -> airlines (many-to-one)
flights -> aircraft (many-to-one)
bookings -> flights (many-to-one)
bookings -> passengers (many-to-one)
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database
MONGO_URI=URL

# Security
GOOGLE_API_KEY="codigo"

# External APIs
flightbookin-API=https://flightbookingU.fastmcp.app/mcp



Connection with claude

"mcpServers": {
    "filesystem-git": {
      "command": "python",
      "args": ["mcp_server.py"]
      }
}