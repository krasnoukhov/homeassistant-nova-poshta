"""Fixtures for Nova Poshta tests."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from . import IVANO_FRANKIVSK, KYIV, ODESA, parcel, response

COORDINATOR = "custom_components.nova_poshta.coordinator.NovaPoshtaCoordinator"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the integration from custom_components."""
    yield


@pytest.fixture
def mock_api():
    """Stub the Nova Poshta API: Kyiv@5 has one parcel, Odesa@5 two."""
    api = SimpleNamespace(
        parcels=[
            parcel("1", KYIV, "5"),
            parcel("2", ODESA, "5"),
            parcel("3", ODESA, "5"),
        ],
    )
    with (
        patch(f"{COORDINATOR}.async_validate_input", return_value=None),
        patch(
            f"{COORDINATOR}._get_data", side_effect=lambda: response(api.parcels)
        ) as api.get_data,
        patch(
            f"{COORDINATOR}.async_search_settlements",
            return_value=[
                {
                    "ref": IVANO_FRANKIVSK[0],
                    "name": IVANO_FRANKIVSK[1],
                    "label": "м. Івано-Франківськ, Івано-Франківська обл.",
                }
            ],
        ) as api.search,
    ):
        yield api
