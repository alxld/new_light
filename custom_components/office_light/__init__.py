"""The new office_light integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "office_light"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    #hass.states.async_set("new_light.fake_office_light", "pre_init")
    #hass.data[DOMAIN] = {"temperature": 23}
    hass.helpers.discovery.load_platform("light", DOMAIN, {}, config)

    return True
