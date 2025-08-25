"""Helper functions for SmartIR."""

import hashlib
from .const import DOMAIN, CONF_CONTROLLER_TYPE, CONTROLLER_TYPES
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

async def async_setup_entry_platform(
    hass, entry, async_add_entities, platform_setup_fn
):
    """Set up SmartIR platform from a config entry."""
    config = hass.data[DOMAIN][entry.entry_id].copy()

    # Generate unique_id if not provided
    if not config.get("unique_id"):
        device_code = config.get("device_code", "unknown")
        controller_data = config.get("controller_data", "unknown")
        device_type = config.get("device_type", "unknown")

        # Create a unique identifier based on device_code, controller_data, and device_type
        unique_string = f"smartir_{device_type}_{device_code}_{controller_data}"
        unique_id = hashlib.md5(unique_string.encode()).hexdigest()[:16]
        config["unique_id"] = f"smartir_{unique_id}"

    await platform_setup_fn(hass, config, async_add_entities)

