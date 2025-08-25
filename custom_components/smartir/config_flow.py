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

<<<<<<< HEAD
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
=======
        return self.async_show_form(
            step_id="controller",
            data_schema=vol.Schema(
                {
                    vol.Required("controller"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                "broadlink",
                                "xiaomi",
                                "lookin",
                                "ESPHome",
                                "mqtt",
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="controller",
                        )
                    )
                }
            ),
        )

    # ------------------------------------------------------------------
    #  CONFIG FLOW – Étape de sélection d’encoding
    # ------------------------------------------------------------------
    async def async_step_commands_encoding(self, user_input=None):
        """Ask the user to select the encoding type."""
        _LOGGER.warning("=== SmartIR Config Flow - Step Commands Encoding ===")
        errors = {}

        if user_input is not None:
            chosen_encoding = user_input.get("commands_encoding")

            # Validation : est-ce un encodage connu ?
            if chosen_encoding not in CONTROLLER_SUPPORT[str(self.controller_type)]:
                errors["commands_encoding"] = "unsupported"

            if not errors:
                # On a terminé la configuration – on crée l’entrée
                self._commands_encoding = (
                    user_input  # ajout de l’encoding dans le dict final
                )
                return self.async_create_entry(title="", data=self.encodingType)

        # Formulaire d’encodage (selon HA 2024+ vous pouvez utiliser un selector)
        data_schema = vol.Schema(
            {
                vol.Required("commands_encoding"): vol.In(
                    CONTROLLER_SUPPORT[str(self.controller_type)]
                )
            }
        )

        return self.async_show_form(
            step_id="commands_encoding", data_schema=data_schema, errors=errors
        )

    # ------------------------------------------------------------------
    #  DEVICE CONFIG – final step
    # ------------------------------------------------------------------
    async def async_step_device_config(self, user_input=None):
        """Handle the device configuration step."""
        _LOGGER.debug("=== SmartIR Config Flow - Step Device Config ===")
        errors = {}

        if user_input is not None:
            # --------------------------------------------------------------
            #  Validate the required fields
            # --------------------------------------------------------------
            device_code = user_input.get("device_code")
            if device_code is None:
                errors["device_code"] = "device_code_required"
            elif device_code <= 0:
                errors["device_code"] = "positive_number_required"

            if not errors:
                device_name = user_input.get(
                    "name", f"SmartIR {self.device_type} {self.controller_type}"
                )
                controller_name = CONTROLLER_SUPPORT[str(self.controller_type)]

                data = {
                    "device_type": self.device_type,
                    "controller": self.controller_type,
                    "name": device_name,
                    "device_code": device_code,
                    "controller_data": user_input["controller_data"],
                }

                if user_input.get("delay") is not None:
                    data["delay"] = user_input["delay"]

                return self.async_create_entry(
                    title=f"{device_name} ({controller_name})", data=data
                )

        # --------------------------------------------------------------
        #  Build the schema – **new selector logic**
        # --------------------------------------------------------------
        schema_dict = {
            vol.Optional("name"): str,
            vol.Required("device_code"): vol.All(int, vol.Range(min=1)),
            # <-- the selector now adapts to the chosen controller type
            vol.Required("controller_data"): self._selector_for_controller_data(),
            vol.Required("commands_encoding"): self.async_step_commands_encoding(),
            vol.Optional("delay", default=0.5): vol.All(
                vol.Coerce(float), vol.Range(min=0.1, max=10.0)
            ),
        }

        # --------------------------------------------------------------
        #  Device‑specific optional entities / sensors
        # --------------------------------------------------------------
        if self.device_type == "climate":
            schema_dict.update(
                {
                    vol.Optional("temperature_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="temperature",
                            multiple=False,
                        )
                    ),
                    vol.Optional("humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            device_class="humidity",
                            multiple=False,
                        )
                    ),
                    vol.Optional("power_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="power", multiple=False
                        )
                    ),
                    vol.Optional("power_sensor_restore_state", default=False): bool,
                }
            )
        elif self.device_type in ["fan", "light", "media_player"]:
            schema_dict.update(
                {
                    vol.Optional("power_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="power", multiple=False
                        )
                    ),
                }
            )

        device_code_help_url = f"https://github.com/smartHomeHub/SmartIR/tree/master/codes/{self.device_type}"

        return self.async_show_form(
            step_id="device_config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"device_code_help_url": device_code_help_url},
>>>>>>> 4a9ce58254801c98da77fa97da1947fe15f31ffa
        )

        return self.async_show_form(step_id="optional", data_schema=schema)

    async def async_step_import(self, import_info: dict) -> config_entries.FlowResult:
        """
        Called when a YAML entry is imported.
        We simply convert it to a config‑entry so the UI stays consistent.
        """
<<<<<<< HEAD
        _LOGGER.debug("Climate ConfigFlow: async_step_import called")
        _debug_log("Importing data", import_info)

        # The import dict contains exactly what we would have gotten from the user
        self._user_input = import_info

        return await self.async_create_entry(
            title=import_info.get(CONF_NAME, "SmartIR Climate"),
            data=import_info,
=======
        if self.controller_type == "ESPHome":
            # Free‑form text – the ESPHome service name.
            # return selector.TextSelector()
            return selector.EntitySelectorConfig(domain="esphome", multiple=False)
        # Default – pick a remote entity.
        return selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote", multiple=False)
>>>>>>> 4a9ce58254801c98da77fa97da1947fe15f31ffa
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
