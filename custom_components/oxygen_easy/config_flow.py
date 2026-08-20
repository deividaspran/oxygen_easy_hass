"""Config flow for Oxygen Easy."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import OxygenAuthenticationError, OxygenCloudError, OxygenCloudSession
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN


class OxygenEasyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure an Oxygen cloud account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial credential form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            try:
                session = OxygenCloudSession(username, password)
                installations = await self.hass.async_add_executor_job(
                    session.installations
                )
                if not installations:
                    errors["base"] = "no_installations"
                else:
                    await self.async_set_unique_id(username.casefold())
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Oxygen Easy",
                        data={CONF_USERNAME: username, CONF_PASSWORD: password},
                    )
            except OxygenAuthenticationError:
                errors["base"] = "invalid_auth"
            except OxygenCloudError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start credential reauthentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate and replace an expired password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = self._reauth_entry.data[CONF_USERNAME]
            try:
                session = OxygenCloudSession(username, user_input[CONF_PASSWORD])
                await self.hass.async_add_executor_job(session.installations)
            except OxygenAuthenticationError:
                errors["base"] = "invalid_auth"
            except OxygenCloudError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )
