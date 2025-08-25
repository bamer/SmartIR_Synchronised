"""SmartIR integration – core entry point."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import (
    entity_platform,
    device_registry,
    entity_registry,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1️⃣  async_setup – called once when HA starts (we only need to register the
#     integration for the UI, nothing else)
# ---------------------------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: Mapping[str, Any]) -> bool:
    """Set up the integration from configuration.yaml (kept for backward‑compatibility)."""
    # If a user still has a `smartir:` block in configuration.yaml we can
    # lazily create a ConfigEntry for it – this makes the migration painless.
    if config.get(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=config[DOMAIN],
            )
        )
    return True


# ---------------------------------------------------------------------------
# 2️⃣  async_setup_entry – called for each ConfigEntry (UI or imported)
# ---------------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartIR from a config entry."""
    # Store the entry’s data into hass.data so we can reuse it in the platform
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the entry to the climate platform (you could also forward to fan,
    # light, etc. if you add them later)
    await hass.config_entries.async_forward_entry_setup(entry, "climate")

    # OPTIONAL – register services that were previously available via
    # `async_reload_service_handler` or any other custom services.
    # Example:
    #   async def async_reload(call: ServiceCall) -> None: …
    #   hass.services.async_register(DOMAIN, "reload", async_reload)

    return True


# ---------------------------------------------------------------------------
# 3️⃣  async_unload_entry – clean‑up when the entry is removed
# ---------------------------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "climate")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
