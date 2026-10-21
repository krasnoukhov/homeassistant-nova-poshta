"""Tests for the Nova Poshta config and options flows."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.nova_poshta.const import (
    API_KEY,
    CONF_SEARCH,
    CONF_SETTLEMENTS,
    DOMAIN,
)

from . import IVANO_FRANKIVSK, KYIV, ODESA, add_entry

# Entries set up here are titled "Nova Poshta"; add_entry() ones "Dmytro"
NEW_KYIV_5 = "sensor.nova_poshta_delivered_parcels_in_kyiv_5"
NEW_ODESA_5 = "sensor.nova_poshta_delivered_parcels_in_odesa_5"
KYIV_5 = "sensor.dmytro_delivered_parcels_in_kyiv_5"
ODESA_5 = "sensor.dmytro_delivered_parcels_in_odesa_5"


def _settlements_field(result: FlowResult):
    return next(
        (key, value)
        for key, value in result["data_schema"].schema.items()
        if key == CONF_SETTLEMENTS
    )


def _options(result: FlowResult) -> dict[str, str]:
    """Settlements the form offers: {ref: label}."""
    _, selector = _settlements_field(result)
    return {x["value"]: x["label"] for x in selector.config["options"]}


def _picked(result: FlowResult) -> list[str]:
    key, _ = _settlements_field(result)
    return key.default()


async def _start_setup(hass: HomeAssistant) -> FlowResult:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {API_KEY: "test-key"}
    )
    assert result["step_id"] == "settlements"
    return result


async def test_setup_tracks_picked_settlements(hass: HomeAssistant, mock_api) -> None:
    """Setup offers the settlements parcels went to; only picked ones get sensors."""
    result = await _start_setup(hass)
    assert _options(result) == {KYIV[0]: "Kyiv", ODESA[0]: "Odesa"}
    assert _picked(result) == []

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SETTLEMENTS: [KYIV[0]]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {API_KEY: "test-key"}
    assert result["options"] == {CONF_SETTLEMENTS: {KYIV[0]: KYIV[1]}}
    assert hass.states.get(NEW_KYIV_5).state == "1"
    assert hass.states.get(NEW_ODESA_5) is None


async def test_setup_tracks_all_by_default(hass: HomeAssistant, mock_api) -> None:
    """Picking nothing keeps every settlement."""
    result = await _start_setup(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["options"] == {CONF_SETTLEMENTS: {}}
    assert hass.states.get(NEW_KYIV_5).state == "1"
    assert hass.states.get(NEW_ODESA_5).state == "2"


async def test_setup_adds_searched_settlement(hass: HomeAssistant, mock_api) -> None:
    """A settlement with no parcels yet is found by search and added to the list."""
    result = await _start_setup(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SETTLEMENTS: [KYIV[0]], CONF_SEARCH: "Івано-Франківськ"},
    )
    mock_api.search.assert_awaited_once_with("Івано-Франківськ")
    assert result["step_id"] == "search"
    assert _options(result) == {
        IVANO_FRANKIVSK[0]: "м. Івано-Франківськ, Івано-Франківська обл."
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SETTLEMENTS: [IVANO_FRANKIVSK[0]]}
    )
    assert result["step_id"] == "settlements"
    assert _options(result) == {
        IVANO_FRANKIVSK[0]: "Ivano-Frankivs'k",
        KYIV[0]: "Kyiv",
        ODESA[0]: "Odesa",
    }
    assert _picked(result) == [KYIV[0], IVANO_FRANKIVSK[0]]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SETTLEMENTS: [KYIV[0], IVANO_FRANKIVSK[0]]}
    )
    await hass.async_block_till_done()

    assert result["options"] == {
        CONF_SETTLEMENTS: {
            KYIV[0]: KYIV[1],
            IVANO_FRANKIVSK[0]: IVANO_FRANKIVSK[1],
        }
    }


async def test_search_finds_nothing(hass: HomeAssistant, mock_api) -> None:
    """An empty search stays on the form with an error."""
    mock_api.search.return_value = []

    result = await _start_setup(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEARCH: "Kyiv"}
    )

    assert result["step_id"] == "settlements"
    assert result["errors"] == {CONF_SEARCH: "no_results"}


async def test_options_untrack_settlement(hass: HomeAssistant, mock_api) -> None:
    """Dropping a settlement in options deletes its sensors."""
    entry = add_entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ODESA_5).state == "2"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "settlements"
    assert _options(result) == {KYIV[0]: "Kyiv", ODESA[0]: "Odesa"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SETTLEMENTS: [KYIV[0]]}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SETTLEMENTS: {KYIV[0]: KYIV[1]}}
    assert hass.states.get(KYIV_5).state == "1"
    assert hass.states.get(ODESA_5) is None
    assert er.async_get(hass).async_get(ODESA_5) is None


async def test_options_start_from_tracked(hass: HomeAssistant, mock_api) -> None:
    """Options list a tracked settlement even with no parcels there."""
    entry = add_entry(hass, {IVANO_FRANKIVSK[0]: IVANO_FRANKIVSK[1]})
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert _options(result) == {
        IVANO_FRANKIVSK[0]: "Ivano-Frankivs'k",
        KYIV[0]: "Kyiv",
        ODESA[0]: "Odesa",
    }
    assert _picked(result) == [IVANO_FRANKIVSK[0]]
