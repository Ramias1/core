"""Support gathering ted5000 and ted6000 information."""
import logging

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    ELECTRIC_POTENTIAL_VOLT,
    ENERGY_WATT_HOUR,
    POWER_WATT,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)

SENSORS = (
    SensorEntityDescription(
        key="consumption",
        name="Current Energy Consumption",
        native_unit_of_measurement=POWER_WATT,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="daily_consumption",
        name="Today's Energy Consumption",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=STATE_CLASS_MEASUREMENT,
        device_class=DEVICE_CLASS_ENERGY,
    ),
    SensorEntityDescription(
        key="mtd_consumption",
        name="Month to Date Energy Consumption",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        device_class=DEVICE_CLASS_ENERGY,
    ),
)

SPYDER_SENSORS = (
    SensorEntityDescription(
        key="consumption",
        name="Current Energy Consumption",
        native_unit_of_measurement=POWER_WATT,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mtd_consumption",
        name="Month to Date Energy Consumption",
        native_unit_of_measurement=ENERGY_WATT_HOUR,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        device_class=DEVICE_CLASS_ENERGY,
    ),
)

MTU_SENSORS = (
    SensorEntityDescription(
        key="consumption",
        name="Current Energy Consumption",
        native_unit_of_measurement=POWER_WATT,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="voltage",
        name="Voltage",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_VOLT,
    ),
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up envoy sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = data[COORDINATOR]
    name = data[NAME]

    entities = []
    for sensor_description in SENSORS:
        if coordinator.data["is_5000"] and sensor_description.key != "consumption":
            continue  # TED 5000 does not support aggregate values for power
        entity_name = f"{name} {sensor_description.name}"
        entities.append(
            TedSensor(
                sensor_description, entity_name, config_entry.unique_id, coordinator
            )
        )
    for spyder_id, spyder in coordinator.data["spyders"].items():
        spyder_name = spyder["name"]
        for sensor_description in SPYDER_SENSORS:
            entity_name = f"{spyder_name} {sensor_description.name}"
            entities.append(
                TedBreakdownSensor(
                    "spyders",
                    spyder_id,
                    sensor_description,
                    entity_name,
                    config_entry.unique_id,
                    coordinator,
                )
            )
    for mtu_id, mtu in coordinator.data["mtus"].items():
        mtu_name = mtu["name"]
        for sensor_description in MTU_SENSORS:
            entity_name = f"{mtu_name} {sensor_description.name}"
            entities.append(
                TedBreakdownSensor(
                    "mtus",
                    mtu_id,
                    sensor_description,
                    entity_name,
                    config_entry.unique_id,
                    coordinator,
                )
            )

    async_add_entities(entities)
    return True


class TedSensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Ted5000 and Ted6000 sensor."""

    def __init__(self, description, name, device_id, coordinator):
        """Initialize the sensor."""
        self.entity_description = description
        self._device_id = device_id
        self._name = name

        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:flash"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return f"{self._device_id}_{self.entity_description.key}"

    @property
    def state(self):
        """Return the state of the resources."""
        return self.coordinator.data.get(self.entity_description.key)


class TedBreakdownSensor(TedSensor):
    """Implementation of a Ted5000 and Ted6000 mtu or spyder."""

    def __init__(self, group, position, description, name, device_id, coordinator):
        """Initialize the sensor."""
        self._group = group
        self._position = position
        super().__init__(description, name, device_id, coordinator)

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return f"{self._device_id}_{self._group}_{self._position}_{self.entity_description.key}"

    @property
    def state(self):
        """Return the state of the resources."""
        return (
            self.coordinator.data[self._group]
            .get(self._position)
            .get(self.entity_description.key)
        )
