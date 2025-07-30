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
            name="Tecnosystemi Climate Coordinator",
            config_entry=config_entry,
            update_interval=timedelta(seconds=30),
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
            async with asyncio.timeout(30):
                for plant in self._plants:
                    for device in plant.getDevices():
                        # To actually find the zone thermostats, we need to get the state;
                        # Then, we create single climate entities for each of them, with
                        # a single parent device (the Polaris controller).
                        state = await self.api.getDeviceState(
                            device, self.config_entry.data[CONF_PIN]
                        )

                        # Note that this call might fail in case the user has logged in with the
                        # same email using the Tecnosystemi app on his/her personal device. In that
                        # case, we force a new login and try again.
                        if state is None:
                            await self.api.login()
                            state = await self.api.getDeviceState(
                                device, self.config_entry.data[CONF_PIN]
                            )

                        for zone in state["Zones"]:
                            zone["Device"] = device
                            zone["Plant"] = plant
                            data[
                                f"{plant.LVPL_Id}_{device.Serial}_{zone['ZoneId']}"
                            ] = zone

                    return data
        except RuntimeError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from None
