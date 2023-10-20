"""Home Assistant component for accessing the Nova Poshta API.

The sensor component creates multipe sensors regarding Nova Poshta status.
"""
from __future__ import annotations

import logging
from typing import cast
from stringcase import snakecase

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
)
from .coordinator import NovaPoshtaCoordinator
from .entity import NovaPoshtaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create Nova Poshta sensor entities in HASS."""
    coordinator: NovaPoshtaCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            NovaPoshtaSensor(coordinator, entry, warehouse)
            for warehouse in coordinator.warehouses
        ]
    )


class NovaPoshtaSensor(NovaPoshtaEntity, SensorEntity):
    """Representation of the Nova Poshta sensor."""

    _parcels: list[dict]

    def __init__(
        self,
        coordinator: NovaPoshtaCoordinator,
        entry: ConfigEntry,
        warehouse: frozenset,
    ) -> None:
        """Initialize a Nova Poshta entity."""
        super().__init__(coordinator)

        warehouse_info = dict(warehouse)
        self._parcels = self.coordinator.delivered_by_warehouse(warehouse_info["id"])

        self.entity_description = SensorEntityDescription(
            key=f"delivered_parcels_{snakecase(warehouse_info['name'])}_{warehouse_info['id']}",
            name=f"Delivered parcels in {warehouse_info['name']}@{warehouse_info['id']}",
            state_class=SensorStateClass.TOTAL,
        )
        self._attr_unique_id = self.entity_description.key
        self._attr_device_info = DeviceInfo(
            name=entry.title,
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return cast(StateType, len(self._parcels))

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        return {
            "parcels": "\n\n".join(
                map(
                    lambda x: f"{x['CargoDescription']}\n{x['CounterpartySenderDescription']}",
                    self._parcels,
                )
            )
        }
