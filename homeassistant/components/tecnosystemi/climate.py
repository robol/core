"""Support for the Airzone Cloud climate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import CONF_PIN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TecnosystemiConfigEntry
from .api import Device
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TecnosystemiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tecnosystemi climate entities from a config entry."""
    api = entry.runtime_data

    # We find all plants from the user, and the relevant plants. Right now,
    # the are all added as climate entities.
    entities = []
    for plant in await api.GetPlants():
        # print(f"Found plant: {plant.LVPL_Name} with ID: {plant.LVPL_Id}")

        for device in plant.getDevices():
            # print("  Device:", device.Name, "Serial:", device.Serial)

            # To actually find the zone thermostats, we need to get the state;
            # Then, we create single climate entities for each of them, with
            # a single parent device (the Polaris controller).
            state = await api.getDeviceState(device, entry.data[CONF_PIN])
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

                entity = TecnosystemiClimateEntity(
                    device=device, config=entry, zone=zone
                )
                entities.append(entity)

    async_add_entities(entities)


class TecnosystemiClimateEntity(ClimateEntity):
    """Minimal Climate entity for Tecnosystemi integration."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_hvac_mode = HVACMode.OFF
    _attr_hvac_action = None  # Could be none, "heating", "cooling"

    def __init__(
        self, device: Device, config: TecnosystemiConfigEntry, zone: dict
    ) -> None:
        """Initialize the climate entity."""
        self.zone_state = zone

        self._attr_unique_id = device.Serial + "_" + str(zone["ZoneId"])

        self._attr_name = zone["Name"] + " - " + device.Name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Tecnosystemi",
            model="ProAir",
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if "Temp" in self.zone_state:
            return float(self.zone_state["Temp"]) / 10.0
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if "SetTemp" in self.zone_state:
            return float(self.zone_state["SetTemp"]) / 10.0
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        # Implement setting temperature here
        return

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        # Implement setting HVAC mode here
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()
