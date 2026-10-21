"""Tests for the Nova Poshta sensors."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.nova_poshta.const import DOMAIN

from . import KYIV, add_entry


def _registered(hass: HomeAssistant, entry, key: str) -> er.RegistryEntry:
    """Register a sensor the way an earlier run would have."""
    return er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}-{key}", config_entry=entry
    )


async def test_sensors_per_warehouse(hass: HomeAssistant, mock_api) -> None:
    """Each warehouse counts only its own parcels."""
    entry = add_entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    kyiv = hass.states.get("sensor.dmytro_delivered_parcels_in_kyiv_5")
    assert kyiv.state == "1"
    assert kyiv.attributes["parcels"] == ["Книги - Магазин"]
    assert hass.states.get("sensor.dmytro_delivered_parcels_in_odesa_5").state == "2"


async def test_untracked_sensors_removed(hass: HomeAssistant, mock_api) -> None:
    """Sensors outside the tracked settlements go, even ones with no parcels left."""
    entry = add_entry(hass, {KYIV[0]: KYIV[1]})
    old_kyiv = _registered(hass, entry, "delivered_parcels_kyiv_9")
    old_odesa = _registered(hass, entry, "delivered_parcels_odesa_9")
    # A different settlement whose name starts with a tracked one's
    old_kyiv_other = _registered(hass, entry, "delivered_parcels_kyiv_oblast_9")

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert registry.async_get(old_kyiv.entity_id) is not None
    assert registry.async_get(old_odesa.entity_id) is None
    assert registry.async_get(old_kyiv_other.entity_id) is None
    assert hass.states.get("sensor.dmytro_delivered_parcels_in_kyiv_5").state == "1"
    assert registry.async_get("sensor.dmytro_delivered_parcels_in_odesa_5") is None


async def test_all_settlements_keep_old_sensors(hass: HomeAssistant, mock_api) -> None:
    """With no settlements picked nothing is removed."""
    entry = add_entry(hass)
    old_odesa = _registered(hass, entry, "delivered_parcels_odesa_9")

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert er.async_get(hass).async_get(old_odesa.entity_id) is not None
