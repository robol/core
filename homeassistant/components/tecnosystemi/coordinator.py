"""Coordinator for Tecnosystemi integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.const import CONF_PIN
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class TecnoSystemiCoordinator(DataUpdateCoordinator):
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

        self.last_request_failed = False

    async def _async_setup(self):
        """Set up the coordinator.

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        # self._device = await self.my_api.get_device()
        self._plants = await self.api.GetPlants()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = {}

        if self.last_request_failed:
            _LOGGER.warning("Last request failed, triggering new login")
            await self.api.login()

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_idx = set(self.async_contexts())
                for plant in self._plants:
                    # print(f"Found plant: {plant.LVPL_Name} with ID: {plant.LVPL_Id}")

                    for device in plant.getDevices():
                        # print("  Device:", device.Name, "Serial:", device.Serial)

                        # To actually find the zone thermostats, we need to get the state;
                        # Then, we create single climate entities for each of them, with
                        # a single parent device (the Polaris controller).
                        state = await self.api.getDeviceState(
                            device, self.config_entry.data[CONF_PIN]
                        )
                        # print("  State:", json.dumps(state))

                        # Sample output for state:
                        # {"Zones": [
                        #    {"ZoneId": 1, "Name": "SALOTTO", "IsMaster": true, "IsOFF": true, "Temp": "265", "SetTemp": "260", "Serranda": 0, "SerrandaSet": 0, "Fancoil": -1, "FancoilSet": 0, "EV": -1, "IsCronoMode": false, "IsCronoActive": true, "Errors": 0, "Umd": "594", "SetUmd": null, "CWin": -1, "CBadge": -1, "COff": false},
                        #    {"ZoneId": 2, "Name": "CUCINA", "IsMaster": false, "IsOFF": true, "Temp": "266", "SetTemp": "260", "Serranda": 0, "SerrandaSet": 0, "Fancoil": -1, "FancoilSet": -1, "EV": -1, "IsCronoMode": false, "IsCronoActive": false, "Errors": 0, "Umd": "603", "SetUmd": null, "CWin": -1, "CBadge": -1, "COff": false},
                        #    {"ZoneId": 3, "Name": "CAMERETTA", "IsMaster": false, "IsOFF": true, "Temp": "265", "SetTemp": "220", "Serranda": 0, "SerrandaSet": 0, "Fancoil": -1, "FancoilSet": -1, "EV": -1, "IsCronoMode": false, "IsCronoActive": false, "Errors": 0, "Umd": "599", "SetUmd": null, "CWin": -1, "CBadge": -1, "COff": false},
                        #    {"ZoneId": 4, "Name": "STUDIO", "IsMaster": false, "IsOFF": false, "Temp": "263", "SetTemp": "210", "Serranda": 19, "SerrandaSet": 0, "Fancoil": -1, "FancoilSet": -1, "EV": -1, "IsCronoMode": false, "IsCronoActive": true, "Errors": 0, "Umd": "565", "SetUmd": null, "CWin": -1, "CBadge": -1, "COff": false},
                        #    {"ZoneId": 5, "Name": "CAMERA", "IsMaster": false, "IsOFF": true, "Temp": "265", "SetTemp": "210", "Serranda": 0, "SerrandaSet": 0, "Fancoil": -1, "FancoilSet": -1, "EV": -1, "IsCronoMode": false, "IsCronoActive": false, "Errors": 0, "Umd": "590", "SetUmd": null, "CWin": -1, "CBadge": -1, "COff": false}], "Errors": 0, "Serial": "414705038650", "Name": "CLIMATIZZATORE", "FWVer": "5.0.15", "IsOFF": false, "IsCooling": true, "OperatingModeCooling": 1, "LastConfigUpdate": "2025-07-26T13:53:32.58", "LastSyncUpdate": "2025-07-26T14:24:43.983", "NumErrors": 0, "Icon": 0, "IrPresent": 1, "TempCan": "230", "IP": "", "FInv": 1, "FEst": 1}
                        # ]}
                        for zone in state["Zones"]:
                            # print("  Zone:", zone["Name"], "ID:", zone["ZoneId"])
                            zone["Device"] = device
                            zone["Plant"] = plant
                            data[
                                f"{plant.LVPL_Id}_{device.Serial}_{zone['ZoneId']}"
                            ] = zone

                    return data
        except RuntimeError as err:
            self.last_request_failed = True
            raise UpdateFailed(f"Error communicating with API: {err}") from None
