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
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Overview

This Flight Bookings System provides a complete solution for managing flight reservations, including passenger information, flight schedules, seat management, and booking confirmations. The system is designed to handle multiple airlines, routes, and booking scenarios.

## 📁 Project Structure

```
flightbookings/
├── data/                   # Data files and database
├── filesystem/             # File management utilities
│   └── mcp_server.py      # MCP server for file operations
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

4. **Set up the database**
   ```bash
   python manage.py migrate
   python manage.py create_sample_data
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
python manage.py runserver

# Production server
gunicorn app:application
```

### Command Line Interface

```bash
# Using the CLI tool
cd host-cli
python cli.py --help

# Example commands
python cli.py search --from "New York" --to "London" --date "2024-12-25"
python cli.py book --flight-id 123 --passenger "John Doe"
```

### MCP Server for File Operations

```bash
# Start the MCP server
cd filesystem
python mcp_server.py
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
DATABASE_URL=sqlite:///flightbookings.db
DATABASE_ENGINE=sqlite

# Security
SECRET_KEY=your-secret-key-here
DEBUG=False

# External APIs
PAYMENT_API_KEY=your-payment-api-key
AIRLINE_API_KEYS=api-keys-for-external-airlines

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Application Settings

Edit `config/settings.py` for:
- Database configurations
- Logging settings
- Cache configurations
- Third-party integrations

## 🛠️ Development

### Setting up Development Environment

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run tests**
   ```bash
   python -m pytest tests/
   ```

3. **Code formatting**
   ```bash
   black src/
   flake8 src/
   ```

4. **Database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### Development Workflow

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and test thoroughly
3. Run linting and formatting
4. Commit with descriptive messages
5. Push and create pull request

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_bookings.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Test Categories

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test component interactions
- **API Tests**: Test REST endpoints
- **End-to-End Tests**: Test complete user workflows

## 🚀 Deployment

### Production Deployment

1. **Set environment variables**
   ```bash
   export DEBUG=False
   export DATABASE_URL=postgresql://user:pass@host:port/dbname
   ```

2. **Install production dependencies**
   ```bash
   pip install -r requirements-prod.txt
   ```

3. **Run database migrations**
   ```bash
   python manage.py migrate --settings=config.production
   ```

4. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

5. **Start production server**
   ```bash
   gunicorn --bind 0.0.0.0:8000 app:application
   ```

### Docker Deployment

```bash
# Build Docker image
docker build -t flightbookings .

# Run container
docker run -p 8000:8000 flightbookings
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Contribution Guidelines

- Write clear, descriptive commit messages
- Include tests for new features
- Update documentation as needed
- Follow the existing code style
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions:

- 📧 Email: support@flightbookings.com
- 📱 Issues: [GitHub Issues](https://github.com/yourusername/flightbookings/issues)
- 📖 Documentation: [Wiki](https://github.com/yourusername/flightbookings/wiki)

## 🔄 Changelog

### v1.0.0 (Current)
- Initial release
- Basic flight booking functionality
- User authentication system
- Admin panel
- API endpoints

---

**Made with ❤️ by the Flight Bookings Team**
