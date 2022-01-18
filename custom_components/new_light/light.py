"""Platform for light integration"""
from __future__ import annotations
import logging
from enum import Enum
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import ATTR_BRIGHTNESS, LightEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .right_light import RightLight

# from homeassistant.components import mqtt

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

light_group = "light.office_group"
brightness_step = 25

# TODO: Up/Down hold transitions - dropped
# TODO: Poll state of light on startup to set object initial state
# TODO: Parameterize transition times (up, down, hold)
# TODO: Add scenes to hold events from buttons
# TODO: Add 'brightness_override' parameter to increase beyond default right_light settings


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
    async def message_received(topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        hass.states.async_set("new_light.fake_office_light", payload)
        await ent.message_received(topic, payload, qos)

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
        self._brightness_override = 0
        self._mode = Modes.NORMAL

        # self.hass.states.async_set("new_light.fake_office_light", "Initialized")
        _LOGGER.info("OfficeLight initialized")

    async def async_added_to_hass(self) -> None:
        """Instantiate RightLight"""
        self._rightlight = RightLight(self._light, self.hass)

    @property
    def should_poll(self):
        """Will update state as needed"""
        return False

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
        await self._rightlight.turn_on(self._brightness, self._brightness_override)
#        self.hass.states.async_set(
#            "new_light.fake_office_light", f"on: {self._brightness}"
#        )
#
#        # await self.hass.components.mqtt.async_publish(self.hass, "zigbee2mqtt/Office/set", f"{{\"brightness\": {self._brightness}, \"state\": \"on\"}}")
#        await self.hass.services.async_call(
#            "light",
#            "turn_on",
#            {"entity_id": self._light, "brightness": self._brightness},
#        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._brightness = 0
        self._state = "off"
        await self._rightlight.disable_and_turn_off()
#        self.hass.states.async_set("new_light.fake_office_light", "off")
#
#        # await self.hass.components.mqtt.async_publish(self.hass, "zigbee2mqtt/Office/set", "OFF"})
#        await self.hass.services.async_call(
#            "light", "turn_off", {"entity_id": self._light}
#        )
        self.async_write_ha_state()

    async def up_brightness(self) -> None:
        """Increase brightness by one step"""
        if self._brightness == None:
            self._brightness = brightness_step
        elif self._brightness > (255 - brightness_step):
            self._brightness = 255
        else:
            self._brightness = self._brightness + brightness_step

        await self.async_turn_on(brightness=self._brightness)

    async def down_brightness(self) -> None:
        """Decrease brightness by one step"""
        if self._brightness == None:
            await self.async_turn_off()
        elif self._brightness < brightness_step:
            await self.async_turn_off()
        else:
            self._brightness = self._brightness - brightness_step
            await self.async_turn_on(brightness=self._brightness)

    def update(self) -> None:
        """Fetch new state data for this light.
        This is the only method that should fetch new data for Home Assistant.
        """
        # self._light.update()
        # self._state = self._light.is_on()
        # self._brightness = self._light.brightness

    async def message_received(self, topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        self.hass.states.async_set("new_light.fake_office_light", f"ENT: {payload}")

        if payload == "on-press":
            await self.async_turn_on()
        elif payload == "off-press":
            await self.async_turn_off()
        elif payload == "up-press":
            await self.up_brightness()
        elif payload == "down-press":
            await self.down_brightness()
        else:
            self.hass.states.async_set(
                "new_light.fake_office_light", f"ENT Fail: {payload}"
            )
