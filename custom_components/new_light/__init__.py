"""The new_light integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "new_light"


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Your controller/hub specific code."""
    hass.states.set("new_light.office_light", "pre_init")
    hass.data[DOMAIN] = {"light_group": "light.office_group"}
    hass.helpers.discovery.load_platform("light", DOMAIN, {}, config)

    return True


# from __future__ import annotations
#
# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import HomeAssistant
#
# from .const import DOMAIN
#
## TODO List the platforms that you want to support.
## For your initial PR, limit it to 1 platform.
# PLATFORMS: list[str] = ["light"]
#
#
# def setup(hass, config):
#    hass.states.set("new_light.office_light", "Setup")
#    return True
#
#
# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#    """Set up new_light from a config entry."""
#    # TODO Store an API object for your platforms to access
#    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)
#
#    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
#
#    return True
#
#
# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#    """Unload a config entry."""
#    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
#    if unload_ok:
#        hass.data[DOMAIN].pop(entry.entry_id)
#
#    return unload_ok
