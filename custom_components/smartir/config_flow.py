"""Config flow for the SmartIR integration – now with a dynamic ESPHome service list."""

from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any, Dict, List

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping of controller → which UI fields are required.
# ---------------------------------------------------------------------------
CONTROLLER_FIELDS: Dict[str, Dict[str, Any]] = {
    "Broadlink": {
        "entity_selector": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote")
        ),
        "needs_service": False,
    },
    "Xiaomi": {
        "entity_selector": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote")
        ),
        "needs_service": False,
    },
    "MQTT": {
        "entity_selector": None,
        "needs_service": False,
        "extra_schema": {
            "mqtt_topic": selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )
        },
    },
    # … keep the other controllers the same as before …
    "ESPHome": {
        # the entity must be an ESPHome entity (switch, light, cover,…)
        "entity_selector": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="esphome")
        ),
        # we will **dynamically** ask for a service later
        "needs_service": True,
        "extra_schema": {},  # no static extra fields
    },
}


# ---------------------------------------------------------------------------
# Helper that we already wrote in the previous cell.
# ---------------------------------------------------------------------------
async def _async_fetch_esphome_services(
    hass: HomeAssistant, entity_id: str
) -> List[str]:
    """Return a list of ESPHome service suffixes for the given entity."""
    all_services = await hass.services.async_get_registered_services()
    esphome_services = all_services.get("esphome", {})
    prefix = f"{entity_id}."
    return [
        name.split(".", 1)[1] for name in esphome_services if name.startswith(prefix)
    ]


# ---------------------------------------------------------------------------
# The actual config flow class
# ---------------------------------------------------------------------------
class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartIR."""

    VERSION = 1

    # -----------------------------------------------------------------------
    # STEP 1 – Pick the controller type (same as before)
    # -----------------------------------------------------------------------
    async def async_step_user(self, user_input: dict | None = None):
        """First step – select the controller type."""
        if user_input is not None:
            self._controller_type = user_input["controller_type"]
            # go to the next step that asks for the generic + controller‑specific options
            return await self.async_step_generic_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("controller_type"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(CONTROLLER_FIELDS.keys())
                        )
                    )
                }
            ),
        )

    # -----------------------------------------------------------------------
    # STEP 2 – Generic + controller‑specific options (remote entity, etc.)
    # -----------------------------------------------------------------------
    async def async_step_generic_options(self, user_input: dict | None = None):
        """Collect the fields that are common to *all* controllers."""

        errors: dict = {}
        ctrl_cfg = CONTROLLER_FIELDS[self._controller_type]

        # -------------------------------------------------------------------
        # Build a base schema that contains the generic fields (name, sensors)
        # -------------------------------------------------------------------
        schema: dict = {
            vol.Optional(CONF_NAME, default="SmartIR Climate"): cv.string,
            vol.Optional(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class="temperature"
                )
            ),
            vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", device_class="humidity"
                )
            ),
        }

        # -------------------------------------------------------------------
        # Add **controller‑specific** fields that do NOT need a second step.
        # -------------------------------------------------------------------
        if ctrl_cfg.get("entity_selector"):
            schema[vol.Required("remote_entity")] = ctrl_cfg["entity_selector"]

        # Extra static fields (MQTT topic, LOOKin host, …)
        for key, sel in ctrl_cfg.get("extra_schema", {}).items():
            schema[vol.Required(key)] = sel

        # -------------------------------------------------------------------
        # If the controller *needs* an ESPHome service we cannot ask for it yet
        # because we first need to know which ESPHome entity the user picks.
        # So we store the partially‑filled data in `self._partial_data` and
        # forward to the next step.
        # -------------------------------------------------------------------
        if user_input is not None:
            # Store everything that we already have – we will merge it later.
            self._partial_data = dict(user_input)

            if ctrl_cfg.get("needs_service"):
                # The next step will ask for the ESPHome entity first.
                return await self.async_step_esphome_entity()
            # No extra step required → create the ConfigEntry now.
            return self._create_entry_from_partial()

        # Show the generic‑options form
        return self.async_show_form(
            step_id="generic_options", data_schema=vol.Schema(schema), errors=errors
        )

    # -----------------------------------------------------------------------
    # STEP 3a – ESPHome entity picker (only when controller_type == "ESPHome")
    # -----------------------------------------------------------------------
    async def async_step_esphome_entity(self, user_input: dict | None = None):
        """Ask the user to choose the ESPHome entity that will send the IR codes."""
        errors: dict = {}

        if user_input is not None:
            entity_id = user_input["esphome_entity"]
            # keep the entity_id for the next step
            self._partial_data["remote_entity"] = entity_id
            # Move to the service‑selection step
            return await self.async_step_esphome_service(entity_id=entity_id)

        # Show a simple entity‑selector limited to the ESPHome domain.
        schema = vol.Schema(
            {
                vol.Required("esphome_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="esphome")
                )
            }
        )
        return self.async_show_form(
            step_id="esphome_entity", data_schema=schema, errors=errors
        )

    # -----------------------------------------------------------------------
    # STEP 3b – ESPHome service selector (dynamic list)
    # -----------------------------------------------------------------------
    async def async_step_esphome_service(
        self, user_input: dict | None = None, *, entity_id: str
    ):
        """Present a drop‑down with *only* the ESPHome services that belong to the chosen entity."""
        errors: dict = {}

        # -------------------------------------------------------------------
        # First call – we need to fetch the service list from HA.
        # -------------------------------------------------------------------
        if not hasattr(self, "_esphome_service_options"):
            self._esphome_service_options = await _async_fetch_esphome_services(
                self.hass, entity_id
            )
            if not self._esphome_service_options:
                # No services were found – tell the user and go back to the entity step.
                errors["base"] = "no_services"
                return await self.async_step_esphome_entity()

        if user_input is not None:
            # User selected a service – store it and finish.
            self._partial_data["esphome_service"] = user_input["esphome_service"]
            return self._create_entry_from_partial()

        # Build the selector with the dynamically‑retrieved options
        schema = vol.Schema(
            {
                vol.Required("esphome_service"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._esphome_service_options,
                        sort=True,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="esphome_service", data_schema=schema, errors=errors
        )

    # -----------------------------------------------------------------------
    # Helper – create the ConfigEntry from the data we accumulated in the flow
    # -----------------------------------------------------------------------
    def _create_entry_from_partial(self):
        """Merge everything we collected and create the ConfigEntry."""
        # Merge the generic data that `async_step_generic_options` already saved
        # with the controller‑specific values that were stored in `self._partial_data`.
        data = {
            CONF_NAME: self._partial_data.get(CONF_NAME, "SmartIR Climate"),
            CONF_TEMPERATURE_SENSOR: self._partial_data.get(CONF_TEMPERATURE_SENSOR),
            CONF_HUMIDITY_SENSOR: self._partial_data.get(CONF_HUMIDITY_SENSOR),
            "controller_type": self._controller_type,
            # remote_entity is always present (either from generic step or ESPHome step)
            "remote_entity": self._partial_data["remote_entity"],
        }

        # ESPHome service (only present when controller_type == ESPHome)
        if self._controller_type == "ESPHome":
            data["esphome_service"] = self._partial_data["esphome_service"]

        # Add any *static* extra fields (MQTT topic, LOOKin host, etc.)
        ctrl_cfg = CONTROLLER_FIELDS[self._controller_type]
        for extra_key in ctrl_cfg.get("extra_schema", {}):
            if extra_key in self._partial_data:
                data[extra_key] = self._partial_data[extra_key]

        return self.async_create_entry(title=data[CONF_NAME], data=data)