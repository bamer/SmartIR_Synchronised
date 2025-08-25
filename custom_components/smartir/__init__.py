"""SmartIR integration entry point."""
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "smartir"
ALLOWED_PLATFORMS = {"climate"}  # <= doit correspondre au manifest


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    _LOGGER.warning(
        "The SmartIR integration is now config-entry based. "
        "Please remove any 'platform: smartir' entries from configuration.yaml."
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    platform = entry.data.get("platform", "climate")
    if platform not in ALLOWED_PLATFORMS:
        _LOGGER.error(
            "Unsupported platform '%s' for %s. Allowed: %s",
            platform, DOMAIN, ", ".join(sorted(ALLOWED_PLATFORMS))
        )
        return False

    _LOGGER.warning("Setting up %s entry %s for platform %s", DOMAIN, entry.title, platform)
    await hass.config_entries.async_forward_entry_setups(entry, [platform])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    platform = entry.data.get("platform", "climate")
    if platform not in ALLOWED_PLATFORMS:
        return True
    _LOGGER.warning("Unloading %s entry %s for platform %s", DOMAIN, entry.title, platform)
    return await hass.config_entries.async_unload_platforms(entry, [platform])
