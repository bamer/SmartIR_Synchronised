"""Config flow for SmartIR integration - Simplified version."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartIR."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Create the config entry with minimal data
            return self.async_create_entry(
                title="SmartIR Device",
                data={
                    "platform": "climate",  # Use 'platform' instead of device_type
                    "controller": "broadlink",  # Use 'controller' instead of controller_type
                    "name": "Test Device",
                    "device_code": 1000,
                    "controller_data": "remote.broadlink"
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("test"): str
            }),
        )