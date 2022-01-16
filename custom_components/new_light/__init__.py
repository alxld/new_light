"""The new_light integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "new_light"


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    hass.states.set("new_light.office_light", "pre_init")
    hass.data[DOMAIN] = {"temperature": 23}
    hass.helpers.discovery.load_platform("light", DOMAIN, {}, config)
    # hass.helpers.discovery.load_platform("sensor", DOMAIN, {}, config)

    return True
