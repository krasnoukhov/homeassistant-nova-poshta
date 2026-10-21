"""Tests for the Nova Poshta integration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.nova_poshta.const import API_KEY, CONF_SETTLEMENTS, DOMAIN

KYIV = ("kyiv-ref", "Київ")
ODESA = ("odesa-ref", "Одеса")
IVANO_FRANKIVSK = ("if-ref", "Івано-Франківськ")


def parcel(
    number: str,
    settlement: tuple[str, str],
    warehouse: str,
    status: str = "7",
    linked: tuple[str, ...] = (),
    document_type: str = "Incoming",
    owner_document_type: str = "",
) -> dict:
    """Build a parcel as getIncomingDocumentsByPhone returns it."""
    ref, name = settlement
    return {
        "Number": number,
        "TypeOfDocument": document_type,
        "OwnerDocumentType": owner_document_type,
        "TrackingStatusCode": status,
        "LinkedEWs": [{"Number": x} for x in linked],
        "CityRecipientDescription": name,
        "CargoDescription": "Книги",
        "CounterpartySenderDescription": "Магазин",
        "SettlmentAddressData": {
            "RecipientSettlementRef": ref,
            "RecipientSettlementDescription": name,
            "RecipientWarehouseNumber": warehouse,
        },
    }


def response(parcels: list[dict]) -> dict:
    """Wrap parcels the way the API does."""
    return {"data": [{"result": parcels}]}


def add_entry(
    hass: HomeAssistant, settlements: dict[str, str] | None = None
) -> MockConfigEntry:
    """Add a Dmytro entry, tracking the given settlements or all of them."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Dmytro",
        unique_id="test-key",
        data={API_KEY: "test-key"},
        options={} if settlements is None else {CONF_SETTLEMENTS: settlements},
    )
    entry.add_to_hass(hass)
    return entry
