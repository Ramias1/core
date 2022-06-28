"""Weather component that handles meteorological data for your location."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Final, TypedDict, final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_UNITS_OF_MEASUREMENT,
    LENGTH_INCHES,
    LENGTH_KILOMETERS,
    LENGTH_MILES,
    LENGTH_MILLIMETERS,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    PRESSURE_HPA,
    PRESSURE_INHG,
    SPEED_KILOMETERS_PER_HOUR,
    SPEED_METERS_PER_SECOND,
    SPEED_MILES_PER_HOUR,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import (
    distance as distance_util,
    pressure as pressure_util,
    speed as speed_util,
    temperature as temperature_util,
)

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

ATTR_CONDITION_CLASS = "condition_class"
ATTR_CONDITION_CLEAR_NIGHT = "clear-night"
ATTR_CONDITION_CLOUDY = "cloudy"
ATTR_CONDITION_EXCEPTIONAL = "exceptional"
ATTR_CONDITION_FOG = "fog"
ATTR_CONDITION_HAIL = "hail"
ATTR_CONDITION_LIGHTNING = "lightning"
ATTR_CONDITION_LIGHTNING_RAINY = "lightning-rainy"
ATTR_CONDITION_PARTLYCLOUDY = "partlycloudy"
ATTR_CONDITION_POURING = "pouring"
ATTR_CONDITION_RAINY = "rainy"
ATTR_CONDITION_SNOWY = "snowy"
ATTR_CONDITION_SNOWY_RAINY = "snowy-rainy"
ATTR_CONDITION_SUNNY = "sunny"
ATTR_CONDITION_WINDY = "windy"
ATTR_CONDITION_WINDY_VARIANT = "windy-variant"
ATTR_FORECAST = "forecast"
ATTR_FORECAST_CONDITION: Final = "condition"
ATTR_FORECAST_PRECIPITATION: Final = "precipitation"
ATTR_FORECAST_PRECIPITATION_PROBABILITY: Final = "precipitation_probability"
ATTR_FORECAST_PRESSURE: Final = "pressure"
ATTR_FORECAST_TEMP: Final = "temperature"
ATTR_FORECAST_TEMP_LOW: Final = "templow"
ATTR_FORECAST_TIME: Final = "datetime"
ATTR_FORECAST_WIND_BEARING: Final = "wind_bearing"
ATTR_FORECAST_WIND_SPEED: Final = "wind_speed"
ATTR_WEATHER_HUMIDITY = "humidity"
ATTR_WEATHER_OZONE = "ozone"
ATTR_WEATHER_PRESSURE = "pressure"
ATTR_WEATHER_TEMPERATURE = "temperature"
ATTR_WEATHER_VISIBILITY = "visibility"
ATTR_WEATHER_WIND_BEARING = "wind_bearing"
ATTR_WEATHER_WIND_SPEED = "wind_speed"
ATTR_WEATHER_PRECIPITATION = "precipitation"

DOMAIN = "weather"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

SCAN_INTERVAL = timedelta(seconds=30)

ROUNDING_PRECISION = 2

VALID_UNITS: dict[str, tuple[str, ...]] = {
    ATTR_WEATHER_TEMPERATURE: temperature_util.VALID_UNITS,
    ATTR_WEATHER_PRESSURE: pressure_util.VALID_UNITS,
    ATTR_WEATHER_VISIBILITY: (LENGTH_KILOMETERS, LENGTH_MILES),
    ATTR_WEATHER_WIND_SPEED: (
        SPEED_KILOMETERS_PER_HOUR,
        SPEED_MILES_PER_HOUR,
        SPEED_METERS_PER_SECOND,
    ),
    ATTR_WEATHER_PRECIPITATION: (LENGTH_MILLIMETERS, LENGTH_INCHES),
}

METRIC_UNITS = {
    ATTR_WEATHER_TEMPERATURE: TEMP_CELSIUS,
    ATTR_WEATHER_PRESSURE: PRESSURE_HPA,
    ATTR_WEATHER_VISIBILITY: LENGTH_KILOMETERS,
    ATTR_WEATHER_WIND_SPEED: SPEED_KILOMETERS_PER_HOUR,
    ATTR_WEATHER_PRECIPITATION: LENGTH_MILLIMETERS,
}

IMPERIAL_UNITS = {
    ATTR_WEATHER_TEMPERATURE: TEMP_FAHRENHEIT,
    ATTR_WEATHER_PRESSURE: PRESSURE_INHG,
    ATTR_WEATHER_VISIBILITY: LENGTH_MILES,
    ATTR_WEATHER_WIND_SPEED: SPEED_MILES_PER_HOUR,
    ATTR_WEATHER_PRECIPITATION: LENGTH_INCHES,
}


class Forecast(TypedDict, total=False):
    """Typed weather forecast dict."""

    condition: str | None
    datetime: str
    precipitation_probability: int | None
    precipitation: float | None
    pressure: float | None
    temperature: float | None
    templow: float | None
    wind_bearing: float | str | None
    wind_speed: float | None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the weather component."""
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    await component.async_setup(config)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    component: EntityComponent = hass.data[DOMAIN]
    return await component.async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    component: EntityComponent = hass.data[DOMAIN]
    return await component.async_unload_entry(entry)


@dataclass
class WeatherEntityDescription(EntityDescription):
    """A class that describes weather entities."""


class WeatherEntity(Entity):
    """ABC for weather data."""

    entity_description: WeatherEntityDescription
    _attr_condition: str | None
    _attr_forecast: list[Forecast] | None = None
    _attr_humidity: float | None = None
    _attr_ozone: float | None = None
    _attr_precision: float
    _attr_pressure: float | None = None
    _attr_pressure_unit: str | None = None
    _attr_state: None = None
    _attr_temperature_unit: str
    _attr_temperature: float | None
    _attr_visibility: float | None = None
    _attr_visibility_unit: str | None = None
    _attr_precipitation_unit: str | None = None
    _attr_wind_bearing: float | str | None = None
    _attr_wind_speed: float | None = None
    _attr_wind_speed_unit: str | None = None
    _option_units_of_measurement: dict[str, str | None] | None = None

    async def async_internal_added_to_hass(self) -> None:
        """Call when the sensor entity is added to hass."""
        await super().async_internal_added_to_hass()
        if not self.registry_entry:
            return
        self.async_registry_entry_updated()

    @property
    def preferred_units(self) -> dict[str, str]:
        """Return the units this integration prefers to use for weather measurement."""
        return METRIC_UNITS if self.hass.config.units.is_metric else IMPERIAL_UNITS

    def displayed_unit(self, quantity: str) -> str:
        """Return the unit the integration will use to measure a given quantity."""
        unit = self.preferred_units[quantity]
        if self._option_units_of_measurement is not None:
            if opt := self._option_units_of_measurement.get(quantity):
                if opt in VALID_UNITS[quantity]:
                    return opt
        return unit

    @property
    def temperature(self) -> float | None:
        """Return the platform temperature in native units (i.e. not converted)."""
        return self._attr_temperature

    @property
    def temperature_unit(self) -> str:
        """Return the native unit of measurement for temperature."""
        return self._attr_temperature_unit

    @property
    def pressure(self) -> float | None:
        """Return the pressure in native units."""
        return self._attr_pressure

    @property
    def pressure_unit(self) -> str | None:
        """Return the native unit of measurement for pressure."""
        return self._attr_pressure_unit

    @property
    def humidity(self) -> float | None:
        """Return the humidity in native units."""
        return self._attr_humidity

    @property
    def wind_speed(self) -> float | None:
        """Return the wind speed in native units."""
        return self._attr_wind_speed

    @property
    def wind_speed_unit(self) -> str | None:
        """Return the native unit of measurement for wind speed."""
        return self._attr_wind_speed_unit

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the wind bearing."""
        return self._attr_wind_bearing

    @property
    def ozone(self) -> float | None:
        """Return the ozone level."""
        return self._attr_ozone

    @property
    def visibility(self) -> float | None:
        """Return the visibility in native units."""
        return self._attr_visibility

    @property
    def visibility_unit(self) -> str | None:
        """Return the native unit of measurement for visibility."""
        return self._attr_visibility_unit

    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the forecast in native units."""
        return self._attr_forecast

    @property
    def precipitation_unit(self) -> str | None:
        """Return the native unit of measurement for accumulated precipitation."""
        return self._attr_precipitation_unit

    @property
    def precision(self) -> float:
        """Return the precision of the temperature value, after unit conversion."""
        if hasattr(self, "_attr_precision"):
            return self._attr_precision
        return (
            PRECISION_TENTHS
            if self.hass.config.units.temperature_unit == TEMP_CELSIUS
            else PRECISION_WHOLE
        )

    def convert_temperature(self, temperature: float, unit: str) -> float:
        """Convert a temperature from a given units to the displayed units."""
        displayed = self.displayed_unit(ATTR_WEATHER_TEMPERATURE)
        temperature = temperature_util.convert(temperature, unit, displayed)
        if displayed == TEMP_CELSIUS:
            return round(temperature, 1)
        return round(temperature)

    def convert_pressure(self, pressure: float, unit: str) -> float:
        """Convert a pressure from a given units to the displayed units."""
        displayed = self.displayed_unit(ATTR_WEATHER_PRESSURE)
        pressure = pressure_util.convert(pressure, unit, displayed)
        return round(pressure, ROUNDING_PRECISION)

    def convert_wind_speed(self, wind_speed: float, unit: str) -> float:
        """Convert a wind speed from a given units to the displayed units."""
        displayed = self.displayed_unit(ATTR_WEATHER_WIND_SPEED)
        wind_speed = speed_util.convert(wind_speed, unit, displayed)
        return round(wind_speed, ROUNDING_PRECISION)

    def convert_visibility(self, visibility: float, unit: str) -> float:
        """Convert a visibility from a given units to the displayed units."""
        displayed = self.displayed_unit(ATTR_WEATHER_VISIBILITY)
        visibility = distance_util.convert(visibility, unit, displayed)
        return round(visibility, ROUNDING_PRECISION)

    def convert_precipitation(self, precipitation: float, unit: str) -> float:
        """Convert a precipitation from a given units to the displayed units."""
        displayed = self.displayed_unit(ATTR_WEATHER_PRECIPITATION)
        precipitation = distance_util.convert(precipitation, unit, displayed)
        return round(precipitation, ROUNDING_PRECISION)

    @final
    @property
    def state_attributes(self):
        """Return the state attributes, converted from native units to user-configured units."""
        data = {}
        if (temperature := self.temperature) is not None:
            if (unit := self.temperature_unit) is not None:
                temperature = self.convert_temperature(temperature, unit)
            data[ATTR_WEATHER_TEMPERATURE] = temperature

        if (humidity := self.humidity) is not None:
            data[ATTR_WEATHER_HUMIDITY] = round(humidity)

        if (ozone := self.ozone) is not None:
            data[ATTR_WEATHER_OZONE] = ozone

        if (pressure := self.pressure) is not None:
            if (unit := self.pressure_unit) is not None:
                pressure = self.convert_pressure(pressure, unit)
            data[ATTR_WEATHER_PRESSURE] = round(pressure, ROUNDING_PRECISION)

        if (wind_bearing := self.wind_bearing) is not None:
            data[ATTR_WEATHER_WIND_BEARING] = wind_bearing

        if (wind_speed := self.wind_speed) is not None:
            if (unit := self.wind_speed_unit) is not None:
                wind_speed = self.convert_wind_speed(wind_speed, unit)
            data[ATTR_WEATHER_WIND_SPEED] = wind_speed

        if (visibility := self.visibility) is not None:
            if (unit := self.visibility_unit) is not None:
                displayed = self.displayed_unit(ATTR_WEATHER_VISIBILITY)
                visibility = round(
                    distance_util.convert(visibility, unit, displayed),
                    ROUNDING_PRECISION,
                )
            data[ATTR_WEATHER_VISIBILITY] = visibility

        if self.forecast is not None:
            forecast = []
            for forecast_entry in self.forecast:
                forecast_entry = dict(forecast_entry)
                if (temp := forecast_entry.get(ATTR_FORECAST_TEMP)) is not None:
                    if (unit := self.temperature_unit) is not None:
                        forecast_entry[ATTR_FORECAST_TEMP] = self.convert_temperature(
                            temp, unit
                        )
                if (temp := forecast_entry.get(ATTR_FORECAST_TEMP_LOW)) is not None:
                    if (unit := self.temperature_unit) is not None:
                        forecast_entry[
                            ATTR_FORECAST_TEMP_LOW
                        ] = self.convert_temperature(temp, unit)
                if (pressure := forecast_entry.get(ATTR_FORECAST_PRESSURE)) is not None:
                    if (unit := self.pressure_unit) is not None:
                        forecast_entry[ATTR_FORECAST_PRESSURE] = self.convert_pressure(
                            pressure, unit
                        )
                if (
                    wind_speed := forecast_entry.get(ATTR_FORECAST_WIND_SPEED)
                ) is not None:
                    if (unit := self.wind_speed_unit) is not None:
                        forecast_entry[
                            ATTR_FORECAST_WIND_SPEED
                        ] = self.convert_wind_speed(wind_speed, unit)
                if (
                    precip := forecast_entry.get(ATTR_FORECAST_PRECIPITATION)
                ) is not None:
                    if (unit := self.precipitation_unit) is not None:
                        forecast_entry[
                            ATTR_FORECAST_PRECIPITATION
                        ] = self.convert_precipitation(precip, unit)

                forecast.append(forecast_entry)

            data[ATTR_FORECAST] = forecast

        return data

    @property
    @final
    def state(self) -> str | None:
        """Return the current state."""
        return self.condition

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        return self._attr_condition

    @callback
    def async_registry_entry_updated(self) -> None:
        """Run when the entity registry entry has been updated."""
        print("registry update!")
        assert self.registry_entry
        if (weather_options := self.registry_entry.options.get(DOMAIN)) and (
            custom_units := weather_options.get(CONF_UNITS_OF_MEASUREMENT)
        ):
            self._option_units_of_measurement = custom_units
            return

        self._option_units_of_measurement = None
