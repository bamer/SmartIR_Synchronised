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
            data_schema=vol.Schema({
                vol.Required("device_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["climate", "fan", "media_player", "light"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="device_type"
                    )
                )
            }),
        )

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
                    data_schema=vol.Schema({
                        vol.Required("controller"): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=["broadlink", "xiaomi", "lookin", "esphome", "mqtt"],
                                mode=selector.SelectSelectorMode.DROPDOWN,
                                translation_key="controller"
                            )
                        )
                    }),
                    errors={"controller": "Controller selection required"}
                )
            
            return await self.async_step_device_config()

        _LOGGER.debug("Showing controller selection form")
        return self.async_show_form(
            step_id="controller", 
            data_schema=vol.Schema({
                vol.Required("controller"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["broadlink", "xiaomi", "lookin", "esphome", "mqtt"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="controller"
                    )
                )
            }),
        )

    async def async_step_device_config(self, user_input=None):
        """Handle the device configuration step."""
        _LOGGER.debug("=== SmartIR Config Flow - Step Device Config ===")
        errors = {}
        
        if user_input is not None:
            _LOGGER.debug(f"Device config input received: {user_input}")
            
            try:
                # Validate device_code
                device_code = user_input.get("device_code")
                if device_code is None:
                    errors["device_code"] = "device_code_required"
                elif device_code <= 0:
                    errors["device_code"] = "positive_number_required"
                
                if not errors:
                    # Create final configuration
                    device_name = user_input.get("name", f"SmartIR {DEVICE_TYPES[self.device_type]}")
                    controller_name = CONTROLLER_TYPES[self.controller_type]
                    
                    _LOGGER.debug(f"Creating entry with device_name: {device_name}, controller_name: {controller_name}")
                    
                    # Test avec différentes combinaisons de données
                    data = {
                        "device_type": self.device_type,
                        "controller": self.controller_type,
                        "name": device_name,
                        "device_code": device_code,
                        "controller_data": user_input["controller_data"],
                    }
                    
                    _LOGGER.debug(f"Entry data being created: {data}")
                    
                    # Add optional fields if provided
                    if user_input.get("delay") is not None:
                        data["delay"] = user_input["delay"]
                        _LOGGER.debug(f"Added delay: {data['delay']}")
                    
                    _LOGGER.debug("About to call async_create_entry...")
                    
                    result = self.async_create_entry(
                        title=f"{device_name} ({controller_name})",
                        data=data,
                    )
                    
                    _LOGGER.debug(f"async_create_entry result: {result}")
                    return result
                    
            except Exception as e:
                _LOGGER.error(f"Exception in device_config step: {e}")
                _LOGGER.error(f"Exception type: {type(e)}")
                import traceback
                _LOGGER.error(f"Traceback: {traceback.format_exc()}")
                errors["base"] = "unknown"

        _LOGGER.debug("Showing device config form")
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


        # Get current configuration
        current_config = self.config_entry.data
        device_type = current_config.get("device_type")
        
        # Build schema based on current configuration and device type
        schema_dict = {
            vol.Optional("device_code", default=current_config.get("device_code", 1)): vol.All(int, vol.Range(min=1)),
            vol.Optional("delay", default=current_config.get("delay", 0.5)): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=10.0)),
        }
        
        # Handle name separately to allow empty values
        if current_config.get("name"):
            schema_dict[vol.Optional("name", default=current_config.get("name"))] = str
        else:
            schema_dict[vol.Optional("name")] = str
        
        if current_config.get("controller_type")=="esphome":
            _LOGGER.warning("Current controller_data is esphome")
            domain = "esphome"
        # Handle controller_data separately to avoid empty string default
        if current_config.get("controller_data"):
            schema_dict[vol.Optional("controller_data", default=current_config.get("controller_data"))] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="remote",
                    multiple=False
                )
            )
        else:

            schema_dict[vol.Optional("controller_data")] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="remote",
                    multiple=False
                )
            )

        # Add device-specific options
        if device_type == "climate":
            # Only add default if entity exists in current config
            temp_sensor_config = {
                "domain": "sensor",
                "device_class": "temperature",
                "multiple": False
            }
            humidity_sensor_config = {
                "domain": "sensor", 
                "device_class": "humidity",
                "multiple": False
            }
            power_sensor_config = {
                "domain": "sensor",
                "device_class": "power",
                "multiple": False
            }
            
            # Build the schema dynamically based on existing values
            if current_config.get("temperature_sensor"):
                schema_dict[vol.Optional("temperature_sensor", default=current_config.get("temperature_sensor"))] = selector.EntitySelector(selector.EntitySelectorConfig(**temp_sensor_config))
            else:
                schema_dict[vol.Optional("temperature_sensor")] = selector.EntitySelector(selector.EntitySelectorConfig(**temp_sensor_config))
                
            if current_config.get("humidity_sensor"):
                schema_dict[vol.Optional("humidity_sensor", default=current_config.get("humidity_sensor"))] = selector.EntitySelector(selector.EntitySelectorConfig(**humidity_sensor_config))
            else:
                schema_dict[vol.Optional("humidity_sensor")] = selector.EntitySelector(selector.EntitySelectorConfig(**humidity_sensor_config))
                
            if current_config.get("power_sensor"):
                schema_dict[vol.Optional("power_sensor", default=current_config.get("power_sensor"))] = selector.EntitySelector(selector.EntitySelectorConfig(**power_sensor_config))
            else:
                schema_dict[vol.Optional("power_sensor")] = selector.EntitySelector(selector.EntitySelectorConfig(**power_sensor_config))
                
            schema_dict[vol.Optional("power_sensor_restore_state", default=current_config.get("power_sensor_restore_state", False))] = bool
            
        elif device_type in ["fan", "light", "media_player"]:
            power_sensor_config = {
                "domain": "sensor",
                "device_class": "power", 
                "multiple": False
            }
            
            if current_config.get("power_sensor"):
                schema_dict[vol.Optional("power_sensor", default=current_config.get("power_sensor"))] = selector.EntitySelector(selector.EntitySelectorConfig(**power_sensor_config))
            else:
                schema_dict[vol.Optional("power_sensor")] = selector.EntitySelector(selector.EntitySelectorConfig(**power_sensor_config))

        device_code_help_url = f"https://github.com/bamer/SmartIR_Synchronised/tree/v0.1-beta/codes/{device_type}"

     

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "device_code_help_url": device_code_help_url
            }
        )