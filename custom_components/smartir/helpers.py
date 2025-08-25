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

async def _async_fetch_esphome_services(
    hass: HomeAssistant, entity_id: str
) -> list[str]:
    """
    Return a list of *service suffixes* that belong to the given ESPHome entity.

    Home Assistant registers ESPHome services under the domain ``esphome`` with the
    name ``<entity_id>.<service>`` (e.g. ``esphome.my_ac.toggle``).  This helper
    extracts the `<service>` part so we can show a nice user‑friendly list.
    """
    # All services that ESPHome registered
    all_services: dict = await hass.services.async_get_registered_services()
    esphome_services: dict = all_services.get("esphome", {})

    # Build a list of ``<entity_id>.<service>`` that belong to the entity
    matching: list[str] = []
    prefix = f"{entity_id}."
    for full_name in esphome_services:
        if full_name.startswith(prefix):
            # ``full_name`` is e.g. "my_ac.toggle" -> we keep only the part after the dot
            matching.append(full_name.split(".", 1)[1])

    # If nothing matches we still return an empty list – the UI will show an error.
    return matching
