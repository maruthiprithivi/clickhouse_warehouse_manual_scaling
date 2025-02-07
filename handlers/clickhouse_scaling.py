from typing import Any, Optional, Union

import requests

from requests.auth import HTTPBasicAuth

from configs.config import CLICKHOUSE_API_KEY, CLICKHOUSE_API_SECRET, CLICKHOUSE_ORGANIZATION_ID
from validators.scaling_options import MIN_IDLE_TIMEOUT_MINUTES, RAM, REPLICAS


class ClickHouseError(Exception):
    """Custom exception for ClickHouse API errors"""

    def __init__(
        self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class ClickHouseAPI:
    """ClickHouse API handler with service-specific configuration"""

    def __init__(
        self,
        service_id: str,
        api_key: str = CLICKHOUSE_API_KEY,
        api_secret: str = CLICKHOUSE_API_SECRET,
        org_id: str = CLICKHOUSE_ORGANIZATION_ID,
    ):
        self.service_id = service_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.org_id = org_id
        self.auth = HTTPBasicAuth(self.api_key, self.api_secret)

    def update_replica_scaling(
        self,
        min_memory_gb: int,
        max_memory_gb: int,
        num_replicas: Optional[int] = None,
        idle_scaling: Optional[bool] = None,
        idle_timeout_minutes: Optional[int] = None,
    ) -> dict[str, str]:
        """
        Update the replica scaling configuration for the ClickHouse service.

        Returns:
            dict[str, str]: Success message or error details
        Raises:
            ClickHouseError: If the API request fails or validation fails
        """
        api_url = f"https://api.clickhouse.cloud//v1/organizations/{self.org_id}/services/{self.service_id}/replicaScaling"

        if min_memory_gb not in RAM:
            raise ClickHouseError(
                f"Invalid min_memory_gb. Please choose from valid RAM options: {RAM}"
            )

        if max_memory_gb not in RAM:
            raise ClickHouseError(
                f"Invalid max_memory_gb. Please choose from valid RAM options: {RAM}"
            )

        if max_memory_gb < min_memory_gb:
            raise ClickHouseError(
                "Configuration error: max_memory_gb must be equal to or greater than min_memory_gb."
            )

        if num_replicas is not None and num_replicas not in REPLICAS:
            raise ClickHouseError(
                f"Invalid num_replicas. Please choose from valid REPLICAS options: {REPLICAS}"
            )

        if idle_timeout_minutes is not None and idle_timeout_minutes < MIN_IDLE_TIMEOUT_MINUTES:
            raise ClickHouseError(
                f"Invalid idle_timeout_minutes. Please choose a value greater than or equal to {MIN_IDLE_TIMEOUT_MINUTES} mins."
            )

        # Check if configuration is already set to requested values, we don't want to make unnecessary API calls when nothing needs to be updated
        checker = self.fetch_service_config()
        config_values = {
            "minReplicaMemoryGb": min_memory_gb,
            "maxReplicaMemoryGb": max_memory_gb,
            "numReplicas": num_replicas,
            "idleScaling": idle_scaling,
            "idleTimeoutMinutes": idle_timeout_minutes,
        }

        if all(
            checker.get(key) == value for key, value in config_values.items() if value is not None
        ):
            return {
                "message": "Current service configuration is already set to the requested values."
            }

        payload = {
            "minReplicaMemoryGb": min_memory_gb,
            "maxReplicaMemoryGb": max_memory_gb,
        }
        if num_replicas is not None:
            payload["numReplicas"] = num_replicas
        if idle_scaling is not None:
            payload["idleScaling"] = idle_scaling
        if idle_timeout_minutes is not None:
            payload["idleTimeoutMinutes"] = idle_timeout_minutes

        response = requests.patch(api_url, json=payload, auth=self.auth)

        if response.status_code == 200:
            return {"message": "Service configuration updated successfully."}
        else:
            raise ClickHouseError(
                "Failed to update service configuration",
                status_code=response.status_code,
                response=response.json(),
            )

    def fetch_service_state(self) -> dict[str, Any]:
        """
        Fetch the current state of the ClickHouse service.

        Returns:
            dict[str, Any]: Service state information
        Raises:
            ClickHouseError: If the API request fails
        """
        api_url = f"https://api.clickhouse.cloud//v1/organizations/{self.org_id}/services/{self.service_id}"
        response = requests.get(api_url, auth=self.auth)

        if response.status_code == 200:
            response_raw = response.json()
            return {"state": response_raw.get("result", {}).get("state", "NA")}
        else:
            raise ClickHouseError(
                "Failed to fetch service state",
                status_code=response.status_code,
                response=response.json(),
            )

    def fetch_service_config(self) -> dict[str, Any]:
        """
        Fetch the current configuration of the ClickHouse service.

        Returns:
            dict[str, Any]: Service configuration details
        Raises:
            ClickHouseError: If the API request fails
        """
        api_url = f"https://api.clickhouse.cloud//v1/organizations/{self.org_id}/services/{self.service_id}"
        response = requests.get(api_url, auth=self.auth)

        if response.status_code == 200:
            response_raw = response.json()
            result = response_raw.get("result", {})
            return {
                "minReplicaMemoryGb": result.get("minReplicaMemoryGb"),
                "maxReplicaMemoryGb": result.get("maxReplicaMemoryGb"),
                "idleScaling": result.get("idleScaling"),
                "idleTimeoutMinutes": result.get("idleTimeoutMinutes"),
                "numReplicas": result.get("numReplicas"),
            }
        else:
            raise ClickHouseError(
                "Failed to fetch service configuration",
                status_code=response.status_code,
                response=response.json(),
            )

    def fetch_ip_access_list(self) -> dict[str, Any]:
        """
        Fetch the IP access list configuration of the ClickHouse service.

        Returns:
            dict[str, Any]: IP access list configuration
        Raises:
            ClickHouseError: If the API request fails
        """
        api_url = f"https://api.clickhouse.cloud//v1/organizations/{self.org_id}/services/{self.service_id}"
        response = requests.get(api_url, auth=self.auth)

        if response.status_code == 200:
            response_raw = response.json()
            return {"ipAccessList": response_raw.get("result", {}).get("ipAccessList", [])}
        else:
            raise ClickHouseError(
                "Failed to fetch IP access list",
                status_code=response.status_code,
                response=response.json(),
            )

    def fetch_service_details(self) -> dict[str, Any]:
        """
        Fetch complete details of the ClickHouse service.

        Returns:
            dict[str, Any]: Complete service details
        Raises:
            ClickHouseError: If the API request fails
        """
        api_url = f"https://api.clickhouse.cloud//v1/organizations/{self.org_id}/services/{self.service_id}"
        response = requests.get(api_url, auth=self.auth)

        if response.status_code == 200:
            return response.json()
        else:
            raise ClickHouseError(
                "Failed to fetch service details",
                status_code=response.status_code,
                response=response.json(),
            )


def _handle_error(e: Union[ClickHouseError, Exception]) -> None:
    """Helper function to handle errors when running as a script"""
    if isinstance(e, ClickHouseError):
        print(f"Error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")
        if e.response:
            print("Response:", e.response)
    else:
        print(f"Unexpected error: {e!s}")


if __name__ == "__main__":
    try:
        from configs.config import CLICKHOUSE_SERVICE_CONFIG

        service_config = next(iter(CLICKHOUSE_SERVICE_CONFIG["services"].values()))
        api = ClickHouseAPI(service_id=service_config["service_id"])

        print("\nFetching current service configuration:")
        config = api.fetch_service_config()
        print(config)

        print("\nFetching service state:")
        state = api.fetch_service_state()
        print(state)

        print("\nFetching IP access list:")
        ip_list = api.fetch_ip_access_list()
        print(ip_list)

    except Exception as e:
        _handle_error(e)
