"""Config flow for SmartIR integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN, 
    CONTROLLER_TYPES, 
    DEVICE_TYPES
)

_LOGGER = logging.getLogger(__name__)


class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartIR."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.device_type = None
        self.controller_type = None

    async def async_step_user(self, user_input=None):
        """Handle the device type selection step."""
        _LOGGER.warning("=== SmartIR Config Flow - Step User ===")
        
        if self._async_current_entries():
            _LOGGER.warning("Single instance already exists, aborting")
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            _LOGGER.warning(f"User input received: {user_input}")
            self.device_type = user_input["device_type"]
            _LOGGER.warning(f"Device type selected: {self.device_type}")
            return await self.async_step_controller()

        _LOGGER.warning("Showing device type selection form")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("device_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            "climate",
                            "fan", 
                            "media_player",
                            "light"
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="device_type"
                    )
                )
            }),
        )

    async def async_step_controller(self, user_input=None):
        """Handle the controller type selection step."""
        _LOGGER.warning("=== SmartIR Config Flow - Step Controller ===")
        
        if user_input is not None:
            _LOGGER.warning(f"Controller input received: {user_input}")
            self.controller_type = user_input.get("controller")
            _LOGGER.warning(f"Controller type selected: {self.controller_type}")
            
            if not self.controller_type:
                _LOGGER.error(f"No controller in user_input: {user_input}")
                return self.async_show_form(
                    step_id="controller",
                    data_schema=vol.Schema({
                        vol.Required("controller"): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    "broadlink",
                                    "xiaomi", 
                                    "lookin",
                                    "esphome",
                                    "mqtt"
                                ],
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                translation_key="controller"
                            )
                        )
                    }),
                    errors={"controller": "Controller selection required"}
                )
            
            return await self.async_step_device_config()

        _LOGGER.warning("Showing controller selection form")
        return self.async_show_form(
            step_id="controller", 
            data_schema=vol.Schema({
                vol.Required("controller"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            "broadlink",
                            "xiaomi", 
                            "lookin",
                            "esphome",
                            "mqtt"
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="controller"
                    )
                )
            }),
        )

    async def async_step_device_config(self, user_input=None):
        """Handle the device configuration step."""
        _LOGGER.warning("=== SmartIR Config Flow - Step Device Config ===")
        errors = {}
        
        if user_input is not None:
            _LOGGER.warning(f"Device config input received: {user_input}")
            
            try:
                # Validate device_code
                device_code = user_input.get("device_code")
                if device_code is not None and device_code <= 0:
                    errors["device_code"] = "positive_number_required"
                
                if not errors:
                    # Create final configuration
                    device_name = user_input.get("name", f"SmartIR {DEVICE_TYPES[self.device_type]}")
                    controller_name = CONTROLLER_TYPES[self.controller_type]
                    
                    _LOGGER.warning(f"Creating entry with device_name: {device_name}, controller_name: {controller_name}")
                    
                    # Test avec différentes combinaisons de données
                    data = {
                        "device_type": self.device_type,
                        "controller": self.controller_type,
                        "name": device_name,
                        "device_code": device_code,
                        "controller_data": user_input["controller_data"],
                    }
                    
                    _LOGGER.warning(f"Entry data being created: {data}")
                    
                    # Add optional fields if provided
                    if user_input.get("delay") is not None:
                        data["delay"] = user_input["delay"]
                        _LOGGER.warning(f"Added delay: {data['delay']}")
                    
                    _LOGGER.warning("About to call async_create_entry...")
                    
                    result = self.async_create_entry(
                        title=f"{device_name} ({controller_name})",
                        data=data,
                    )
                    
                    _LOGGER.warning(f"async_create_entry result: {result}")
                    return result
                    
            except Exception as e:
                _LOGGER.error(f"Exception in device_config step: {e}")
                _LOGGER.error(f"Exception type: {type(e)}")
                import traceback
                _LOGGER.error(f"Traceback: {traceback.format_exc()}")
                errors["base"] = "unknown"

        _LOGGER.warning("Showing device config form")
        # Build schema based on device type
        schema_dict = {
            vol.Optional("name"): str,
            vol.Required("device_code"): vol.All(int, vol.Range(min=1)),
            vol.Required("controller_data"): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="remote",
                    multiple=False
                )
            ),
            vol.Optional("delay", default=0.5): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=10.0)),
        }

        # Add device-specific sensors
        if self.device_type == "climate":
            schema_dict.update({
                vol.Optional("temperature_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="temperature",
                        multiple=False
                    )
                ),
                vol.Optional("humidity_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", 
                        device_class="humidity",
                        multiple=False
                    )
                ),
                vol.Optional("power_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="power",
                        multiple=False
                    )
                ),
                vol.Optional("power_sensor_restore_state", default=False): bool,
            })
        elif self.device_type in ["fan", "light", "media_player"]:
            schema_dict.update({
                vol.Optional("power_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class="power", 
                        multiple=False
                    )
                ),
            })

        # Generate help URL based on device type
        device_code_help_url = f"https://github.com/smartHomeHub/SmartIR/tree/master/codes/{self.device_type}"

        return self.async_show_form(
            step_id="device_config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={
                "device_code_help_url": device_code_help_url
            }
        )