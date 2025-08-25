# custom_components/smartir/config_flow.py
from homeassistant.helpers import selector          # <-- NEW IMPORT
"""UI flow for the SmartIR integration."""
from __future__ import annotations

import logging
import voluptuous as vol


from homeassistant import config_entries, core
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector, config_validation as cv
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID, CONF_DEVICE_CODE, CONF_CONTROLLER_DATA

# Import the helper that loads device data from your yaml files.
# This keeps the same logic you already use in `smartir_entity.py`.
from .smartir_entity import load_device_data_file

_LOGGER = logging.getLogger(__name__)
# custom_components/smartir/config_flow.py



# ----------------------------------------------------------------------
# 1️⃣  Common helpers
# ----------------------------------------------------------------------
def _debug_log(title: str, payload: dict) -> None:
    """Convenience wrapper that logs the whole step in one line."""
    _LOGGER.debug("%s: %s", title, payload)

# ----------------------------------------------------------------------
# 2️⃣  Platform specific ConfigFlow classes
# ----------------------------------------------------------------------
class SmartIRClimateConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for the Climate platform."""

    # Tell HA that this flow is for the *smartir* domain.
    DOMAIN = "smartir"

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict | None = None
    async def _async_get_esphome_services(self) -> list[str]:
        """
        Retourne la liste triée des noms de services disponibles sous le domaine
        'esphome'.  Si aucun service n’est trouvé, une liste vide est renvoyée.
        """
        try:
            all_services = await self.hass.services.async_services()
            esphome_services = sorted(all_services.get("esphome", {}).keys())
            _LOGGER.debug(
                "ESPHome services détectés : %s",
                esphome_services,
            )
            return esphome_services
        except Exception as exc:
            # On ne bloque pas la configuration si l’appel échoue.
            _LOGGER.warning("Impossible de récupérer les services ESPHome : %s", exc)
            return []

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Step 0 – ask for mandatory fields."""
        _LOGGER.debug("Climate ConfigFlow: async_step_user called")
        if user_input is not None:
            # We have the values that the user entered.
            _debug_log("Received user input", user_input)

            # Validate and store temporarily
            self._user_input = user_input

            # Move to the optional‑sensor step
            return await self.async_step_optional()

        # No data yet – show the form
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR Climate"): cv.string,
                vol.Required(CONF_UNIQUE_ID): cv.string,
                vol.Required(CONF_DEVICE_CODE): cv.positive_int,
                vol.Required("controller_type", default="ESPHome"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["ESPHome", "Other"])
                ),
                vol.Required("esphome_service"): selector.TextSelector(),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={"example": "master_bedroom_ac_smart_ir"},
        )

    async def async_step_optional(self) -> config_entries.FlowResult:
        """Step 1 – ask for optional sensors."""
        _LOGGER.debug("Climate ConfigFlow: async_step_optional called")
        if self._user_input is None:
            return await self.async_abort(reason="missing_user_input")

        schema = vol.Schema(
            {
                vol.Optional("temperature_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", multiple=False)
                ),
                vol.Optional("humidity_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", multiple=False)
                ),
                vol.Optional("power_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=False)
                ),
            }
        )

        return self.async_show_form(step_id="optional", data_schema=schema)

    async def async_step_import(self, import_info: dict) -> config_entries.FlowResult:
        """
        Called when a YAML entry is imported.
        We simply convert it to a config‑entry so the UI stays consistent.
        """
        _LOGGER.debug("Climate ConfigFlow: async_step_import called")
        _debug_log("Importing data", import_info)

        # The import dict contains exactly what we would have gotten from the user
        self._user_input = import_info

        return await self.async_create_entry(
            title=import_info.get(CONF_NAME, "SmartIR Climate"),
            data=import_info,
        )

    async def async_create_entry(self, title: str, data: dict) -> config_entries.FlowResult:
        """Create the final entry."""
        _LOGGER.debug("Climate ConfigFlow: creating entry %s", title)

        # Optional step – we don't need to do anything special here.
        return super().async_create_entry(title=title, data=data)


# ----------------------------------------------------------------------
# 3️⃣  The same pattern for Fan / Light / Media Player
# ----------------------------------------------------------------------
class SmartIRFanConfigFlow(config_entries.ConfigFlow):
    """Config flow for the Fan platform."""
    DOMAIN = "smartir"
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Fan ConfigFlow: async_step_user called")
        if user_input:
            self._user_input = user_input
            return await self.async_create_entry(
                title=user_input.get(CONF_NAME, "SmartIR Fan"),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR Fan"): cv.string,
                vol.Required(CONF_UNIQUE_ID): cv.string,
                vol.Required(CONF_DEVICE_CODE): cv.positive_int,
                vol.Required("controller_type", default="ESPHome"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["ESPHome", "Other"])
                ),
                vol.Required("esphome_service"): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, import_info: dict):
        _LOGGER.debug("Fan ConfigFlow: async_step_import called")
        return await self.async_create_entry(
            title=import_info.get(CONF_NAME, "SmartIR Fan"),
            data=import_info,
        )


# Light
class SmartIRLightConfigFlow(config_entries.ConfigFlow):
    DOMAIN = "smartir"
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Light ConfigFlow: async_step_user called")
        if user_input:
            return await self.async_create_entry(
                title=user_input.get(CONF_NAME, "SmartIR Light"),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR Light"): cv.string,
                vol.Required(CONF_UNIQUE_ID): cv.string,
                vol.Required(CONF_DEVICE_CODE): cv.positive_int,
                vol.Required("controller_type", default="ESPHome"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["ESPHome", "Other"])
                ),
                vol.Required("esphome_service"): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, import_info: dict):
        _LOGGER.debug("Light ConfigFlow: async_step_import called")
        return await self.async_create_entry(
            title=import_info.get(CONF_NAME, "SmartIR Light"),
            data=import_info,
        )


# Media Player
class SmartIRMediaPlayerConfigFlow(config_entries.ConfigFlow):
    DOMAIN = "smartir"
    VERSION = 1

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("MediaPlayer ConfigFlow: async_step_user called")
        if user_input:
            return await self.async_create_entry(
                title=user_input.get(CONF_NAME, "SmartIR Media Player"),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR Media Player"): cv.string,
                vol.Required(CONF_UNIQUE_ID): cv.string,
                vol.Required(CONF_DEVICE_CODE): cv.positive_int,
                vol.Required("controller_type", default="ESPHome"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["ESPHome", "Other"])
                ),
                vol.Required("esphome_service"): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_import(self, import_info: dict):
        _LOGGER.debug("MediaPlayer ConfigFlow: async_step_import called")
        return await self.async_create_entry(
            title=import_info.get(CONF_NAME, "SmartIR Media Player"),
            data=import_info,
        )
