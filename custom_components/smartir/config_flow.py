"""Config flow for SmartIR."""

from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
)

_LOGGER = logging.getLogger(__name__)


class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartIR."""

    VERSION = 1
    # If you ever need migration you would bump VERSION and implement async_migrate_

    # -----------------------------------------------------------------------
    # STEP 1 – “User” – the form shown when the user clicks “Add Integration”
    # -----------------------------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show the form to the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # ------------------------------------------------------------------
            # 1️⃣ Validate that the JSON device data file exists and looks ok.
            #    (You already have `load_device_data_file()` that does the heavy
            #    validation – reuse it here.)
            # ------------------------------------------------------------------
            try:
                # The helper expects a *config* dict that mimics the old schema.
                # We can just build it from the UI values.
                dummy_cfg = {
                    CONF_NAME: user_input.get(CONF_NAME, "SmartIR Climate"),
                    CONF_TEMPERATURE_SENSOR: user_input.get(CONF_TEMPERATURE_SENSOR),
                    CONF_HUMIDITY_SENSOR: user_input.get(CONF_HUMIDITY_SENSOR),
                    # add any other required keys (controller, encoding, …)
                }

                # `load_device_data_file` is async – it also validates the JSON.
                # We only need to know if it raises or returns None.
                device_data = await self.hass.async_add_executor_job(
                    # we must import it inside the function to avoid circular imports
                    lambda: __import__("smartir.smartir_entity", fromlist=["load_device_data_file"])
                    .load_device_data_file(
                        dummy_cfg,
                        "climate",
                        {"hvac_modes": []},  # minimal extra data – the function uses it
                        self.hass,
                    )
                )
                if not device_data:
                    raise ValueError("Device data validation failed")
            except Exception as exc:  # pragma: no cover – defensive
                _LOGGER.error("Device data validation error: %s", exc)
                errors["base"] = "invalid_device_data"
            else:
                # -------------------------------------------------------------
                # 2️⃣ If everything is fine, create the ConfigEntry
                # -------------------------------------------------------------
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        # -----------------------------------------------------------------------
        # 3️⃣ Show the form – we use Home Assistant selectors so the UI gets
        #    drop‑downs, entity pickers, etc.
        # -----------------------------------------------------------------------
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR Climate"): cv.string,
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional(
                    CONF_HUMIDITY_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
                ),
                # -----------------------------------------------------------------
                #   Add any other required options (controller type, encoding,
                #   remote entity, MQTT topic, …).  The selector can be a
                #   `selector.SelectSelector` with a list of supported values.
                # -----------------------------------------------------------------
                vol.Required("controller_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["Broadlink", "Xiaomi", "MQTT", "LOOKin", "ESPHome", "ZHA", "UFOR11"]
                    )
                ),
                vol.Required("remote_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
                vol.Required("commands_encoding"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["Base64", "Hex", "Pronto", "Raw"]
                    )
                ),
                # … add any static fields you need for the device JSON folder etc.
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    # -----------------------------------------------------------------------
    # OPTIONAL – Options flow (if you want to let the user edit the entry later)
    # -----------------------------------------------------------------------
    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        return await self.async_step_user(user_input)


# ---------------------------------------------------------------------------
# 6️⃣  Helper – provide a “translation” for the UI errors we raise above.
# ---------------------------------------------------------------------------
# Create a file `strings.json` under `custom_components/smartir/translations/en.json`
# with something like:
# {
#   "config": {
#     "error": {
#       "invalid_device_data": "Unable to read or validate the device data file."
#     }
#   }
# }
