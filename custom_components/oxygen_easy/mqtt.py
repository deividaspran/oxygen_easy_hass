"""AWS IoT MQTT transport used by the Oxygen Easy cloud."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from concurrent.futures import Future as ConcurrentFuture
from typing import Any

from awscrt import auth, io, mqtt
from awsiot import mqtt_connection_builder

from .api import OxygenCloudError, OxygenCloudSession
from .const import IOT_ENDPOINT, REGION, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)

ValueCallback = Callable[[dict[str, dict[str, Any]]], None]


def extract_values(document: Any) -> dict[str, dict[str, Any]]:
    """Extract controller parameter values from responses and push messages."""
    found: dict[str, dict[str, Any]] = {}

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            component = node.get("component")
            parameters = node.get("parameters")
            if isinstance(component, str) and isinstance(parameters, dict):
                values = found.setdefault(component, {})
                for uid, raw_value in parameters.items():
                    if not isinstance(uid, str) or not uid.startswith("u"):
                        continue
                    if isinstance(raw_value, list):
                        if raw_value:
                            values[uid] = raw_value[0]
                    elif not isinstance(raw_value, dict):
                        values[uid] = raw_value
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(document)
    return found


class OxygenMqttError(OxygenCloudError):
    """MQTT request or connection failed."""


class OxygenMqttClient:
    """Manage one account-scoped WebSocket connection and request routing."""

    def __init__(
        self,
        session: OxygenCloudSession,
        value_callback: ValueCallback,
    ) -> None:
        self._session = session
        self._value_callback = value_callback
        self._loop = asyncio.get_running_loop()
        self._connection: Any | None = None
        self._bootstrap: io.ClientBootstrap | None = None
        self._connected = False
        self._installations: set[str] = set()
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._transaction = 0
        self._client_id: str | None = None
        self._credential_key: str | None = None
        self._connect_lock = asyncio.Lock()

    async def async_ensure_connected(self, installation_ids: set[str]) -> None:
        """Connect, renewing the SigV4 credential provider when necessary."""
        async with self._connect_lock:
            await asyncio.get_running_loop().run_in_executor(
                None, self._session.ensure_credentials
            )
            credentials_changed = (
                self._credential_key is not None
                and self._credential_key != self._session.access_key_id
            )
            subscriptions_changed = installation_ids != self._installations
            if self._connection is None or credentials_changed:
                if self._connection is not None:
                    await self.async_disconnect()
                self._installations = set(installation_ids)
                await asyncio.get_running_loop().run_in_executor(None, self._connect)
            elif subscriptions_changed:
                new_ids = installation_ids - self._installations
                self._installations = set(installation_ids)
                await asyncio.get_running_loop().run_in_executor(
                    None, self._subscribe_installations, new_ids
                )

    def _connect(self) -> None:
        credentials = self._session.credentials
        identity_id = self._session.identity_id
        if credentials is None or identity_id is None:
            raise OxygenMqttError("AWS credentials are unavailable")

        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        self._bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
        provider = auth.AwsCredentialsProvider.new_static(
            credentials["AccessKeyId"],
            credentials["SecretKey"],
            credentials["SessionToken"],
        )
        self._client_id = f"{identity_id}-{int(time.time() * 1000)}"
        self._connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=IOT_ENDPOINT,
            region=REGION,
            credentials_provider=provider,
            client_bootstrap=self._bootstrap,
            client_id=self._client_id,
            clean_session=True,
            keep_alive_secs=30,
            on_connection_interrupted=self._on_connection_interrupted,
            on_connection_resumed=self._on_connection_resumed,
        )
        try:
            self._connection.connect().result(REQUEST_TIMEOUT)
            self._subscribe_installations(self._installations)
        except Exception as err:
            connection = self._connection
            self._connection = None
            if connection is not None:
                try:
                    connection.disconnect().result(REQUEST_TIMEOUT)
                except Exception:
                    pass
            raise OxygenMqttError("Could not connect to Oxygen AWS IoT") from err
        self._credential_key = credentials["AccessKeyId"]
        self._connected = True

    def _subscribe_installations(self, installation_ids: set[str]) -> None:
        if self._connection is None or self._client_id is None:
            return
        for installation_id in installation_ids:
            topics = (
                f"{installation_id}/installationNotifications",
                f"{installation_id}/{self._client_id}/installationResponse",
            )
            for topic in topics:
                future, _packet_id = self._connection.subscribe(
                    topic=topic,
                    qos=mqtt.QoS.AT_LEAST_ONCE,
                    callback=self._on_message,
                )
                future.result(REQUEST_TIMEOUT)

    def _on_connection_interrupted(
        self, _connection: Any, error: Exception, **_: Any
    ) -> None:
        _LOGGER.warning("Oxygen MQTT connection interrupted: %s", error)
        self._loop.call_soon_threadsafe(self._set_connected, False)

    def _on_connection_resumed(
        self,
        connection: Any,
        return_code: mqtt.ConnectReturnCode,
        session_present: bool,
        **_: Any,
    ) -> None:
        self._loop.call_soon_threadsafe(self._set_connected, True)
        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            connection.resubscribe_existing_topics()

    def _set_connected(self, connected: bool) -> None:
        self._connected = connected

    def _on_message(self, topic: str, payload: bytes, **_: Any) -> None:
        try:
            document = json.loads(payload)
        except (TypeError, ValueError):
            _LOGGER.debug("Ignoring malformed Oxygen MQTT payload")
            return
        self._loop.call_soon_threadsafe(self._handle_message, document)

    def _handle_message(self, document: Any) -> None:
        if not isinstance(document, dict):
            return
        transaction_id = document.get("transactionId")
        if transaction_id is not None:
            pending = self._pending.pop(str(transaction_id), None)
            if pending is not None and not pending.done():
                pending.set_result(document)
        values = extract_values(document)
        if values:
            self._value_callback(values)

    async def async_send_operation(
        self, installation_id: str, operation: dict[str, Any]
    ) -> dict[str, Any]:
        """Publish an operation and wait for its matching response."""
        await self.async_ensure_connected(self._installations or {installation_id})
        if self._connection is None or self._client_id is None or not self._connected:
            raise OxygenMqttError("Oxygen MQTT is disconnected")
        self._transaction += 1
        transaction_id = str(self._transaction)
        request = {"transactionId": transaction_id, "operations": [operation]}
        pending: asyncio.Future[dict[str, Any]] = self._loop.create_future()
        self._pending[transaction_id] = pending
        topic = f"{installation_id}/{self._client_id}/installationRequest"
        try:
            publish_future, _packet_id = self._connection.publish(
                topic=topic,
                payload=json.dumps(request, separators=(",", ":")),
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )
            if isinstance(publish_future, ConcurrentFuture):
                await asyncio.wrap_future(publish_future)
            async with asyncio.timeout(REQUEST_TIMEOUT):
                return await pending
        except TimeoutError as err:
            raise OxygenMqttError("Oxygen MQTT request timed out") from err
        except Exception as err:
            raise OxygenMqttError("Oxygen MQTT request failed") from err
        finally:
            self._pending.pop(transaction_id, None)

    async def async_disconnect(self) -> None:
        """Disconnect and reject requests that can no longer complete."""
        connection, self._connection = self._connection, None
        self._connected = False
        for pending in self._pending.values():
            if not pending.done():
                pending.set_exception(OxygenMqttError("Oxygen MQTT disconnected"))
        self._pending.clear()
        if connection is not None:
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None, lambda: connection.disconnect().result(REQUEST_TIMEOUT)
                )
            except Exception:
                _LOGGER.debug("Error while disconnecting Oxygen MQTT", exc_info=True)
