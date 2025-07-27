"""The Tecnosystemi integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import TecnoSystemiAPI

_PLATFORMS: list[Platform] = [Platform.CLIMATE]

type TecnosystemiConfigEntry = ConfigEntry[TecnoSystemiAPI]


async def async_setup_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Set up Tecnosystemi from a config entry."""

    # entry.data contains username and password
    # device_id = hashlib.sha256(entry.entry_id.encode()).hexdigest()[:16]
    device_id = entry.data["device_id"]
    # print("Obtained unique device ID:", entry.data["device_id"])

    entry.runtime_data = TecnoSystemiAPI(
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
