"""DataUpdateCoordinator for the Nova Poshta integration."""

from __future__ import annotations

from datetime import timedelta, date
import logging
from typing import Callable, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import httpx
from novaposhta.client import NovaPoshtaApi, InvalidAPIKeyError, APIRequestError
from translitua import translit, UkrainianSimple

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
        self._client = NovaPoshtaApi(
            data[API_KEY], timeout=HTTP_TIMEOUT, async_mode=True, raise_for_errors=True
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_shutdown(self) -> None:
        """Close the client."""
        await super().async_shutdown()
        await self._client.close_async()

    async def _send(self, client_lambda: Callable[[Any], Any]) -> dict[str, Any]:
        try:
            return await client_lambda()
        except httpx.HTTPError as http_error:
            raise ConnectionError from http_error
        except InvalidAPIKeyError as client_error:
            raise InvalidAuth from client_error
        except APIRequestError as client_error:
            raise ConnectionError from client_error

    async def async_validate_input(self) -> None:
        """Validate Nova Poshta component."""
        return await self._send(self._client.common.get_cargo_types)

    async def _get_data(self) -> dict[str, Any]:
        """Get new sensor data for Nova Poshta component."""
        try:
            today = date.today()
            return await self._send(
                lambda: self._client.internet_document.get_incoming_documents_by_phone(
                    date_from=f"{(today - timedelta(days=180)).strftime('%d.%m.%Y')} 00:00:00",
                    date_to=f"{(today + timedelta(days=1)).strftime('%d.%m.%Y')} 00:00:00",
                    limit=100,
                )
            )
        except ConnectionError as http_error:
            raise UpdateFailed from http_error

    async def _async_update_data(self) -> dict[str, Any]:
        """Get new sensor data for Nova Poshta component."""
        return await self._get_data()

    @property
    def parcels(self) -> list[dict]:
        """Retrieve parcels data from the response."""
        return self.data["data"][0]["result"]

    @property
    def warehouses(self) -> list[dict]:
        """Retrieve unique warehouses."""
        # _LOGGER.debug(f"Parcels ({len(self.parcels)}): {self.parcels}")
        return list(
            set(
                map(
                    lambda x: frozenset(
                        {
                            "id": x["SettlmentAddressData"]["RecipientWarehouseNumber"],
                            "name": translit(
                                (
                                    x["CityRecipientDescription"]
                                    or x["SettlmentAddressData"][
                                        "RecipientSettlementDescription"
                                    ]
                                ),
                                UkrainianSimple,
                            ).replace("Kyyiv", "Kyiv"),
                        }.items()
                    ),
                    self.parcels,
                )
            )
        )

    def delivered_by_warehouse(self, warehouse_id: str) -> list[dict]:
        """Retrieve delivered parcels for the warehouse id."""
        delivered = list(
            filter(
                lambda x: x["TypeOfDocument"] == "Incoming" and (x["TrackingStatusCode"] == "7"
                or x["TrackingStatusCode"] == "8"),
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
