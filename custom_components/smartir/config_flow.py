# custom_components/smartir/config_flow.py
"""UI flow for the SmartIR integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector, config_validation as cv
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID

_LOGGER = logging.getLogger(__name__)

# Domaine unique pour SmartIR
DOMAIN = "smartir"

# Constante locale (n’existe pas dans Home Assistant)
CONF_DEVICE_CODE = "device_code"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _warning_log(title: str, payload: dict) -> None:
    """Convenience wrapper that logs the whole step in one line."""
    _LOGGER.warning("%s: %s", title, payload)


# ----------------------------------------------------------------------
# Main ConfigFlow
# ----------------------------------------------------------------------
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for SmartIR."""

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict | None = None

    async def _async_get_esphome_services(self) -> list[str]:
        """
        Retourne la liste triée des noms de services disponibles sous le domaine
        'esphome'. Si aucun service n’est trouvé, une liste vide est renvoyée.
        """
        try:
            all_services = await self.hass.services.async_services()
            esphome_services = sorted(all_services.get("esphome", {}).keys())
            _LOGGER.warning("ESPHome services détectés : %s", esphome_services)
            return esphome_services
        except Exception as exc:
            _LOGGER.warning("Impossible de récupérer les services ESPHome : %s", exc)
            return []

    # ---------------------------
    # Step: User
    # ---------------------------
    async def async_step_user(self, user_input=None):
        """Étape 0 – saisie des paramètres obligatoires."""
        _LOGGER.warning("SmartIR ConfigFlow : async_step_user appelé")

        if user_input:
            # L’utilisateur a soumis le formulaire.
            self._user_input = user_input
            return await self.async_create_entry(
                title=user_input.get(CONF_NAME, "SmartIR"),
                data=user_input,
            )

        # Récupération dynamique des services ESPHome
        esphome_services = await self._async_get_esphome_services()

        if esphome_services:
            es_service_selector = selector.SelectSelector(
                selector.SelectSelectorConfig(options=esphome_services)
            )
        else:  # Fallback si aucun service trouvé
            _LOGGER.warning("Aucun service ESPHome détecté – fallback mode texte.")
            es_service_selector = selector.TextSelector()

        # Construction du schéma de formulaire
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="SmartIR"): cv.string,
                vol.Required(CONF_UNIQUE_ID): cv.string,
                vol.Required(CONF_DEVICE_CODE): cv.positive_int,
                vol.Required("platform", default="climate"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["climate", "fan", "light", "media_player"]
                    )
                ),
                vol.Required("controller_type", default="ESPHome"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=["ESPHome", "Other"])
                ),
                vol.Required("esphome_service"): es_service_selector,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "example": "master_bedroom_smart_ir_send_raw_command"
            },
        )

    # ---------------------------
    # Step: Optional
    # ---------------------------
    async def async_step_optional(self, user_input=None) -> config_entries.FlowResult:
        """Step 1 – ask for optional sensors."""
        _LOGGER.warning("SmartIR ConfigFlow: async_step_optional called")

        if self._user_input is None:
            return await self.async_abort(reason="missing_user_input")

        if user_input:
            # Fusionner les données avec l’entrée initiale
            full_data = {**self._user_input, **user_input}
            return await self.async_create_entry(
                title=full_data.get(CONF_NAME, "SmartIR"),
                data=full_data,
            )

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

    # ---------------------------
    # Step: Import
    # ---------------------------
    async def async_step_import(self, import_info: dict) -> config_entries.FlowResult:
        """
        Called when a YAML entry is imported.
        We simply convert it to a config-entry so the UI stays consistent.
        """
        _LOGGER.warning("SmartIR ConfigFlow: async_step_import called")
        _warning_log("Importing data", import_info)

        # The import dict contains exactly what we would have gotten from the user
        self._user_input = import_info

        return await self.async_create_entry(
            title=import_info.get(CONF_NAME, "SmartIR"),
            data=import_info,
        )

    # ---------------------------
    # Final step
    # ---------------------------
    async def async_create_entry(self, title: str, data: dict) -> config_entries.FlowResult:
        """Create the final entry."""
        _LOGGER.warning("SmartIR ConfigFlow: creating entry %s", title)
        return super().async_create_entry(title=title, data=data)
