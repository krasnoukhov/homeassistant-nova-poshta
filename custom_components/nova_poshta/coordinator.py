"""DataUpdateCoordinator for the Nova Poshta integration."""

from __future__ import annotations

from datetime import timedelta, date
import logging
from typing import Callable, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.httpx_client import get_async_client

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

    def __init__(
        self,
        data: dict[str, Any],
        hass: HomeAssistant,
        settlements: dict[str, str] | None = None,
    ) -> None:
        """Initialize.

        settlements maps the refs of the settlements to track to their names;
        empty means track all of them.
        """
        self.settlements = dict(settlements or {})
        async_http_client = AsyncHttpClientWrapper(get_async_client(hass))
        self._client = NovaPoshtaApi(
            data[API_KEY],
            timeout=HTTP_TIMEOUT,
            async_mode=True,
            raise_for_errors=True,
            http_client=async_http_client,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _send(self, client_lambda: Callable[[Any], Any]) -> dict[str, Any]:
        try:
            return await client_lambda()
        except httpx.HTTPError as http_error:
            raise ConnectionError(
                f"{type(http_error).__name__}: {http_error}"
            ) from http_error
        except InvalidAPIKeyError as client_error:
            raise InvalidAuth from client_error
        except APIRequestError as client_error:
            raise APIError(f"API error: {client_error}") from client_error

    async def async_validate_input(self) -> None:
        """Validate Nova Poshta component."""
        return await self._send(self._client.common.get_cargo_types)

    async def async_search_settlements(self, query: str) -> list[dict[str, str]]:
        """Search settlements by name: [{ref, name, label}]."""
        try:
            response = await self._send(
                lambda: self._client.address.search_settlements(
                    city_name=query, limit=20
                )
            )
        except APIError:
            # A non-Cyrillic query is an API error, not an empty result
            return []

        return [
            {
                "ref": x["Ref"],
                "name": x["MainDescription"],
                "label": x["Present"],
            }
            for result in response["data"]
            for x in result["Addresses"]
        ]

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
            raise UpdateFailed(str(http_error)) from http_error

    async def _async_update_data(self) -> dict[str, Any]:
        """Get new sensor data for Nova Poshta component."""
        return await self._get_data()

    @property
    def parcels(self) -> list[dict]:
        """Retrieve parcels data from the response."""
        return self.data["data"][0]["result"]

    @property
    def parcel_settlements(self) -> dict[str, str]:
        """Retrieve settlements parcels went to, tracked or not: {ref: name}."""
        if self.data is None:
            return {}

        return {
            x["SettlmentAddressData"]["RecipientSettlementRef"]: x[
                "SettlmentAddressData"
            ]["RecipientSettlementDescription"]
            for x in self.parcels
        }

    @property
    def warehouses(self) -> list[frozenset]:
        """Retrieve unique warehouses in the tracked settlements."""
        # _LOGGER.debug(f"Parcels ({len(self.parcels)}): {self.parcels}")
        return list(
            set(
                map(
                    lambda x: frozenset(warehouse_of(x).items()),
                    filter(
                        lambda x: not self.settlements
                        or x["SettlmentAddressData"]["RecipientSettlementRef"]
                        in self.settlements,
                        self.parcels,
                    ),
                )
            )
        )

    def delivered_by_warehouse(self, warehouse: dict) -> list[dict]:
        """Retrieve delivered parcels for the warehouse."""
        delivered = list(
            filter(
                lambda x: (x["TypeOfDocument"] == "Incoming" or x["OwnerDocumentType"])
                and (x["TrackingStatusCode"] == "7" or x["TrackingStatusCode"] == "8"),
                self.parcels,
            )
        )
        # A redirect or a return to sender opens a second waybill for the same
        # parcel, and Nova Poshta types it by who ordered the service ("Outgoing")
        # rather than by where the parcel is going -- hence OwnerDocumentType above.
        # Both waybills can sit at 7/8 at once, so keep only the leg that is live:
        # a document naming a successor that is itself in the list is superseded.
        numbers = set(map(lambda x: x["Number"], delivered))
        latest = list(
            filter(
                lambda x: not any(ew["Number"] in numbers for ew in x["LinkedEWs"]),
                delivered,
            )
        )
        # Warehouse numbers repeat across settlements, so match the name too
        return list(filter(lambda x: warehouse_of(x) == warehouse, latest))


def place_name(name: str) -> str:
    """Transliterate a place name the way sensor names spell it."""
    return translit(name, UkrainianSimple).replace("Kyyiv", "Kyiv")


def warehouse_of(parcel: dict) -> dict:
    """Retrieve the warehouse a parcel goes to."""
    address = parcel["SettlmentAddressData"]
    return {
        "id": address["RecipientWarehouseNumber"],
        "name": place_name(
            parcel["CityRecipientDescription"]
            or address["RecipientSettlementDescription"]
        ),
    }


class AsyncHttpClientWrapper:
    def __init__(self, client):
        self._client = client

    def AsyncClient(self, *args, **kwargs):
        return self._client


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class APIError(ConnectionError):
    """Error to indicate the API rejected a request."""
