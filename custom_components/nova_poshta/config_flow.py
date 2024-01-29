"""Config flow for Nova Poshta integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow
import homeassistant.helpers.config_validation as cv

from .const import (
    API_KEY,
    DOMAIN,
)
from .coordinator import InvalidAuth, NovaPoshtaCoordinator

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(API_KEY): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from USER_SCHEMA with values provided by the user.
    """

    coordinator = NovaPoshtaCoordinator(data, hass)
    await coordinator.async_validate_input()

    return {"title": "Nova Poshta"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nova Poshta."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=USER_SCHEMA, errors={}
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)

            await self.async_set_unique_id(user_input[API_KEY])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=info["title"], data=user_input)
        except ConnectionError:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except AbortFlow as abort_flow_error:
            errors["base"] = abort_flow_error.reason
        except Exception as exception_error:  # pylint: disable=broad-except
            _LOGGER.exception(f"Unexpected exception {exception_error}")
            errors["base"] = "unknown"

        data_schema = self.add_suggested_values_to_schema(USER_SCHEMA, user_input)
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
