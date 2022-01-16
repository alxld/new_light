"""Platform for light integration"""
from __future__ import annotations
import logging
from enum import Enum
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import ATTR_BRIGHTNESS, LightEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

# from homeassistant.components import mqtt

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

light_group = "light.office_group"


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the light platform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return
    hass.states.async_set("new_light.fake_office_light", "Setup")
    ent = OfficeLight()
    add_entities([ent])

    @callback
    def message_received(topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        hass.states.async_set("new_light.fake_office_light", payload)
        ent.message_received(topic, payload, qos)

    await hass.components.mqtt.async_subscribe(
        "zigbee2mqtt/Office Switch/action", message_received
    )

    hass.states.async_set("new_light.fake_office_light", f"Subscribed")


class Modes(Enum):
    NORMAL = 0
    COLOR = 1
    COLOR_TEMP = 2
    RIGHT_LIGHT = 3


class OfficeLight(LightEntity):
    """Office Light."""

    def __init__(self) -> None:
        """Initialize Office Light."""
        self._light = light_group
        self._name = "FakeOfficeLight"
        self._state = None
        self._brightness = None
        self._mode = Modes.NORMAL

        self.hass.states.async_set("new_light.fake_office_light", "Initialized")
        _LOGGER.info("OfficeLight initialized")

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light.
        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on.
        You can skip the brightness part if your light does not support
        brightness control.
        """

        self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        self._state = "on"
        self._mode = Modes.NORMAL
        self.hass.states.async_set("new_light.fake_office_light", "on")
        await self.hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": self._light, "brightness": self._brightness},
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._brightness = 0
        self._state = "off"
        self.hass.states.async_set("new_light.fake_office_light", "off")
        await self.hass.services.async_call(
            "light", "turn_off", {"entity_id": self._light}
        )

    def update(self) -> None:
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        # self._light.update()
        # self._state = self._light.is_on()
        # self._brightness = self._light.brightness

    def message_received(self, topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        self.hass.states.async_set("new_light.fake_office_light", f"ENT: {payload}")

        if "on-press" in payload:
            self.async_turn_on()
        elif "off-press" in payload:
            self.async_turn_off()
        else:
            self.hass.states.async_set(
                "new_light.fake_office_light", f"ENT Fail: {payload}"
            )
