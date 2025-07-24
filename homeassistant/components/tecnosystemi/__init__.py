"""The Tecnosystemi integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

_PLATFORMS: list[Platform] = [Platform.CLIMATE]

type TecnosystemiConfigEntry = ConfigEntry[str]


async def async_setup_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Set up Tecnosystemi from a config entry."""

    # entry.runtime_data = MyAPI(...)
    entry.runtime_data = "xxx"  # Should have the api here, I guess?

    # See https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/test-before-setup/
    raise ConfigEntryNotReady(
        "Tecnosystemi API is not ready. Please check your configuration."
    )

    # await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    #

    # return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
