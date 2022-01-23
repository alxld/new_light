"""Platform for light integration"""
from __future__ import annotations
import logging, json
from enum import Enum
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import ATTR_BRIGHTNESS, LightEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers import event
from .right_light import RightLight

#TODO: Return supported features

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

light_entity = "light.office_group"
brightness_step = 32

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
    ent = OfficeLight()
    add_entities([ent])

    @callback
    async def switch_message_received(topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        await ent.switch_message_received(topic, payload, qos)

    @callback
    async def motion_sensor_message_received(topic: str, payload: str, qos: int) -> None:
        """A new motion sensor MQTT message has been received"""
        await ent.motion_sensor_message_received(topic, json.loads(payload), qos)

    await hass.components.mqtt.async_subscribe( "zigbee2mqtt/Office Switch/action", switch_message_received )
    await hass.components.mqtt.async_subscribe( "zigbee2mqtt/Theater Motion Sensor", motion_sensor_message_received )


class Modes(Enum):
    NORMAL = 0
    COLOR = 1
    COLOR_TEMP = 2
    RIGHT_LIGHT = 3


class OfficeLight(LightEntity):
    """Office Light."""

    def __init__(self) -> None:
        """Initialize Office Light."""
        self._light = light_entity
        self._name = "Office"
        self._state = 'off'
        self._brightness = 0
        self._brightness_override = 0
        self._mode = "Off"

        # Record whether a switch was used to turn on this light
        self.switched_on = False

#        # Track if the Theater Harmony is on
#        self.harmony_on = False

        # self.hass.states.async_set(f"light.{self._name}", "Initialized")
        _LOGGER.info("OfficeLight initialized")

    async def async_added_to_hass(self) -> None:
        """Instantiate RightLight"""
        self._rightlight = RightLight(self._light, self.hass)

#        #temp = self.hass.states.get(harmony_entity).new_state
#        #_LOGGER.error(f"Harmony state: {temp}")
#        event.async_track_state_change_event(self.hass, harmony_entity, self.harmony_update)

        # Not working.  Light starts up an sends None=>Off, Off=>Off, Off=>On, but not sure if that's always the case
        #event.async_track_state_change_event(self.hass, self._light, self.light_update)

#    @callback
#    async def harmony_update(self, this_event):
#        """Track harmony updates"""
#        ev = this_event.as_dict()
#        ns = ev["data"]["new_state"].state
#        if ns == "on":
#            self.harmony_on = True
#        else:
#            self.harmony_on = False

    @callback
    async def light_update(self, this_event):
        """Get initial light state"""
        ev = this_event.as_dict()
        if self._state == None and ev["data"]["old_state"] != None:
            _LOGGER.error(f"Light update: {this_event}")

    def _updateState(self, comment = ""):
#        self.hass.states.async_set(f"light.{self._name}", self._state, {"brightness": self._brightness, "brightness_override": self._brightness_override, "switched_on": self.switched_on, "harmony_on": self.harmony_on, "mode": self._mode, "comment": comment})
        self.hass.states.async_set(f"light.{self._name}", self._state, {"brightness": self._brightness, "brightness_override": self._brightness_override, "switched_on": self.switched_on, "mode": self._mode, "comment": comment})

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

#    @property
#    def supported_color_modes(self) -> set[str] | None:
#        return ['color_temp', 'xy']

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on.
        You can skip the brightness part if your light does not support
        brightness control.
        """
        self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        self._state = "on"
        self._mode = "On"
        await self._rightlight.turn_on(brightness=self._brightness, brightness_override=self._brightness_override)
        self._updateState()

#        # await self.hass.components.mqtt.async_publish(self.hass, "zigbee2mqtt/Office/set", f"{{\"brightness\": {self._brightness}, \"state\": \"on\"}}")
#        await self.hass.services.async_call(
#            "light",
#            "turn_on",
#            {"entity_id": self._light, "brightness": self._brightness},
#        )
        self.async_write_ha_state()

    async def async_turn_on_mode(self, **kwargs: Any) -> None:
        self._mode = kwargs.get("mode", "Vivid")
        self._state = "on"
        await self._rightlight.turn_on(mode=self._mode)
        self._updateState()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._brightness = 0
        self._brightness_override = 0
        self._state = "off"
        await self._rightlight.disable_and_turn_off()
        self._updateState()

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
            self._brightness_override = self._brightness_override + brightness_step
        else:
            self._brightness = self._brightness + brightness_step

        await self.async_turn_on(brightness=self._brightness)

    async def down_brightness(self) -> None:
        """Decrease brightness by one step"""
        if self._brightness == None:
            await self.async_turn_off()
        elif self._brightness_override > 0:
            self._brightness_override = 0
            await self.async_turn_on(brightness=self._brightness)
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

    async def switch_message_received(self, topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        #self.hass.states.async_set(f"light.{self._name}", f"ENT: {payload}")
        self._updateState(f"{payload}")

        self.switched_on = True
        if payload == "on-press":
            await self.async_turn_on()
        elif payload == "on-hold":
            await self.async_turn_on_mode(mode="Vivid")
        elif payload == "off-press":
            self.switched_on = False
            await self.async_turn_off()
        elif payload == "up-press":
            await self.up_brightness()
        elif payload == "up-hold":
            await self.async_turn_on_mode(mode="Bright")
        elif payload == "down-press":
            await self.down_brightness()
        else:
            self._updateState(f"Fail: {payload}")

#    async def motion_sensor_message_received(self, topic: str, payload: str, qos: int) -> None:
#        """A new MQTT message has been received."""
#        occ = payload["occupancy"]
#        self._updateState(f"OCC: {occ}")
#
#        # Disable motion sensor tracking if the lights are switched on or the harmony is on
#        if self.switched_on or self.harmony_on:
#            return
#
#        if occ == "true":
#            await self.async_turn_on()
#        elif occ == "false":
#            await self.async_turn_off()