"""The Tecnosystemi integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import TecnosystemiAPI

_PLATFORMS: list[Platform] = [Platform.CLIMATE]

type TecnosystemiConfigEntry = ConfigEntry[TecnosystemiAPI]


async def async_setup_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Set up Tecnosystemi from a config entry."""

    device_id = entry.data["device_id"]

    entry.runtime_data = TecnosystemiAPI(
        username=entry.data["username"],
        password=entry.data["password"],
        device_id=device_id,
    )

    try:
        await entry.runtime_data.login()
    except RuntimeError:
        raise ConfigEntryNotReady(
            "Tecnosystemi API is not ready. Please check your configuration."
        ) from None

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
