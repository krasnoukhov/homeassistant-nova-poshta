"""Tests for the Nova Poshta coordinator."""

from unittest.mock import AsyncMock, MagicMock

from novaposhta.client import APIRequestError

from homeassistant.core import HomeAssistant

from custom_components.nova_poshta.const import API_KEY
from custom_components.nova_poshta.coordinator import NovaPoshtaCoordinator

from . import KYIV, ODESA, parcel, response


def _coordinator(
    hass: HomeAssistant, parcels: list[dict], settlements: dict[str, str] | None = None
) -> NovaPoshtaCoordinator:
    coordinator = NovaPoshtaCoordinator({API_KEY: "test-key"}, hass, settlements)
    coordinator.data = response(parcels)
    return coordinator


async def test_same_warehouse_number_in_two_settlements(hass: HomeAssistant) -> None:
    """Kyiv@5 and Odesa@5 are different warehouses."""
    coordinator = _coordinator(
        hass,
        [parcel("1", KYIV, "5"), parcel("2", ODESA, "5"), parcel("3", ODESA, "5")],
    )

    assert sorted(dict(x)["name"] for x in coordinator.warehouses) == ["Kyiv", "Odesa"]
    assert len(coordinator.delivered_by_warehouse({"id": "5", "name": "Kyiv"})) == 1
    assert len(coordinator.delivered_by_warehouse({"id": "5", "name": "Odesa"})) == 2


async def test_settlements_limit_warehouses(hass: HomeAssistant) -> None:
    """Only tracked settlements have warehouses; all are offered to pick."""
    coordinator = _coordinator(
        hass,
        [parcel("1", KYIV, "5"), parcel("2", ODESA, "7")],
        {KYIV[0]: KYIV[1]},
    )

    assert [dict(x) for x in coordinator.warehouses] == [{"id": "5", "name": "Kyiv"}]
    assert coordinator.parcel_settlements == {KYIV[0]: KYIV[1], ODESA[0]: ODESA[1]}


async def test_redirect_to_untracked_settlement(hass: HomeAssistant) -> None:
    """A parcel redirected elsewhere leaves the tracked warehouse."""
    coordinator = _coordinator(
        hass,
        [
            parcel("1", KYIV, "5", linked=("2",)),
            parcel(
                "2",
                ODESA,
                "7",
                document_type="Outgoing",
                owner_document_type="Redirect",
            ),
        ],
        {KYIV[0]: KYIV[1]},
    )

    assert coordinator.delivered_by_warehouse({"id": "5", "name": "Kyiv"}) == []


async def test_parcel_settlements_before_first_update(hass: HomeAssistant) -> None:
    """No data yet means nothing to offer."""
    coordinator = NovaPoshtaCoordinator({API_KEY: "test-key"}, hass)

    assert coordinator.parcel_settlements == {}


async def test_search_settlements(hass: HomeAssistant) -> None:
    """Search results map to ref, name and label."""
    coordinator = NovaPoshtaCoordinator({API_KEY: "test-key"}, hass)
    coordinator._client = MagicMock()
    coordinator._client.address.search_settlements = AsyncMock(
        return_value={
            "data": [
                {
                    "TotalCount": 1,
                    "Addresses": [
                        {
                            "Ref": KYIV[0],
                            "MainDescription": KYIV[1],
                            "Present": "м. Київ, Київська обл.",
                        }
                    ],
                }
            ]
        }
    )

    assert await coordinator.async_search_settlements("Київ") == [
        {"ref": KYIV[0], "name": KYIV[1], "label": "м. Київ, Київська обл."}
    ]


async def test_search_settlements_in_latin(hass: HomeAssistant) -> None:
    """The API rejects Latin queries; that's an empty result."""
    coordinator = NovaPoshtaCoordinator({API_KEY: "test-key"}, hass)
    coordinator._client = MagicMock()
    coordinator._client.address.search_settlements = AsyncMock(
        side_effect=APIRequestError("CityName has invalid characters")
    )

    assert await coordinator.async_search_settlements("Kyiv") == []
