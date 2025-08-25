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

    # ----------------------------------------------------------------------
    #  USER – choose device type
    # ----------------------------------------------------------------------
    async def async_step_user(self, user_input=None):
        """Handle the device type selection step."""
        _LOGGER.debug("=== SmartIR Config Flow - Step User ===")

        if user_input is not None:
            _LOGGER.debug(f"User input received: {user_input}")
            self.device_type = user_input["device_type"]
            _LOGGER.debug(f"Device type selected: {self.device_type}")
            return await self.async_step_controller()

        _LOGGER.debug("Showing device type selection form")
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

    # ----------------------------------------------------------------------
    #  CONTROLLER – choose controller type
    # ----------------------------------------------------------------------
    async def async_step_controller(self, user_input=None):
        """Handle the controller type selection step."""
        _LOGGER.debug("=== SmartIR Config Flow - Step Controller ===")

        if user_input is not None:
            _LOGGER.debug(f"Controller input received: {user_input}")
            self.controller_type = user_input.get("controller")
            _LOGGER.debug(f"Controller type selected: {self.controller_type}")

            if not self.controller_type:
                _LOGGER.error(f"No controller in user_input: {user_input}")
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
                                        "esphome",
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

        _LOGGER.debug("Showing controller selection form")
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
                                "esphome",
                                "mqtt",
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="controller",
                        )
                    )
                }
            ),
        )

    # ----------------------------------------------------------------------
    #  DEVICE CONFIG – final step (the only part we modify)
    # ----------------------------------------------------------------------
    async def async_step_device_config(self, user_input=None):
        """Handle the device configuration step."""
        _LOGGER.debug("=== SmartIR Config Flow - Step Device Config ===")
        errors = {}

        if user_input is not None:
            _LOGGER.debug(f"Device config input received: {user_input}")

            try:
                # ------------------------------------------------------------------
                #  Validate required fields
                # ------------------------------------------------------------------
                device_code = user_input.get("device_code")
                if device_code is None:
                    errors["device_code"] = "device_code_required"
                elif device_code <= 0:
                    errors["device_code"] = "positive_number_required"

                if not errors:
                    # --------------------------------------------------------------
                    #  Build the entry data
                    # --------------------------------------------------------------
                    device_name = user_input.get(
                        "name", f"SmartIR {DEVICE_TYPES[self.device_type]}"
                    )
                    controller_name = CONTROLLER_TYPES[self.controller_type]

                    _LOGGER.debug(
                        f"Creating entry with device_name: {device_name}, "
                        f"controller_name: {controller_name}"
                    )

                    data = {
                        "device_type": self.device_type,
                        "controller": self.controller_type,
                        "name": device_name,
                        "device_code": device_code,
                        "controller_data": user_input["controller_data"],
                    }

                    _LOGGER.debug(f"Entry data being created: {data}")

                    # Optional delay
                    if user_input.get("delay") is not None:
                        data["delay"] = user_input["delay"]
                        _LOGGER.debug(f"Added delay: {data['delay']}")

                    _LOGGER.debug("About to call async_create_entry...")

                    return self.async_create_entry(
                        title=f"{device_name} ({controller_name})", data=data
                    )

            except Exception as e:  # pragma: no cover – defensive logging
                _LOGGER.error(f"Exception in device_config step: {e}")
                _LOGGER.error(f"Exception type: {type(e)}")
                import traceback

                _LOGGER.error(f"Traceback: {traceback.format_exc()}")
                errors["base"] = "unknown"

        # ----------------------------------------------------------------------
        #  Build the schema – *** NEW LOGIC FOR controller_data***
        # ----------------------------------------------------------------------
        _LOGGER.debug("Showing device config form")
        # Base fields that are always present
        schema_dict = {
            vol.Optional("name"): str,
            vol.Required("device_code"): vol.All(int, vol.Range(min=1)),
            vol.Required("controller_data"): self._selector_for_controller_data(),
            vol.Optional(
                "delay", default=0.5
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=10.0)),
        }

        # --------------------------------------------------------------
        #  Device‑specific optional sensors / settings
        # --------------------------------------------------------------
        if self.device_type == "climate":
            schema_dict.update(
                {
                    vol.Optional("temperature_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="temperature", multiple=False
                        )
                    ),
                    vol.Optional("humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="humidity", multiple=False
                        )
                    ),
                    vol.Optional("power_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="power", multiple=False
                        )
                    ),
                    vol.Optional(
                        "power_sensor_restore_state", default=False
                    ): bool,
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

        # --------------------------------------------------------------
        #  Help link for the device‑code list
        # --------------------------------------------------------------
        device_code_help_url = (
            f"https://github.com/smartHomeHub/SmartIR/tree/master/codes/{self.device_type}"
        )

        return self.async_show_form(
            step_id="device_config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"device_code_help_url": device_code_help_url},
        )

    # ----------------------------------------------------------------------
    #  Helper – choose the correct selector for “controller_data”
    # ----------------------------------------------------------------------
    def _selector_for_controller_data(self):
        """
        Return the appropriate selector object for the *controller_data* field
        based on the previously chosen controller type.

        * **esphome** → ``ServiceSelector`` (domain ``esphome``) – the UI will
          let the user pick an ESPHome service/action.
        * every other controller → ``EntitySelector`` limited to the
          ``remote`` domain (the original behaviour).
        """
        if self.controller_type == "esphome":
            # ESPHome exposes its calls as services under the “esphome” domain.
            # A ServiceSelector makes the user pick one of those services.
            return selector.ServiceSelector(
                selector.ServiceSelectorConfig(domain="esphome")
            )
        # Default – remote entity selector (Broadlink, Xiaomi, etc.)
        return selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote", multiple=False)
        )


# ----------------------------------------------------------------------
#  OPTIONS FLOW – only tiny tweak so the same selector is used when
#  editing an entry (keeps UI consistent)
# ----------------------------------------------------------------------
class SmartIROptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for SmartIR."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.device_type = config_entry.data.get("device_type")

    async def async_step_init(self, user_input=None):
        """Manage the SmartIR options."""
        if user_input is not None:
            # Update the config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Current configuration – used as defaults
        current_config = self.config_entry.data

        # --------------------------------------------------------------
        #  Base fields
        # --------------------------------------------------------------
        schema_dict = {
            vol.Optional(
                "device_code", default=current_config.get("device_code", 1)
            ): vol.All(int, vol.Range(min=1)),
            vol.Optional(
                "delay", default=current_config.get("delay", 0.5)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=10.0)),
        }

        # --------------------------------------------------------------
        #  Optional name
        # --------------------------------------------------------------
        if current_config.get("name"):
            schema_dict[
                vol.Optional("name", default=current_config.get("name"))
            ] = str
        else:
            schema_dict[vol.Optional("name")] = str

        # --------------------------------------------------------------
        #  controller_data – same selector logic as the config flow
        # --------------------------------------------------------------
        controller_type = current_config.get("controller")
        if controller_type == "esphome":
            schema_dict[
                vol.Optional(
                    "controller_data",
                    default=current_config.get("controller_data"),
                )
            ] = selector.ServiceSelector(
                selector.ServiceSelectorConfig(domain="esphome")
            )
        else:
            schema_dict[
                vol.Optional(
                    "controller_data",
                    default=current_config.get("controller_data"),
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="remote", multiple=False)
            )

        # --------------------------------------------------------------
        #  Device‑specific optional entities
        # --------------------------------------------------------------
        if self.device_type == "climate":
            # Temperature sensor
            if current_config.get("temperature_sensor"):
                schema_dict[
                    vol.Optional(
                        "temperature_sensor",
                        default=current_config.get("temperature_sensor"),
                    )
                ] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature", multiple=False
                    )
                )
            else:
                schema_dict[vol.Optional("temperature_sensor")] = selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature", multiple=False
                    )
                )
            # Humidity sensor
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
            # Power sensor
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
            # Power‑sensor‑restore‑state flag
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

        # --------------------------------------------------------------
        #  Help URL (same as in the original flow)
        # --------------------------------------------------------------
        device_code_help_url = (
            f"https://github.com/bamer/SmartIR_Synchronised/tree/v0.1-beta/codes/{self.device_type}"
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={"device_code_help_url": device_code_help_url},
        )
