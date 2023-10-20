"""Base entity for the Nova Poshta integration."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NovaPoshtaCoordinator


class NovaPoshtaEntity(CoordinatorEntity[NovaPoshtaCoordinator]):
    """Defines a base Nova Poshta entity."""

    _attr_has_entity_name = True
