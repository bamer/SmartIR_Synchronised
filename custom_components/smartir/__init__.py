# custom_components/smartir/__init__.py
"""SmartIR integration entry point."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the SmartIR integration from YAML (deprecated)."""
    # The old `async_setup_platform` functions are now replaced by
    # `async_setup_entry`.  If you still want to support legacy yaml,
    # keep this wrapper and delegate to `load_device_data_file`.
    _LOGGER.warning(
        "The SmartIR integration is now config‑entry based. "
        "Please remove any 'platform: smartir' entries from configuration.yaml."
    )
    return True
