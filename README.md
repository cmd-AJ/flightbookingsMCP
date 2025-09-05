# Flight Data MCP Server

Este servidor MCP expone funcionalidades para interactuar con datos de vuelos.

## Funcionalidades:
- Consultar vuelos más baratos.
- Obtener un resumen general de los datos de vuelos.
- Mantener y recuperar el contexto de la conversación.

## Instrucciones para ejecutar:
1. Clona el repositorio.
2. Instala las dependencias: `pip install -r requirements.txt`.
3. Ejecuta el servidor: `python mcp_server.py`.

## Uso de la API:
Los métodos disponibles incluyen:
- `get_cheapest_flights(route, limit)`
- `get_flight_summary()`
- `set_user_context(user_id, context)`
- `get_user_context(user_id)`
