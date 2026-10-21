"""Config flow for Nova Poshta integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow, FlowHandler, FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    API_KEY,
    CONF_SEARCH,
    CONF_SETTLEMENTS,
    DOMAIN,
)
from .coordinator import InvalidAuth, NovaPoshtaCoordinator, place_name

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(API_KEY): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> NovaPoshtaCoordinator:
    """Validate the user input allows us to connect.

    Data has the keys from USER_SCHEMA with values provided by the user.
    """

    coordinator = NovaPoshtaCoordinator(data, hass)
    await coordinator.async_validate_input()

    return coordinator


def _settlements_selector(options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options, multiple=True, mode=SelectSelectorMode.LIST
        )
    )


class SettlementsFlow(FlowHandler):
    """Steps that pick the settlements to track, shared by setup and options."""

    _coordinator: NovaPoshtaCoordinator
    # {ref: name}
    _settlements: dict[str, str]
    # {ref: {ref, name, label}} from the last search
    _found: dict[str, dict[str, str]]

    def _async_finish(self, settlements: dict[str, str]) -> FlowResult:
        raise NotImplementedError

    async def async_step_settlements(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick settlements, or search for one that isn't listed."""
        known = {**self._coordinator.parcel_settlements, **self._settlements}
        errors = {}

        if user_input is not None:
            self._settlements = {
                ref: known[ref] for ref in user_input.get(CONF_SETTLEMENTS, [])
            }
            query = user_input.get(CONF_SEARCH, "").strip()
            if not query:
                return self._async_finish(self._settlements)

            try:
                found = await self._coordinator.async_search_settlements(query)
            except ConnectionError:
                errors["base"] = "cannot_connect"
            else:
                if found:
                    self._found = {x["ref"]: x for x in found}
                    return await self.async_step_search()
                errors[CONF_SEARCH] = "no_results"

        options = sorted(
            (
                SelectOptionDict(value=ref, label=place_name(name))
                for ref, name in known.items()
            ),
            key=lambda x: x["label"],
        )
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SETTLEMENTS, default=list(self._settlements)
                ): _settlements_selector(options),
                vol.Optional(CONF_SEARCH): cv.string,
            }
        )
        return self.async_show_form(
            step_id="settlements", data_schema=data_schema, errors=errors
        )

    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick from what the search found, then go back to the list."""
        if user_input is not None:
            for ref in user_input.get(CONF_SETTLEMENTS, []):
                self._settlements[ref] = self._found[ref]["name"]
            return await self.async_step_settlements()

        options = [
            SelectOptionDict(value=x["ref"], label=x["label"])
            for x in self._found.values()
        ]
        data_schema = vol.Schema(
            {vol.Optional(CONF_SETTLEMENTS, default=[]): _settlements_selector(options)}
        )
        return self.async_show_form(step_id="search", data_schema=data_schema)


class ConfigFlow(config_entries.ConfigFlow, SettlementsFlow, domain=DOMAIN):
    """Handle a config flow for Nova Poshta."""

    VERSION = 1

    _data: dict[str, Any]

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        description_placeholders = {
            "cabinet_url": "https://new.novaposhta.ua/dashboard/settings/developers",
            "developer_url": "https://developers.novaposhta.ua",
        }

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=USER_SCHEMA,
                errors={},
                description_placeholders=description_placeholders,
            )

        errors = {}

        try:
            coordinator = await validate_input(self.hass, user_input)

            await self.async_set_unique_id(user_input[API_KEY])
            self._abort_if_unique_id_configured()

            # Parcels so far suggest which settlements to track
            await coordinator.async_refresh()
            self._coordinator = coordinator
            self._data = user_input
            self._settlements = {}
            return await self.async_step_settlements()
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
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    def _async_finish(self, settlements: dict[str, str]) -> FlowResult:
        return self.async_create_entry(
            title="Nova Poshta",
            data=self._data,
            options={CONF_SETTLEMENTS: settlements},
        )


class OptionsFlowHandler(config_entries.OptionsFlow, SettlementsFlow):
    """Handle Nova Poshta options."""

    async def async_step_init(self, _user_input=None):
        """Start from the settlements tracked now."""
        entry = self.config_entry
        self._settlements = dict(entry.options.get(CONF_SETTLEMENTS, {}))
        self._coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if self._coordinator is None:
            # The entry isn't loaded, so fetch parcels just for the list
            self._coordinator = NovaPoshtaCoordinator(entry.data, self.hass)
            await self._coordinator.async_refresh()

        return await self.async_step_settlements()

    def _async_finish(self, settlements: dict[str, str]) -> FlowResult:
        return self.async_create_entry(data={CONF_SETTLEMENTS: settlements})
