from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JarvisAuthError, JarvisUpdateClient, JarvisUpdaterError
from .const import CONF_CHANNEL, CONF_LICENSE_KEY, CONF_UPDATE_URL, DEFAULT_CHANNEL, DEFAULT_UPDATE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class JarvisUpdaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Jarvis Cards Updater."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_UPDATE_URL] = str(user_input.get(CONF_UPDATE_URL) or DEFAULT_UPDATE_URL).rstrip("/")
            user_input[CONF_CHANNEL] = str(user_input.get(CONF_CHANNEL) or DEFAULT_CHANNEL)
            try:
                manifest = await self._async_validate(user_input)
            except JarvisAuthError:
                errors["base"] = "invalid_license"
            except JarvisUpdaterError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - Home Assistant config flows should not leak traces to users
                _LOGGER.exception("Unexpected error validating Jarvis license")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"jarvis-cards-{manifest.channel}")
                self._abort_if_unique_id_configured(updates=user_input)
                title = f"Jarvis Cards ({manifest.channel})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LICENSE_KEY): str,
                    vol.Optional(CONF_UPDATE_URL, default=DEFAULT_UPDATE_URL): str,
                    vol.Optional(CONF_CHANNEL, default=DEFAULT_CHANNEL): vol.In(["stable"]),
                }
            ),
            errors=errors,
        )

    async def _async_validate(self, user_input: dict[str, Any]):
        session: ClientSession = async_get_clientsession(self.hass)
        client = JarvisUpdateClient(session, user_input)
        return await client.async_get_manifest()
