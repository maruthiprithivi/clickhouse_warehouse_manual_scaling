# ClickHouse Cloud Manual Scaling Service

This service provides an external controlled request routing system for manual scaling of ClickHouse Cloud services. It allows multiple users to initiate scaling requests through a secure FastAPI service that handles user verification, service confirmation, and request routing.

![Architecture Diagram](docs/chc_manual_scaling.jpg)

## Features

- User verification and authentication
- Service confirmation before scaling
- Request routing to specific compute groups
- FastAPI-based REST endpoints
- Secure configuration management
- Comprehensive request validation

## System Architecture

The system consists of three main components:

1. **Manual Scaling Initiators**: End users who initiate scaling requests
2. **User Environment**: Contains the Scaling Service (FastAPI) that handles:
   - User Verification
   - Service Confirmation
   - Request Routing
3. **ClickHouse Cloud**: The target environment with multiple compute groups

## Prerequisites

- Python 3.13 or higher
- ClickHouse Cloud API credentials
- Access to ClickHouse Cloud services
- UV package manager (`pip install uv`)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/maruthiprithivi/clickhouse_warehouse_manual_scaling
cd ch_warehouse_manual_scaling
```

2. Create and activate a Python virtual environment:

```bash
uv venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

3. Install dependencies using UV:

```bash
uv sync
```

4. Install development dependencies (optional):

```bash
uv sync --only-dev
```

## Configuration

1. Copy the environment template:

```bash
cp configs/.env_template configs/.env
```

2. Update the `.env` file with your ClickHouse credentials:

```env
CLICKHOUSE_API_KEY=<your_api_key>
CLICKHOUSE_API_SECRET=<your_api_secret>
CLICKHOUSE_ORGANIZATION_ID=<your_org_id>
CLICKHOUSE_FAST_API_USERNAME=<api_username>
CLICKHOUSE_FAST_API_PASSWORD=<api_password>
CLICKHOUSE_FAST_API_PORT=8000
CLICKHOUSE_FAST_API_HOST=0.0.0.0
CLICKHOUSE_FAST_API_DOCS_PATH=/clickhouse/manual/scaling/docs
```

3. Configure organization settings in `configs/org_config.yaml`:

```yaml
cp configs/org_config.yaml_template configs/org_config.yaml
# Edit the file according to your organization's needs
```

## Running the Service

1. Start the FastAPI service:

```bash
make dev
```

2. Access the API documentation:

```
http://localhost:8000/clickhouse/manual/scaling/docs
```

## Development

### Code Quality

The project uses several tools to maintain code quality, specifically for code formatting and checking:

1. Install pre-commit:

```bash
uv add --dev pre-commit
```

2. Install pre-commit hooks:

```bash
pre-commit install
```

3. Run code formatting and linting:

```bash
make pre-commit
```

The pre-commit hooks include tools such as `ruff` and `ruff-format` for code formatting and checking.

## API Endpoints

The service provides the following main endpoints:

- `POST /scaling`: Initiate a scaling request for a ClickHouse service
- `GET /service/state`: Get the current state of the ClickHouse service
- `GET /service/config`: Get the current configuration of the ClickHouse service
- `GET /service/ip-access-list`: Get the current IP access list of the ClickHouse service
- `GET /service/details`: Get the complete details of the ClickHouse service

For detailed API documentation, visit the Swagger UI at `/clickhouse/manual/scaling/docs` when the service is running.

## Security

- All API endpoints are protected with authentication
- Environment variables are used for sensitive configuration
- Request validation ensures data integrity
- User verification is required for scaling operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Make sure to add a summary of the changes you made
5. Push to the branch
6. Create a Pull Request

## Support

For support, please [create an issue](https://github.com/maruthiprithivi/clickhouse_warehouse_manual_scaling/issues) in the repository.
