"""Support for the Airzone Cloud climate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TecnosystemiConfigEntry
from .const import DOMAIN
from .coordinator import TecnosystemiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TecnosystemiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tecnosystemi climate entities from a config entry."""
    api = entry.runtime_data

    coordinator = TecnosystemiCoordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for device_id in coordinator.data:
        entity = TecnosystemiClimateEntity(
            device_id=device_id,
            zone=coordinator.data[device_id],
            coordinator=coordinator,
        )
        entities.append(entity)

    async_add_entities(entities)


class TecnosystemiClimateEntity(CoordinatorEntity, ClimateEntity):
    """Minimal Climate entity for Tecnosystemi integration."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_hvac_mode = HVACMode.OFF
    _attr_hvac_action = None  # Could be none, "heating", "cooling"

    def __init__(
        self, device_id: str, zone: dict, coordinator: TecnosystemiCoordinator
    ) -> None:
        """Initialize the climate entity."""
        CoordinatorEntity.__init__(self, coordinator)

        self.zone_state = zone
        self.device_id = device_id
        self._attr_unique_id = device_id
        self.coordinator = coordinator

        self._attr_name = zone["Name"] + " - " + zone["Device"].Name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Tecnosystemi",
            model="ProAir",
        )

        # self._handle_coordinator_update()
        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        self._attr_hvac_mode = (
            HVACMode.OFF if self.zone_state["IsOFF"] else HVACMode.COOL
        )
        self._attr_current_temperature = float(self.zone_state["Temp"]) / 10.0
        self._attr_target_temperature = float(self.zone_state["SetTemp"]) / 10.0
        self._attr_current_humidity = float(self.zone_state.get("Umd", 0)) / 10.0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # print(self._attr_unique_id)
        # print(self.coordinator.data)
        self.zone_state = self.coordinator.data[self.device_id]
        # print("Zone: ", self.zone_state["Name"])
        # print("Updated zone state:", self.zone_state)

        self.update_attrs_from_state()
        # self.state = self.coordinator.data[self.zone["ZoneId"]]
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        # Implement setting temperature here
        return

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        # Implement setting HVAC mode here
        self._attr_hvac_mode = hvac_mode  # We actually need to this through APIs
        await self.coordinator.async_request_refresh()
        # self.async_write_ha_state()
