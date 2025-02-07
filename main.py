import logging
import secrets

from logging.handlers import RotatingFileHandler
from typing import Optional

import uvicorn

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, validator

from configs.config import (
    CLICKHOUSE_FAST_API_DOCS_PATH,
    CLICKHOUSE_FAST_API_HOST,
    CLICKHOUSE_FAST_API_PASSWORD,
    CLICKHOUSE_FAST_API_PORT,
    CLICKHOUSE_FAST_API_USERNAME,
    CLICKHOUSE_SERVICE_CONFIG,
)
from handlers.clickhouse_scaling import ClickHouseAPI, ClickHouseError
from validators.scaling_options import MIN_IDLE_TIMEOUT_MINUTES, RAM, REPLICAS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
file_handler = RotatingFileHandler("app.log", maxBytes=1024 * 1024, backupCount=5)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

app = FastAPI(docs_url=None, redoc_url=None)
security = HTTPBasic()


# Request Models
class ServiceCredentials(BaseModel):
    service_id: str = Field(..., description="Service ID for authentication")
    username: str = Field(..., description="Service username for authentication")
    password: str = Field(..., description="Service password for authentication")

    class Config:
        json_schema_extra = {"description": "Service credentials for authentication"}


class ScalingRequest(ServiceCredentials):
    min_memory_gb: int = Field(..., description="Minimum memory in GB", example=RAM[0])
    max_memory_gb: int = Field(..., description="Maximum memory in GB", example=RAM[2])
    num_replicas: Optional[int] = Field(
        None, description=f"Number of replicas (options: {REPLICAS})", example=REPLICAS[0]
    )
    idle_scaling: Optional[bool] = Field(
        None, description="Enable/disable idle scaling", example=True
    )
    idle_timeout_minutes: Optional[int] = Field(
        None,
        description=f"Idle timeout in minutes (minimum: {MIN_IDLE_TIMEOUT_MINUTES})",
        example=MIN_IDLE_TIMEOUT_MINUTES,
    )

    @classmethod
    @validator("min_memory_gb")
    def validate_min_memory(cls, v):
        if v not in RAM:
            raise ValueError(f"min_memory_gb must be one of {RAM}")
        return v

    @classmethod
    @validator("max_memory_gb")
    def validate_max_memory(cls, v, values):
        if v not in RAM:
            raise ValueError(f"max_memory_gb must be one of {RAM}")
        if "min_memory_gb" in values and v < values["min_memory_gb"]:
            raise ValueError("max_memory_gb must be greater than or equal to min_memory_gb")
        return v

    @classmethod
    @validator("num_replicas")
    def validate_replicas(cls, v):
        if v is not None and v not in REPLICAS:
            raise ValueError(f"num_replicas must be one of {REPLICAS}")
        return v

    @classmethod
    @validator("idle_timeout_minutes")
    def validate_idle_timeout(cls, v):
        if v is not None and v < MIN_IDLE_TIMEOUT_MINUTES:
            raise ValueError(f"idle_timeout_minutes must be at least {MIN_IDLE_TIMEOUT_MINUTES}")
        return v

    class Config:
        json_schema_extra = {
            "description": "Request model for scaling configuration. Values will be validated against ClickHouse Cloud's allowed configurations."
        }


def get_admin_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Authenticate admin user for documentation access."""
    is_admin = secrets.compare_digest(
        credentials.username, CLICKHOUSE_FAST_API_USERNAME
    ) and secrets.compare_digest(credentials.password, CLICKHOUSE_FAST_API_PASSWORD)

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_clickhouse_api(credentials: HTTPBasicCredentials) -> ClickHouseAPI:
    """
    Authenticate user and return ClickHouseAPI instance for their service.
    Raises HTTPException if authentication fails.
    """
    is_admin = secrets.compare_digest(
        credentials.username, CLICKHOUSE_FAST_API_USERNAME
    ) and secrets.compare_digest(credentials.password, CLICKHOUSE_FAST_API_PASSWORD)

    if is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin credentials cannot be used for API access",
            headers={"WWW-Authenticate": "Basic"},
        )

    for service_name, service_config in CLICKHOUSE_SERVICE_CONFIG["services"].items():
        if secrets.compare_digest(
            credentials.username, service_config["username"]
        ) and secrets.compare_digest(credentials.password, service_config["password"]):
            logger.info(f"Authenticated service: {service_name}")
            return ClickHouseAPI(service_id=service_config["service_id"])

    logger.warning(f"Failed authentication attempt from user: {credentials.username}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def get_api_dependency(credentials: HTTPBasicCredentials = Depends(security)) -> ClickHouseAPI:
    """Dependency injection for API endpoints."""
    return get_clickhouse_api(credentials)


@app.get(f"{CLICKHOUSE_FAST_API_DOCS_PATH}", include_in_schema=False)
async def get_documentation(username: str = Depends(get_admin_auth)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Documentation")


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema(username: str = Depends(get_admin_auth)):
    return get_openapi(
        title="ClickHouse Scaling API",
        version="1.0.0",
        description="API for managing ClickHouse service scaling",
        routes=app.routes,
    )


def authenticate_service(request: ScalingRequest) -> str:
    """
    Authenticate service using provided credentials.
    Returns service_name if authentication successful, raises HTTPException otherwise.
    """
    for service_name, service_config in CLICKHOUSE_SERVICE_CONFIG["services"].items():
        if (
            secrets.compare_digest(request.service_id, service_config["service_id"])
            and secrets.compare_digest(request.username, service_config["username"])
            and secrets.compare_digest(request.password, service_config["password"])
        ):
            return service_name

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid service credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def authenticate_service_basic(credentials: HTTPBasicCredentials, service_id: str) -> str:
    """
    Authenticate service using HTTP Basic Auth credentials and service_id.
    Returns service_name if authentication successful, raises HTTPException otherwise.
    """

    is_admin = secrets.compare_digest(
        credentials.username, CLICKHOUSE_FAST_API_USERNAME
    ) and secrets.compare_digest(credentials.password, CLICKHOUSE_FAST_API_PASSWORD)

    if is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin credentials cannot be used for API access",
            headers={"WWW-Authenticate": "Basic"},
        )

    matching_service = None
    matching_service_name = None

    for service_name, service_config in CLICKHOUSE_SERVICE_CONFIG["services"].items():
        if secrets.compare_digest(service_id, service_config["service_id"]):
            matching_service = service_config
            matching_service_name = service_name
            break

    if not matching_service:
        logger.warning(f"Invalid service_id attempt: {service_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service_id",
            headers={"WWW-Authenticate": "Basic"},
        )

    if not (
        secrets.compare_digest(credentials.username, matching_service["username"])
        and secrets.compare_digest(credentials.password, matching_service["password"])
    ):
        logger.warning(
            f"Invalid credentials for service_id {service_id} from user: {credentials.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials for this service",
            headers={"WWW-Authenticate": "Basic"},
        )

    logger.info(f"Successfully authenticated service: {matching_service_name}")
    return matching_service_name


# Endpoints
@app.post("/scaling")
async def update_scaling(request: ScalingRequest):
    """
    Update the scaling configuration for the ClickHouse service.
    Service is authenticated using provided credentials and parameters are validated against allowed values.
    """
    try:
        service_name = authenticate_service(request)
        logger.info(f"Authenticated service: {service_name}")

        api = ClickHouseAPI(service_id=request.service_id)

        return api.update_replica_scaling(
            min_memory_gb=request.min_memory_gb,
            max_memory_gb=request.max_memory_gb,
            num_replicas=request.num_replicas,
            idle_scaling=request.idle_scaling,
            idle_timeout_minutes=request.idle_timeout_minutes,
        )
    except ClickHouseError as e:
        logger.error(f"Error updating scaling configuration: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@app.get("/service/state")
async def get_service_state(
    service_id: str,
    username: str,
    password: str,
):
    """
    Get the current state of the ClickHouse service.
    Service is authenticated using provided credentials.
    """
    try:
        credentials = ServiceCredentials(
            service_id=service_id, username=username, password=password
        )

        service_name = authenticate_service(credentials)
        logger.info(f"Authenticated service: {service_name}")

        api = ClickHouseAPI(service_id=service_id)

        return api.fetch_service_state()
    except ClickHouseError as e:
        logger.error(f"Error fetching service state: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@app.get("/service/config")
async def get_service_config(
    service_id: str,
    username: str,
    password: str,
):
    """
    Get the current configuration of the ClickHouse service.
    Service is authenticated using provided credentials.
    """
    try:
        credentials = ServiceCredentials(
            service_id=service_id, username=username, password=password
        )

        service_name = authenticate_service(credentials)
        logger.info(f"Authenticated service: {service_name}")

        api = ClickHouseAPI(service_id=service_id)

        return api.fetch_service_config()
    except ClickHouseError as e:
        logger.error(f"Error fetching service configuration: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@app.get("/service/ip-access-list")
async def get_ip_access_list(
    service_id: str,
    username: str,
    password: str,
):
    """
    Get the IP access list configuration of the ClickHouse service.
    Service is authenticated using provided credentials.
    """
    try:
        credentials = ServiceCredentials(
            service_id=service_id, username=username, password=password
        )

        service_name = authenticate_service(credentials)
        logger.info(f"Authenticated service: {service_name}")

        api = ClickHouseAPI(service_id=service_id)

        return api.fetch_ip_access_list()
    except ClickHouseError as e:
        logger.error(f"Error fetching IP access list: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@app.get("/service/details")
async def get_service_details(
    service_id: str,
    username: str,
    password: str,
):
    """
    Get complete details of the ClickHouse service.
    Service is authenticated using provided credentials.
    """
    try:
        credentials = ServiceCredentials(
            service_id=service_id, username=username, password=password
        )

        service_name = authenticate_service(credentials)
        logger.info(f"Authenticated service: {service_name}")

        api = ClickHouseAPI(service_id=service_id)

        return api.fetch_service_details()
    except ClickHouseError as e:
        logger.error(f"Error fetching service details: {e.message}")
        raise HTTPException(
            status_code=e.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=CLICKHOUSE_FAST_API_HOST,
        port=int(CLICKHOUSE_FAST_API_PORT),
        reload=True,
    )
