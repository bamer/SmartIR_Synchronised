# ---------------------------  config_flow.py  ---------------------------
"""Config flow for SmartIR integration."""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONTROLLER_TYPES, DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartIR."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SmartIROptionsFlow(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self.device_type = None
        self.controller_type = None

    # ------------------------------------------------------------------
    #  USER – choose device type
    # ------------------------------------------------------------------
    async def async_step_user(self, user_input=None):
        _LOGGER.debug("=== SmartIR Config Flow - Step User ===")
        if user_input is not None:
            self.device_type = user_input["device_type"]
            return await self.async_step_controller()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("device_type"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["climate", "fan", "media_player", "light"],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="device_type",
                        )
                    )
                }
            ),
        )


    # ------------------------------------------------------------------
    #  CONTROLLER – choose controller type
    # ------------------------------------------------------------------
    async def async_step_controller(self, user_input=None):
        _LOGGER.debug("=== SmartIR Config Flow - Step Controller ===")
        if user_input is not None:
            self.controller_type = user_input.get("controller")
            if not self.controller_type:
                _LOGGER.error("No controller in user_input")
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
                    errors={"controller": "Controller selection required"},
                )
            return await self.async_step_device_config()

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
                    "name", f"SmartIR {DEVICE_TYPES[self.device_type]}"
                )
                controller_name = CONTROLLER_TYPES[self.controller_type]

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
        )

    # ----------------------------------------------------------------------
    #  Helper – return the proper selector for “controller_data”
    # ----------------------------------------------------------------------
    def _selector_for_controller_data(self):
        """
        Return a selector that matches the expected ``controller_data`` type.

        * **ESPHome** → ``TextSelector`` (you type the ESPHome service name,
          e.g. ``my_device_send_ir``).
        * all other controllers → ``EntitySelector`` limited to the ``remote``
          domain (the original behaviour).
        """
        if self.controller_type == "ESPHome":
            # Free‑form text – the ESPHome service name.
            return selector.TextSelector()
        # Default – pick a remote entity.
        return selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote", multiple=False)
        )


# ----------------------------------------------------------------------
#  OPTIONS FLOW – keep the UI consistent when editing an entry
# ----------------------------------------------------------------------
class SmartIROptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SmartIR."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.device_type = config_entry.data.get("device_type")

    async def async_step_init(self, user_input=None):
        """Manage the SmartIR options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_config = self.config_entry.data
        schema_dict = {
            vol.Optional(
                "device_code", default=current_config.get("device_code", 1)
            ): vol.All(int, vol.Range(min=1)),
            vol.Optional("delay", default=current_config.get("delay", 0.5)): vol.All(
                vol.Coerce(float), vol.Range(min=0.1, max=10.0)
            ),
        }

        # Optional name
        if current_config.get("name"):
            schema_dict[vol.Optional("name", default=current_config.get("name"))] = str
        else:
            schema_dict[vol.Optional("name")] = str

        # ---------- controller_data selector ----------
        controller_type = current_config.get("controller")
        if controller_type == "ESPHome":
            selector_obj = selector.TextSelector()
        else:
            selector_obj = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="remote", multiple=False)
            )
        schema_dict[
            vol.Optional(
                "controller_data",
                default=current_config.get("controller_data"),
            )
        ] = selector_obj

        # ---------- device‑specific options ----------
        if self.device_type == "climate":
            # temperature sensor
            if current_config.get("temperature_sensor"):
                schema_dict[
                    vol.Optional(
                        "temperature_sensor",
                        default=current_config.get("temperature_sensor"),
                    )
                ] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature",
                        multiple=False,
                    )
                )
            else:
                schema_dict[vol.Optional("temperature_sensor")] = (
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="temperature", multiple=False
                        )
                    )
                )
            # humidity sensor
            if current_config.get("humidity_sensor"):
                schema_dict[
                    vol.Optional(
                        "humidity_sensor",
                        default=current_config.get("humidity_sensor"),
                    )
                ] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity", multiple=False
                    )
                )
            else:
                schema_dict[vol.Optional("humidity_sensor")] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity", multiple=False
                    )
                )
            # power sensor
            if current_config.get("power_sensor"):
                schema_dict[
                    vol.Optional(
                        "power_sensor",
                        default=current_config.get("power_sensor"),
                    )
                ] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="power", multiple=False
                    )
                )
            else:
                schema_dict[vol.Optional("power_sensor")] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="power", multiple=False
                    )
                )
            schema_dict[
                vol.Optional(
                    "power_sensor_restore_state",
                    default=current_config.get("power_sensor_restore_state", False),
                )
            ] = bool

        elif self.device_type in ["fan", "light", "media_player"]:
            if current_config.get("power_sensor"):
                schema_dict[
                    vol.Optional(
                        "power_sensor",
                        default=current_config.get("power_sensor"),
                    )
                ] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="power", multiple=False
                    )
                )
            else:
                schema_dict[vol.Optional("power_sensor")] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="power", multiple=False
                    )
                )

        device_code_help_url = f"https://github.com/bamer/SmartIR_Synchronised/tree/v0.1-beta/codes/{self.device_type}"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={"device_code_help_url": device_code_help_url},
        )
