"""Authentication and signed account API access for Oxygen Easy."""

from __future__ import annotations

import threading
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import boto3
import requests
from botocore import UNSIGNED
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.credentials import Credentials
from pycognito import Cognito

from .const import (
    API_HOST,
    API_STAGE,
    APP_ID,
    ARCHIVES_API,
    CLIENT_ID,
    CREDENTIAL_REFRESH_MARGIN,
    IDENTITY_POOL_ID,
    REGION,
    REQUEST_TIMEOUT,
    USER_POOL_ID,
)


class OxygenCloudError(Exception):
    """Base cloud communication error."""


class OxygenAuthenticationError(OxygenCloudError):
    """Authentication failed."""


class OxygenApiError(OxygenCloudError):
    """The account API returned an error."""


class OxygenCloudSession:
    """Own Cognito identity and its short-lived AWS credentials."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self._password = password
        self.identity_id: str | None = None
        self.id_token: str | None = None
        self.credentials: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def access_key_id(self) -> str | None:
        """Return the active AWS access key identifier, never the secret."""
        if self.credentials is None:
            return None
        return self.credentials.get("AccessKeyId")

    def ensure_credentials(self) -> bool:
        """Ensure valid credentials; return whether they were replaced."""
        with self._lock:
            if not self._credentials_expiring():
                return False
            self._authenticate()
            return True

    def _credentials_expiring(self) -> bool:
        if not self.credentials:
            return True
        expiration = self.credentials.get("Expiration")
        if not isinstance(expiration, datetime):
            return True
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=UTC)
        return expiration - datetime.now(UTC) <= CREDENTIAL_REFRESH_MARGIN

    def _authenticate(self) -> None:
        try:
            cognito = Cognito(USER_POOL_ID, CLIENT_ID, username=self.username)
            cognito.authenticate(password=self._password)
            self.id_token = cognito.id_token
            login_key = f"cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
            logins = {login_key: cognito.id_token}
            identity = boto3.client(
                "cognito-identity",
                region_name=REGION,
                config=Config(signature_version=UNSIGNED),
            )
            self.identity_id = identity.get_id(
                IdentityPoolId=IDENTITY_POOL_ID, Logins=logins
            )["IdentityId"]
            response = identity.get_credentials_for_identity(
                IdentityId=self.identity_id, Logins=logins
            )
            self.credentials = response["Credentials"]
        except Exception as err:
            raise OxygenAuthenticationError(
                "Oxygen cloud authentication failed"
            ) from err

    def signed_get(self, path: str, query: list[tuple[str, str]] | None = None) -> Any:
        """Make a blocking SigV4-signed GET request."""
        self.ensure_credentials()
        if self.credentials is None:
            raise OxygenAuthenticationError("AWS credentials are unavailable")

        uri = API_STAGE + (path if path.startswith("/") else f"/{path}")
        url = f"https://{API_HOST}{uri}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        aws_request = AWSRequest(method="GET", url=url, headers={"appid": APP_ID})
        credentials = Credentials(
            self.credentials["AccessKeyId"],
            self.credentials["SecretKey"],
            self.credentials["SessionToken"],
        )
        SigV4Auth(credentials, "execute-api", REGION).add_auth(aws_request)
        prepared = aws_request.prepare()
        try:
            response = requests.get(
                url, headers=dict(prepared.headers), timeout=REQUEST_TIMEOUT
            )
        except requests.RequestException as err:
            raise OxygenApiError("Could not reach the Oxygen account API") from err
        if response.status_code in (401, 403):
            raise OxygenAuthenticationError("Oxygen cloud credentials were rejected")
        if not response.ok:
            raise OxygenApiError(
                f"Oxygen account API returned HTTP {response.status_code}"
            )
        try:
            return response.json() if response.content else None
        except ValueError as err:
            raise OxygenApiError("Oxygen account API returned invalid JSON") from err

    def installations(self) -> list[dict[str, Any]]:
        """List installations available to the account."""
        result = self.signed_get("/v1/get-installation-list")
        if not isinstance(result, list):
            raise OxygenApiError("Installation list has an unexpected shape")
        return [item for item in result if isinstance(item, dict)]

    def installation_details(self, installation_id: str) -> dict[str, Any]:
        """Get gateway and component metadata for an installation."""
        quoted_id = urllib.parse.quote(installation_id, safe="")
        result = self.signed_get(f"/v1/installation/{quoted_id}/get-details")
        if not isinstance(result, dict):
            raise OxygenApiError("Installation details have an unexpected shape")
        return result

    def component_profile(
        self,
        producer_code: str,
        name: str,
        hardware_version: str,
        software_version: str,
    ) -> dict[str, Any]:
        """Get a component's web profile."""
        parts = (producer_code, name, hardware_version, software_version)
        encoded = "/".join(urllib.parse.quote(part, safe="") for part in parts)
        result = self.signed_get(f"/v1/profiles/{encoded}/web/profile.json")
        if not isinstance(result, dict):
            raise OxygenApiError("Component profile has an unexpected shape")
        return result

    def component_translations(
        self,
        producer_code: str,
        name: str,
        hardware_version: str,
        software_version: str,
    ) -> dict[str, str]:
        """Get a component's English web-profile translations."""
        parts = (producer_code, name, hardware_version, software_version)
        encoded = "/".join(urllib.parse.quote(part, safe="") for part in parts)
        result = self.signed_get(f"/v1/profiles/{encoded}/web/trans_en.json")
        if not isinstance(result, dict):
            raise OxygenApiError("Component translations have an unexpected shape")
        return {
            str(key): str(value)
            for key, value in result.items()
            if isinstance(value, str)
        }

    def active_alarms(
        self,
        installation_id: str,
        component_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Get active alarms from the read-only Oxygen archive API."""
        self.ensure_credentials()
        if self.id_token is None:
            raise OxygenAuthenticationError("Oxygen ID token is unavailable")
        try:
            response = requests.post(
                f"{ARCHIVES_API}/alarms/values",
                headers={
                    "Authorization": f"Bearer {self.id_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "filter": "active",
                    "installation": installation_id,
                    "components": component_ids,
                },
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as err:
            raise OxygenApiError("Could not reach the Oxygen alarms API") from err
        if response.status_code in (401, 403):
            raise OxygenAuthenticationError("Oxygen alarms credentials were rejected")
        if not response.ok:
            raise OxygenApiError(
                f"Oxygen alarms API returned HTTP {response.status_code}"
            )
        try:
            result = response.json()
        except ValueError as err:
            raise OxygenApiError("Oxygen alarms API returned invalid JSON") from err
        if not isinstance(result, list):
            raise OxygenApiError("Oxygen alarms API returned an unexpected shape")
        return [item for item in result if isinstance(item, dict)]
