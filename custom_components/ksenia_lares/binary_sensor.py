"""This component provides support for Lares motion/door events."""
import asyncio
import datetime
import logging
from typing import Any

import async_timeout

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.switch import SwitchEntity

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DEFAULT_TIMEOUT,
    ZONE_STATUS_ALARM,
    ZONE_STATUS_NOT_USED,
    ZONE_BYPASS_ON,
)
from .base import LaresBase

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = 10

DEFAULT_DEVICE_CLASS = "motion"
DOOR_DEVICE_CLASS = "door"


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up binary sensors attached to a Lares alarm device from a config entry."""

    client = LaresBase(config_entry.data)
    zones_descriptions = await client.zoneDescriptions()
    _LOGGER.info("There are {num} zones".format(num=len(zones_descriptions)))
    partitions_descriptions = await client.partitions()
    _LOGGER.info("There are {num} partitions".format(num=len(partitions_descriptions)))
    outputs_descriptions = await client.outputDescriptions()
    _LOGGER.info("There are {num} outputs".format(num=len(outputs_descriptions)))

    async def async_update_data():
        async with async_timeout.timeout(DEFAULT_TIMEOUT):
            return await client.zones()

    async def async_update_partitions():
        async with async_timeout.timeout(DEFAULT_TIMEOUT):
            return await client.partitionsStatus()

    async def async_update_outputs():
        async with async_timeout.timeout(DEFAULT_TIMEOUT):
            return await client.outputs()

    interval = None
    if "rate" in config_entry.data and config_entry.data["rate"] is not None:
        interval = timedelta(seconds=int(config_entry.data["rate"]))
    else:
        interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    _LOGGER.info("setting interval to %i seconds", interval.seconds)

    # ZONES
    zones_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="lares_zones",
        update_method=async_update_data,
        update_interval=interval,
    )

    # Fetch initial data so we have data when entities subscribe
    await zones_coordinator.async_refresh()

    def filter_active_zones(sensor):
        _LOGGER.info("filter_active_zones %s", sensor)
        return sensor[1]["status"] != ZONE_STATUS_NOT_USED

    async_add_devices(
        LaresSensor(zones_coordinator, idx, zones_descriptions[idx])
        for idx, zone in filter(filter_active_zones, enumerate(zones_coordinator.data))
    )

    # PARTITIONS
    coordinator_partitions = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="lares_partitions",
        update_method=async_update_partitions,
        update_interval=interval,
    )

    await coordinator_partitions.async_refresh()

    def filter_active_partition(partition):
        _LOGGER.info("filter_active_partition %s", partition)
        return True

    async_add_devices(
        LaresPartition(coordinator_partitions, idx, partitions_descriptions[idx])
        for idx, zone in
        filter(filter_active_partition, enumerate(coordinator_partitions.data))
    )

    # OUTPUTS
    coordinator_outputs = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="lares_outputs",
        update_method=async_update_outputs,
        update_interval=interval,
    )

    await coordinator_outputs.async_refresh()

    def filter_active_output(output):
        _LOGGER.info("filter_active_output %s", output)
        return output[1]["type"] != ZONE_STATUS_NOT_USED

    async_add_devices(
        LaresOutput(coordinator_outputs, idx, outputs_descriptions[idx])
        for idx, out in filter(filter_active_output, enumerate(coordinator_outputs.data))
    )


class LaresSensor(CoordinatorEntity, BinarySensorEntity):
    """An implementation of a Lares door/window/motion sensor."""

    def __init__(self, coordinator, idx, description):
        """Initialize a the switch."""
        super().__init__(coordinator)

        self._coordinator = coordinator
        self._description = description
        self._idx = idx

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"lares_zones_{self._idx}"

    @property
    def name(self):
        """Return the name of this camera."""
        return self._description

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._coordinator.data[self._idx]["status"] == ZONE_STATUS_ALARM

    @property
    def available(self):
        """Return True if entity is available."""
        status = self._coordinator.data[self._idx]["status"]

        return status != ZONE_STATUS_NOT_USED or status == ZONE_BYPASS_ON

    @property
    def device_class(self):
        """Return the class of this device."""
        return DEFAULT_DEVICE_CLASS

    @property
    def enabled(self):
        return self._coordinator.data[self._idx]["status"] != ZONE_STATUS_NOT_USED


class LaresPartition(CoordinatorEntity, BinarySensorEntity):

    def __init__(self, coordinator, idx, description):
        """Initialize a the switch."""
        super().__init__(coordinator)

        self._coordinator = coordinator
        self._description = description
        self._idx = idx

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return (self._coordinator.data[self._idx] == "ARMED" or self._coordinator.data[self._idx] == "ARMED_IMMEDIATE")

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"lares_partition_{self._idx}"

    @property
    def name(self):
        """Return the name of this camera."""
        return self._description

    @property
    def available(self):
        """Return True if entity is available."""
        return True

    @property
    def enabled(self):
        return True


class LaresOutput(CoordinatorEntity, BinarySensorEntity):

    def __init__(self, coordinator, idx, description):
        """Initialize a the switch."""
        super().__init__(coordinator)

        self._coordinator = coordinator
        self._description = description
        self._idx = idx

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return f"lares_output_{self._idx}"

    @property
    def name(self):
        """Return the name of this camera."""
        return self._description

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._coordinator.data[self._idx]["status"] == "ON"

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.data[self._idx]["type"] != ZONE_STATUS_NOT_USED

    @property
    def enabled(self):
        return self._coordinator.data[self._idx]["type"] != ZONE_STATUS_NOT_USED
