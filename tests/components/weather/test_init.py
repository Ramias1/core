"""The test for weather entity."""
import pytest
from pytest import approx

from homeassistant.components.weather import (
    ATTR_CONDITION_SUNNY,
    ATTR_FORECAST,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_WIND_SPEED,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_VISIBILITY,
    ATTR_WEATHER_WIND_SPEED,
)
from homeassistant.const import (
    LENGTH_MILES,
    LENGTH_MILLIMETERS,
    PRESSURE_HPA,
    PRESSURE_INHG,
    PRESSURE_KPA,
    PRESSURE_MMHG,
    SPEED_KILOMETERS_PER_HOUR,
    SPEED_METERS_PER_SECOND,
    SPEED_MILES_PER_HOUR,
    TEMP_FAHRENHEIT,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util.distance import convert as convert_distance
from homeassistant.util.pressure import convert as convert_pressure
from homeassistant.util.speed import convert as convert_speed
from homeassistant.util.temperature import convert as convert_temperature
from homeassistant.util.unit_system import IMPERIAL_SYSTEM, METRIC_SYSTEM


async def create_entity(hass, **kwargs):
    """Create the weather entity to run tests on."""
    kwargs = {"temperature": None, "temperature_unit": None, **kwargs}
    platform = getattr(hass.components, "test.weather")
    platform.init(empty=True)
    platform.ENTITIES.append(
        platform.MockWeatherMockForecast(
            name="Test", condition=ATTR_CONDITION_SUNNY, **kwargs
        )
    )

    entity0 = platform.ENTITIES[0]
    assert await async_setup_component(
        hass, "weather", {"weather": {"platform": "test"}}
    )
    await hass.async_block_till_done()
    return entity0


@pytest.mark.parametrize("unit_system", [IMPERIAL_SYSTEM, METRIC_SYSTEM])
async def test_temperature_conversion(
    hass,
    enable_custom_integrations,
    unit_system,
):
    """Test temperature conversion."""
    hass.config.units = unit_system
    native_value = 38
    native_unit = TEMP_FAHRENHEIT

    entity0 = await create_entity(
        hass, temperature=native_value, temperature_unit=native_unit
    )

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = convert_temperature(
        native_value, native_unit, unit_system.temperature_unit
    )
    assert float(state.attributes[ATTR_WEATHER_TEMPERATURE]) == approx(
        expected, rel=0.1
    )
    assert float(forecast[ATTR_FORECAST_TEMP]) == approx(expected, rel=0.1)
    assert float(forecast[ATTR_FORECAST_TEMP_LOW]) == approx(expected, rel=0.1)


@pytest.mark.parametrize(
    "unit_system,display_unit",
    [(IMPERIAL_SYSTEM, PRESSURE_INHG), (METRIC_SYSTEM, PRESSURE_HPA)],
)
async def test_pressure_conversion(
    hass,
    enable_custom_integrations,
    unit_system,
    display_unit,
):
    """Test pressure conversion."""
    hass.config.units = unit_system
    native_value = 30
    native_unit = PRESSURE_INHG

    entity0 = await create_entity(
        hass, pressure=native_value, pressure_unit=native_unit
    )
    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = convert_pressure(native_value, native_unit, display_unit)
    assert float(state.attributes[ATTR_WEATHER_PRESSURE]) == approx(expected, rel=1e-2)
    assert float(forecast[ATTR_FORECAST_PRESSURE]) == approx(expected, rel=1e-2)


@pytest.mark.parametrize(
    "unit_system,display_unit",
    [
        (IMPERIAL_SYSTEM, SPEED_MILES_PER_HOUR),
        (METRIC_SYSTEM, SPEED_KILOMETERS_PER_HOUR),
    ],
)
async def test_wind_speed_conversion(
    hass,
    enable_custom_integrations,
    unit_system,
    display_unit,
):
    """Test wind speed conversion."""
    hass.config.units = unit_system
    native_value = 10
    native_unit = SPEED_METERS_PER_SECOND

    entity0 = await create_entity(
        hass, wind_speed=native_value, wind_speed_unit=native_unit
    )

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = convert_speed(native_value, native_unit, display_unit)
    assert float(state.attributes[ATTR_WEATHER_WIND_SPEED]) == approx(
        expected, rel=1e-2
    )
    assert float(forecast[ATTR_FORECAST_WIND_SPEED]) == approx(expected, rel=1e-2)


@pytest.mark.parametrize("unit_system", [IMPERIAL_SYSTEM, METRIC_SYSTEM])
async def test_visibility_conversion(
    hass,
    enable_custom_integrations,
    unit_system,
):
    """Test visibility conversion."""
    hass.config.units = unit_system
    native_value = 10
    native_unit = LENGTH_MILES

    entity0 = await create_entity(
        hass, visibility=native_value, visibility_unit=native_unit
    )

    state = hass.states.get(entity0.entity_id)
    expected = convert_distance(native_value, native_unit, unit_system.length_unit)
    assert float(state.attributes[ATTR_WEATHER_VISIBILITY]) == approx(
        expected, rel=1e-2
    )


@pytest.mark.parametrize("unit_system", [IMPERIAL_SYSTEM, METRIC_SYSTEM])
async def test_precipitation_conversion(
    hass,
    enable_custom_integrations,
    unit_system,
):
    """Test precipitation conversion."""
    hass.config.units = unit_system
    native_value = 30
    native_unit = LENGTH_MILLIMETERS

    entity0 = await create_entity(
        hass, precipitation=native_value, precipitation_unit=native_unit
    )

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    expected = convert_distance(
        native_value, native_unit, unit_system.accumulated_precipitation_unit
    )
    assert float(forecast[ATTR_FORECAST_PRECIPITATION]) == approx(expected, rel=1e-2)


async def test_none_forecast(
    hass,
    enable_custom_integrations,
):
    """Test that conversion with None values succeeds."""
    entity0 = await create_entity(
        hass,
        pressure=None,
        pressure_unit=PRESSURE_INHG,
        wind_speed=None,
        wind_speed_unit=SPEED_METERS_PER_SECOND,
        precipitation=None,
        precipitation_unit=LENGTH_MILLIMETERS,
    )

    state = hass.states.get(entity0.entity_id)
    forecast = state.attributes[ATTR_FORECAST][0]

    assert forecast[ATTR_FORECAST_PRESSURE] is None
    assert forecast[ATTR_FORECAST_WIND_SPEED] is None
    assert forecast[ATTR_FORECAST_PRECIPITATION] is None


@pytest.mark.parametrize(
    "attribute,state_unit,custom_unit,state_value,custom_value",
    [
        ("pressure", PRESSURE_HPA, PRESSURE_INHG, 1000.0, 29.53),
        ("pressure", PRESSURE_KPA, PRESSURE_HPA, 1.234, 12.34),
        ("pressure", PRESSURE_HPA, PRESSURE_MMHG, 1000, 750),
        ("pressure", PRESSURE_HPA, "peer_pressure", 1000, 1000),
    ],
)
async def test_custom_unit(
    hass,
    enable_custom_integrations,
    attribute,
    state_unit,
    custom_unit,
    state_value,
    custom_value,
):
    """Test custom unit."""
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get_or_create("weather", "test", "very_unique")
    entity_registry.async_update_entity_options(
        entry.entity_id, "weather", {"units_of_measurement": {attribute: custom_unit}}
    )
    await hass.async_block_till_done()

    entity0 = await create_entity(
        hass,
        unique_id="very_unique",
        **{attribute: state_value, attribute + "_unit": state_unit},
    )

    state = hass.states.get(entity0.entity_id)
    assert float(state.attributes[attribute]) == approx(custom_value, rel=1e-2)


@pytest.mark.parametrize(
    "attribute,state_unit,custom_unit,state_value,custom_value",
    [
        ("pressure", PRESSURE_HPA, PRESSURE_INHG, 1000.0, 29.53),
        ("pressure", PRESSURE_HPA, PRESSURE_MMHG, 1000, 750),
        ("pressure", PRESSURE_HPA, "peer_pressure", 1000, 1000),
    ],
)
async def test_custom_unit_change(
    hass,
    enable_custom_integrations,
    attribute,
    state_unit,
    custom_unit,
    state_value,
    custom_value,
):
    """Test custom unit changes are picked up."""
    entity_registry = er.async_get(hass)
    entity0 = await create_entity(
        hass,
        unique_id="very_unique",
        **{attribute: state_value, attribute + "_unit": state_unit},
    )

    state = hass.states.get(entity0.entity_id)
    assert float(state.attributes[attribute]) == approx(float(state_value))

    entity_registry.async_update_entity_options(
        "weather.test", "weather", {"units_of_measurement": {attribute: custom_unit}}
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity0.entity_id)
    assert float(state.attributes[attribute]) == approx(float(custom_value), rel=1e-2)

    entity_registry.async_update_entity_options(
        "weather.test", "weather", {"units_of_measurement": {attribute: state_unit}}
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity0.entity_id)
    assert float(state.attributes[attribute]) == approx(float(state_value))

    entity_registry.async_update_entity_options("weather.test", "weather", None)
    await hass.async_block_till_done()

    state = hass.states.get(entity0.entity_id)
    assert float(state.attributes[attribute]) == approx(float(state_value))
