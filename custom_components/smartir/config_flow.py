"""Config flow for the SmartIR integration.

The flow works in two UI steps :

1️⃣  Choose the controller type (Broadlink, MQTT, ESPHome, …)  
2️⃣  Generic options (name, optional sensors, plus the fields that are
    specific to the selected controller).

The only special case is **ESPHome** : instead of asking for a “remote
entity” we ask the user to choose an **ESPHome action (service)** that
really exists on the host.  The list of actions is built dynamically
from the current Home‑Assistant service registry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

# ---------------------------------------------------------------------------
#  Constantes de ton intégration (tu les as déjà dans const.py)
# ---------------------------------------------------------------------------
from .const import (
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Définition des champs que chaque type de contrôleur requiert.
#  Pour ESPHome on **ne** demande **pas** de remote_entity, on demande
#  un service (action) à la place.
# ---------------------------------------------------------------------------
CONTROLLER_FIELDS: Dict[str, Dict[str, Any]] = {
    # -----------------------------------------------------------------------
    # Controllers that use a *remote* entity (Broadlink, Xiaomi, …)
    # -----------------------------------------------------------------------
    "Broadlink": {
        "entity_selector": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote")
        ),
        "needs_action": False,
        "extra_schema": {},  # ← pas de champs supplémentaires ici
    },
    "Xiaomi": {
        "entity_selector": selector.EntitySelector(
            selector.EntitySelectorConfig(domain="remote")
        ),
        "needs_action": False,
        "extra_schema": {},
    },
    # -----------------------------------------------------------------------
    # MQTT – only a topic is required
    # -----------------------------------------------------------------------
    "MQTT": {
        "entity_selector": None,
        "needs_action": False,
        "extra_schema": {
            "mqtt_topic": selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )
        },
    },
    # -----------------------------------------------------------------------
    # LOOKin – only the host address is required
    # -----------------------------------------------------------------------
    "LOOKin": {
        "entity_selector": None,
        "needs_action": False,
        "extra_schema": {
            "remote_host": selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )
        },
    },
    # -----------------------------------------------------------------------
    # ZHA – several numeric / string fields
    # -----------------------------------------------------------------------
    "ZHA": {
        "entity_selector": None,
        "needs_action": False,
        "extra_schema": {
            "zha_ieee": selector.TextSelector(),
            "zha_endpoint_id": selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=255, step=1)
            ),
            "zha_cluster_id": selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=65535, step=1)
            ),
            "zha_cluster_type": selector.TextSelector(),
            "zha_command": selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=65535, step=1)
            ),
            "zha_command_type": selector.TextSelector(),
        },
    },
    # -----------------------------------------------------------------------
    # UFOR11 – just a MQTT topic like the normal MQTT controller
    # -----------------------------------------------------------------------
    "UFOR11": {
        "entity_selector": None,
        "needs_action": False,
        "extra_schema": {
            "mqtt_topic": selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            )
        },
    },
    # -----------------------------------------------------------------------
    # **ESPHome** – no remote entity, we need a *service* (action)
    # -----------------------------------------------------------------------
    "ESPHome": {
        "entity_selector": None,               # ← on ne demande pas d’entité remote
        "needs_action": True,                  # ← indique qu’on doit demander un service
        "extra_schema": {},                    # aucun autre champ spécial
    },
}


# ---------------------------------------------------------------------------
#  Helper – retourne la liste de *tous* les services ESPHome enregistrés.
# ---------------------------------------------------------------------------
async def _async_list_esphome_services(hass: HomeAssistant) -> List[str]:
    """Return a sorted list like ['esphome.my_ac.toggle', 'esphome.my_ac.turn_on', …]."""
    all_services = await hass.services.async_get_registered_services()
    esphome = all_services.get("esphome", {})
    # chaque clef de ``esphome`` est déjà du type "my_ac.toggle"
    return sorted([f"esphome.{svc}" for svc in esphome])


# ---------------------------------------------------------------------------
#  Config flow class
# ---------------------------------------------------------------------------
class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartIR."""

    VERSION = 1

    # -----------------------------------------------------------------------
    # STEP 1 – Choix du type de contrôleur
    # -----------------------------------------------------------------------
    async def async_step_user(self, user_input: dict | None = None):
        """First step – ask the user which controller they want to use."""
        if user_input is not None:
            self._controller_type = user_input["controller_type"]
            # Passe directement à l’étape qui contient les options génériques
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
    # STEP 2 – Options génériques (nom, capteurs, puis champs propres au
    #            contrôleur choisi).  C’est le seul endroit qui change
    #            pour ESPHome (on affiche un service au lieu d’une entité).
    # -----------------------------------------------------------------------
    async def async_step_generic_options(self, user_input: dict | None = None):
        """Collect the generic options and the controller‑specific options."""
        errors: dict = {}
        ctrl_cfg = CONTROLLER_FIELDS[self._controller_type]

        # -------------------- 2.1  Base schema (identique pour tous) ----------
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

        # -------------------- 2.2  Remote entity (pour les contrôleurs qui en ont) ----------
        if ctrl_cfg.get("entity_selector"):
            schema[vol.Required("remote_entity")] = ctrl_cfg["entity_selector"]

        # -------------------- 2.3  Champs “extra” (MQTT topic, LOOKin host, …) ----------
        for key, sel in ctrl_cfg.get("extra_schema", {}).items():
            schema[vol.Required(key)] = sel

        # -------------------- 2.4  Cas spécial ESPHome : choisir un service ----------
        if self._controller_type == "ESPHome":
            # On récupère la liste des services ESPHome disponibles
            service_options = await _async_list_esphome_services(self.hass)

            if not service_options:
                # Aucun service trouvé → on montre l’erreur
                errors["base"] = "no_esphome_actions"
            else:
                schema[vol.Required("esphome_action")] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=service_options,
                        sort=True,
                        # le texte affiché sera exactement le nom complet du service
                        # (ex. “esphome.my_ac.toggle”)
                    )
                )

        # -------------------- 2.5  L’utilisateur a validé le formulaire ------------
        if user_input is not None:
            # On mémorise tout ce qui a été saisi
            self._partial_data = dict(user_input)

            # Pour ESPHome on garde le service choisi sous la clé «esphome_action»,
            # le reste du flow (création de l’entrée) attend simplement que la
            # donnée soit présente dans ``self._partial_data``.
            if self._controller_type == "ESPHome":
                self._partial_data["esphome_action"] = user_input["esphome_action"]

            # Aucun sous‑step supplémentaire → on crée l’entrée
            return self._create_entry_from_partial()

        # -------------------- 2.6  Affichage du formulaire --------------------
        return self.async_show_form(
            step_id="generic_options", data_schema=vol.Schema(schema), errors=errors
        )

    # -----------------------------------------------------------------------
    # Helper – construit le dictionnaire qui sera stocké dans le ConfigEntry
    # -----------------------------------------------------------------------
    def _create_entry_from_partial(self):
        """Combine everything we have gathered and create the ConfigEntry."""
        data: dict = {
            CONF_NAME: self._partial_data.get(CONF_NAME, "SmartIR Climate"),
            CONF_TEMPERATURE_SENSOR: self._partial_data.get(
                CONF_TEMPERATURE_SENSOR
            ),
            CONF_HUMIDITY_SENSOR: self._partial_data.get(CONF_HUMIDITY_SENSOR),
            "controller_type": self._controller_type,
        }


        # -------------------------------------------------------------------
        # Remote entity – présent pour tous les contrôleurs *sauf* ESPHome
        # -------------------------------------------------------------------
        if self._controller_type != "ESPHome":
            data["remote_entity"] = self._partial_data["remote_entity"]
        else:
            # ESPHome – on stocke le service complet choisi par l’utilisateur
            data["esphome_action"] = self._partial_data["esphome_action"]

        # -------------------------------------------------------------------
        # Extra fields (MQTT topic, LOOKin host, ZHA data, …)
        # -------------------------------------------------------------------
        ctrl_cfg = CONTROLLER_FIELDS[self._controller_type]
        for extra_key in ctrl_cfg.get("extra_schema", {}):
            if extra_key in self._partial_data:
                data[extra_key] = self._partial_data[extra_key]

        return self.async_create_entry(title=data[CONF_NAME], data=data)

    # -----------------------------------------------------------------------
    # (Optionnel)  Gestion des erreurs de traduction – tu peux ajouter les
    # strings dans `translations/en.json` ou `translations/fr.json`
    # -----------------------------------------------------------------------
    # Exemple de fichiers JSON :
    #
    #   {
    #     "config": {
    #       "error": {
    #         "no_esphome_actions": "Aucun service ESPHome n’a été trouvé sur cet hôte."
    #       }
    #     }
    #   }
    #
