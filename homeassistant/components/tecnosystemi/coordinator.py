"""Coordinator for Tecnosystemi integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.const import CONF_PIN
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class TecnosystemiCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, config_entry, api):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Tecnosystemi Climate Coordinator",
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=30),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True,
        )
        self.api = api
        self._plants = []

    async def _async_setup(self):
        """Set up the coordinator.

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        self._plants = await self.api.GetPlants()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = {}

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(10):
                for plant in self._plants:
                    for device in plant.getDevices():
                        # To actually find the zone thermostats, we need to get the state;
                        # Then, we create single climate entities for each of them, with
                        # a single parent device (the Polaris controller).
                        state = await self.api.getDeviceState(
                            device, self.config_entry.data[CONF_PIN]
                        )

                        for zone in state["Zones"]:
                            # print("  Zone:", zone["Name"], "ID:", zone["ZoneId"])
                            zone["Device"] = device
                            zone["Plant"] = plant
                            data[
                                f"{plant.LVPL_Id}_{device.Serial}_{zone['ZoneId']}"
                            ] = zone

                    return data
        except RuntimeError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from None
