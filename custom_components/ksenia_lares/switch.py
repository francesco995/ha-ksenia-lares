"""This component provides support for Lares motion/door events."""
import asyncio
import datetime
import logging
from typing import Any

import async_timeout

from datetime import timedelta

from homeassistant.components.switch import DEVICE_CLASSES, SwitchEntity

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

DEFAULT_DEVICE_CLASS = "switch"


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up binary sensors attached to a Lares alarm device from a config entry."""

    client = LaresBase(config_entry.data)
    descriptions = await client.outputDescriptions()

    async def async_update_data():
        """Perform the actual updates."""

        async with async_timeout.timeout(DEFAULT_TIMEOUT):
            return await client.outputs()

    interval = None
    if "rate" in config_entry.data and config_entry.data["rate"] is not None:
        interval = timedelta(seconds=int(config_entry.data["rate"]))
    else:
        interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

    _LOGGER.info("setting interval to %i seconds", interval.seconds)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="lares_outputs",
        update_method=async_update_data,
        update_interval=interval,
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    def filter_active_sensors(sensor):
        _LOGGER.info("filter_active_output %s", sensor)
        return sensor[1]["type"] != ZONE_STATUS_NOT_USED

    async_add_devices(
        LaresOutput(coordinator, idx, descriptions[idx])
        for idx, zone in filter(filter_active_sensors, enumerate(coordinator.data))
    )


class LaresOutput(CoordinatorEntity, SwitchEntity):

    def turn_on(self, **kwargs: Any) -> None:
        pass

    def turn_off(self, **kwargs: Any) -> None:
        pass

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
        return self._coordinator.data[self._idx]["value"] == 1

    @property
    def available(self):
        """Return True if entity is available."""
        return self._coordinator.data[self._idx]["type"] != ZONE_STATUS_NOT_USED

    @property
    def device_class(self):
        """Return the class of this device."""
        return DEFAULT_DEVICE_CLASS

    @property
    def enabled(self):
        return self._coordinator.data[self._idx]["type"] != ZONE_STATUS_NOT_USED
