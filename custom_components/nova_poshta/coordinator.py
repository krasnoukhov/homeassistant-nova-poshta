"""DataUpdateCoordinator for the Nova Poshta integration."""
from __future__ import annotations

from datetime import timedelta, date
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import httpx
from novaposhta.client import NovaPoshtaApi

from .const import (
    API_KEY,
    DOMAIN,
    HTTP_TIMEOUT,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class NovaPoshtaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Nova Poshta Coordinator class."""

    def __init__(self, data: dict[str, Any], hass: HomeAssistant) -> None:
        """Initialize."""
        self._client = NovaPoshtaApi(data[API_KEY], timeout=HTTP_TIMEOUT)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def _send(self, **kwargs) -> dict[str, Any]:
        try:
            response = self._client.send(**kwargs)
            # TODO: check response json
            return response
        except httpx.HTTPError as http_error:
            raise ConnectionError from http_error

    def _validate(self) -> None:
        """Validate using Nova Poshta API."""
        self._send(model_name="Common", api_method="getCargoTypes", method_props={})

    async def async_validate_input(self) -> None:
        """Validate Nova Poshta component."""
        return await self.hass.async_add_executor_job(self._validate)

    def _get_data(self) -> dict[str, Any]:
        """Get new sensor data for Nova Poshta component."""
        try:
            today = date.today()
            return self._send(
                model_name="InternetDocument",
                api_method="getIncomingDocumentsByPhone",
                method_props={
                    "DateFrom": f"{(today - timedelta(days=14)).strftime('%d.%m.%Y')} 00:00:00",
                    "DateTo": f"{(today + timedelta(days=1)).strftime('%d.%m.%Y')} 00:00:00",
                    "Limit": 100,
                },
            )
        except ConnectionError as http_error:
            raise UpdateFailed from http_error

    async def _async_update_data(self) -> dict[str, Any]:
        """Get new sensor data for Nova Poshta component."""
        return await self.hass.async_add_executor_job(self._get_data)

    @property
    def parcels(self) -> list[dict]:
        """Retrieve parcels data from the response."""
        return self.data["data"][0]["result"]

    @property
    def warehouses(self) -> list[str]:
        """Retrieve unique warehouse ids."""
        return list(
            set(
                map(
                    lambda x: x["SettlmentAddressData"]["RecipientWarehouseNumber"],
                    self.parcels,
                )
            )
        )

    def delivered_by_warehouse(self, warehouse_id: str) -> list[dict]:
        """Retrieve delivered parcels for the warehouse id."""
        delivered = list(
            filter(
                lambda x: x["TrackingStatusCode"] == "7"
                or x["TrackingStatusCode"] == "8",
                self.parcels,
            )
        )
        return list(
            filter(
                lambda x: x["SettlmentAddressData"]["RecipientWarehouseNumber"]
                == warehouse_id,
                delivered,
            )
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
