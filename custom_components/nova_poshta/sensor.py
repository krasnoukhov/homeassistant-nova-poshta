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

    _warehouse: dict

    def __init__(
        self,
        coordinator: NovaPoshtaCoordinator,
        entry: ConfigEntry,
        warehouse: frozenset,
    ) -> None:
        """Initialize a Nova Poshta entity."""
        super().__init__(coordinator)

        self._warehouse = dict(warehouse)
        self.entity_description = SensorEntityDescription(
            key=f"delivered_parcels_{snakecase(self._warehouse['name'])}_{self._warehouse['id']}",
            name=f"Delivered parcels in {self._warehouse['name']}@{self._warehouse['id']}",
            state_class=SensorStateClass.TOTAL,
        )
        self._attr_unique_id = "-".join(
            [
                entry.entry_id,
                self.entity_description.key,
            ]
        )
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
            "parcels": list(
                map(
                    lambda x: f"{x['CargoDescription']} - {x['CounterpartySenderDescription']}",
                    self._parcels,
                )
            )
        }

    @property
    def _parcels(self) -> list[dict]:
        return self.coordinator.delivered_by_warehouse(self._warehouse["id"])
