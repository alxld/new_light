"""Platform for light integration"""
from __future__ import annotations
from collections import OrderedDict

import json
import logging
import sys

from homeassistant.components.light import (  # ATTR_EFFECT,; ATTR_FLASH,; ATTR_WHITE_VALUE,; PLATFORM_SCHEMA,; SUPPORT_EFFECT,; SUPPORT_FLASH,; SUPPORT_WHITE_VALUE,; ATTR_SUPPORTED_COLOR_MODES,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    ATTR_MAX_MIREDS,
    ATTR_MIN_MIREDS,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ENTITY_ID_FORMAT,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    SUPPORT_TRANSITION,
    LightEntity,
)
from homeassistant.const import (  # ATTR_SUPPORTED_FEATURES,; CONF_ENTITY_ID,; CONF_NAME,; CONF_OFFSET,; CONF_UNIQUE_ID,; EVENT_HOMEASSISTANT_START,; STATE_ON,; STATE_UNAVAILABLE,
    ATTR_ENTITY_ID,
)

# from enum import Enum
# import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import event
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

sys.path.append("custom_components/right_light")
from right_light import RightLight

_LOGGER = logging.getLogger(__name__)


class NewLight(LightEntity):
    """New Light Super Class"""

    entities = OrderedDict()
    """Dictionary of entities.  Each will be a rightlight object and be addressable from the json buttonmap.  The first
    added entity will be the default entity for this light."""

    has_switch = False
    """Does this light have an associated switch?  Override to set to true if needed"""

    switch_action = None
    """MQTT topic to monitor for switch activity.  Typically zigbee2mqtt/<room> Switch/action"""

    has_json = False
    """Does this light have a JSON buttonmap?  Override to set to true if needed"""

    has_motion_sensor = False
    """Does this light have an associated motion sensor?  Override to set to true if needed"""

    has_brightness_threshold = False
    """Does this light use a brightness threshold switch?  Override to set to true if needed"""

    brightness_threshold = 128
    """Brightness threshold above which to also turn on second light entity"""

    has_harmony = False
    """Does this light have an associated Harmony hub?  Override to set to true if needed"""

    harmony_entity = None
    """Entity name of harmony hub if one exists"""

    brightness_step = 43
    """Step to increment/decrement brightness when using a switch"""

    motion_sensor_brightness = 192
    """Brightness of this light when a motion sensor turns it on"""

    def __init__(self, name, debug=False, debug_rl=False) -> None:
        """Initialize NewLight Super Class."""
        self._name = name
        # self._state = 'off'
        self._brightness = 0
        """Light's current brightness"""
        self._brightness_override = 0
        """Allow brightness above 255 (for going brighter than RightLight default)"""
        self._hs_color: Optional[Tuple[float, float]] = None
        """Light's current color in hs"""
        self._color_temp: Optional[int] = None
        """Light's current color in Kelvin"""
        self._rgb_color: Optional[Tuple[int, int, int]] = None
        """Light's current color in RGB"""
        self._min_mireds: int = 154
        """Light's minimum supported mireds"""
        self._max_mireds: int = 500
        """Light's maximum supported mireds"""
        self._mode = "Off"
        """Light's current mode"""
        self._is_on = False
        """Boolean to show if light is on"""
        self._available = True
        """Boolean to show if light is available (always true)"""
        self._occupancy = False
        """Boolean for tracking motion sensor state"""
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, self._name, [])
        """Generates a unique entity ID based on instance's name"""
        # self._white_value: Optional[int] = None
        self._effect_list: Optional[List[str]] = None
        """A list of supported effects"""
        # self._effect: Optional[str] = None
        self._supported_features: int = 0
        """Supported features of this light.  OR togther SUPPORT_BRIGHTNESS, SUPPORT_COLOR_TEMP, SUPPORT_COLOR, SUPPORT_TRANSITION"""
        self._supported_features |= SUPPORT_BRIGHTNESS
        self._supported_features |= SUPPORT_COLOR_TEMP
        self._supported_features |= SUPPORT_COLOR
        self._supported_features |= SUPPORT_TRANSITION
        # self._supported_features |= SUPPORT_WHITE_VALUE

        self._buttonCounts = {
            "on-press": 0,
            "on-hold": 0,
            "up-press": 0,
            "up-hold": 0,
            "down-press": 0,
            "down-hold": 0,
            "off-press": 0,
            "off-hold": 0,
        }
        """Stores current button presses for handling JSON buttonmap lists"""

        self._switched_on = False
        """Boolean showing whether the light was turned on by a switch/GUI"""

        self._harmony_on = False
        """Track state of associated harmony hub"""

        self._debug = debug
        """Boolean to enable debug mode"""

        self._debug_rl = debug_rl
        """Boolean to enable RightLight debug mode"""

        if self._debug:
            _LOGGER.info(f"{self._name} Light initialized")

    async def async_added_to_hass(self) -> None:
        """Initialize light objects"""
        # Instantiate per-entity rightlight objects
        for entname in self.entities.keys():
            self.entities[entname] = RightLight(entname, self.hass, self._debug_rl)

        # Subscribe to switch events
        if self.has_switch:
            if self.has_json:
                await self.hass.components.mqtt.async_subscribe(
                    self.switch_action, self.json_switch_message_received
                )
            else:
                await self.hass.components.mqtt.async_subscribe(
                    self.switch_action, self.switch_message_received
                )

        # Subscribe to motion sensor events
        if self.has_motion_sensor:
            await self.hass.components.mqtt.async_subscribe(
                self.motion_sensor_action, self.motion_sensor_message_received
            )

        # Subscribe to harmony events
        if self.has_harmony:
            event.async_track_state_change_event(
                self.hass, self.harmony_entity, self.harmony_update
            )

        self.async_schedule_update_ha_state(force_refresh=True)

    @property
    def should_poll(self):
        """Allows for color updates to be polled"""
        return True

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._is_on

    @property
    def device_info(self):
        prop = {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (self._name, self.unique_id)
            },
            "name": self._name,
            "manufacturer": "Aaron",
        }
        return prop

    @property
    def unique_id(self):
        """Return the unique id of the light."""
        return self.entity_id

    @property
    def available(self) -> bool:
        """Return whether the light group is available."""
        return self._available

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def hs_color(self) -> Optional[Tuple[float, float]]:
        """Return the hue and saturation color value [float, float]."""
        return self._hs_color

    @property
    def color_temp(self) -> Optional[int]:
        """Return the CT color value in mireds."""
        return self._color_temp

    @property
    def min_mireds(self) -> int:
        """Return the coldest color_temp that this light group supports."""
        return self._min_mireds

    @property
    def max_mireds(self) -> int:
        """Return the warmest color_temp that this light group supports."""
        return self._max_mireds

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        return self._rgb_color

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    async def async_turn_on(self, **kwargs) -> None:
        """Instruct the light to turn on."""
        if self._debug:
            _LOGGER.error(f"{self._name} LIGHT ASYNC_TURN_ON: {kwargs}")

        if "brightness" in kwargs:
            self._brightness = kwargs["brightness"]
        elif self._brightness == 0:
            self._brightness = 255

        if "source" in kwargs and kwargs["source"] == "MotionSensor":
            pass
        else:
            self._switched_on = True

        if "source" in kwargs and kwargs["source"] == "Switch":
            # Assume RightLight mode for all switch presses
            rl = True
        elif self._is_on == False:
            # If light is off, default to RightLight mode (can be overriden with color/colortemp attributes)
            rl = True
        else:
            rl = False
        # rl = True

        self._is_on = True
        self._mode = "On"
        data = {ATTR_ENTITY_ID: list(self.entities.keys())[0], "transition": 0.1}

        if ATTR_HS_COLOR in kwargs:
            rl = False
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        if ATTR_RGB_COLOR in kwargs:
            rl = False
            data[ATTR_RGB_COLOR] = kwargs[ATTR_RGB_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_COLOR_TEMP in kwargs:
            rl = False
            data[ATTR_COLOR_TEMP] = kwargs[ATTR_COLOR_TEMP]
        if ATTR_COLOR_MODE in kwargs:
            rl = False
            data[ATTR_COLOR_MODE] = kwargs[ATTR_COLOR_MODE]
        if ATTR_TRANSITION in kwargs:
            data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

        f, r = self.getEntityNames()

        # Disable other entities before turning on main entity
        for ent in r:
            await self.entities[ent].disable()

        if rl:
            # Turn on light using RightLight
            await self.entities[f].turn_on(
                brightness=self._brightness,
                brightness_override=self._brightness_override,
            )
        else:
            # Use for other modes, like specific color or temperatures
            await self.entities[f].turn_on_specific(data)

        if self.has_brightness_threshold and (
            self._brightness > self.brightness_threshold
        ):
            # Process second entity if over brightness threshold
            if rl:
                # Turn on second entity using RightLight
                await self.entities[r[0]].turn_on(
                    brightness=self._brightness,
                    brightness_override=self._brightness_override,
                )
            else:
                # Use for other modes, like specific color or temperatures
                await self.entities[r[0]].turn_on_specific(data)

        self.async_schedule_update_ha_state(force_refresh=True)

    def getEntityNames(self):
        """Split entity key list into first (default) and rest list"""
        k = list(self.entities.keys())
        return k[0], k[1:]

    async def async_turn_on_mode(self, **kwargs: Any) -> None:
        """Turn on one of RightLight's color modes"""
        self._mode = kwargs.get("mode", "Vivid")
        self._is_on = True
        self._brightness = 255
        self._switched_on = True

        f, r = self.getEntityNames()
        # Disable other entities before turning on main entity
        for ent in r:
            await self.entities[ent].disable()
        await self.entities[f].turn_on(mode=self._mode)

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._brightness = 0
        self._brightness_override = 0
        self._is_on = False
        self._switched_on = False

        f, r = self.getEntityNames()
        # Disable other entities before turning off main entity
        for ent in r:
            await self.entities[ent].disable()
        await self.entities[f].disable_and_turn_off()

        self.async_schedule_update_ha_state(force_refresh=True)

    async def up_brightness(self, **kwargs) -> None:
        """Increase brightness by one step"""
        if self._brightness == None:
            self._brightness = self.brightness_step
        elif self._brightness > (255 - self.brightness_step):
            self._brightness = 255
            self._brightness_override = self._brightness_override + self.brightness_step
        else:
            self._brightness = self._brightness + self.brightness_step

        await self.async_turn_on(brightness=self._brightness, **kwargs)

    async def down_brightness(self, **kwargs) -> None:
        """Decrease brightness by one step"""
        if self._brightness == None:
            await self.async_turn_off(**kwargs)
        elif self._brightness_override > 0:
            self._brightness_override = 0
            await self.async_turn_on(brightness=self._brightness, **kwargs)
        elif self._brightness < self.brightness_step:
            await self.async_turn_off(**kwargs)
        else:
            self._brightness = self._brightness - self.brightness_step
            await self.async_turn_on(brightness=self._brightness, **kwargs)

    async def async_update(self):
        """Query light and determine the state."""
        if self._debug:
            _LOGGER.error(f"{self._name} LIGHT ASYNC_UPDATE")

        f, r = self.getEntityNames()
        state = self.hass.states.get(f)

        if state == None:
            return

        self._hs_color = state.attributes.get(ATTR_HS_COLOR, self._hs_color)
        self._rgb_color = state.attributes.get(ATTR_RGB_COLOR, self._rgb_color)
        self._color_temp = state.attributes.get(ATTR_COLOR_TEMP, self._color_temp)
        self._min_mireds = state.attributes.get(ATTR_MIN_MIREDS, 154)
        self._max_mireds = state.attributes.get(ATTR_MAX_MIREDS, 500)
        self._effect_list = state.attributes.get(ATTR_EFFECT_LIST)

        # Reload JSON buttonmap regularly
        if self.has_json:
            self._button_map_data = json.load(
                open(f"custom_components/{self._name}/button_map.json")
            )

    @callback
    async def switch_message_received(self, topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        # self.hass.states.async_set(f"light.{self._name}", f"ENT: {payload}")

        self.switched_on = True
        if payload == "on-press":
            self._brightness_override = 0
            await self.async_turn_on(source="Switch", brightness=255)
        elif payload == "on-hold":
            self._brightness_override = 128
            await self.async_turn_on(source="Switch", brightness=255)
        elif payload == "off-press":
            self.switched_on = False
            await self.async_turn_off(source="Switch")
        elif payload == "up-press":
            await self.up_brightness(source="Switch")
        elif payload == "down-press":
            await self.down_brightness(source="Switch")
        else:
            _LOGGER.error(f"{self._name} switch handler fail: {payload}")

    @callback
    async def json_switch_message_received(
        self, topic: str, payload: str, qos: int
    ) -> None:
        """A new MQTT message has been received."""
        if payload in self._button_map_data.keys():
            config_list = self._button_map_data[payload]
            this_list = config_list[self._buttonCounts[payload]]

            # Increment button count and loop to zero.  Zero out the rest
            self._buttonCounts[payload] += 1
            if self._buttonCounts[payload] >= len(config_list):
                self._buttonCounts[payload] = 0
            for key in self._buttonCounts.keys():
                if key != payload:
                    self._buttonCounts[key] = 0

            for command in this_list:
                if self._debug:
                    _LOGGER.error(f"{self._name} JSON Switch command: {command}")
                if command[0] == "Brightness":
                    ent = command[1]
                    br = command[2]

                    if br == 0:
                        await self.hass.services.async_call(
                            "light", "turn_off", {"entity_id": ent}
                        )
                    else:
                        await self.hass.services.async_call(
                            "light", "turn_on", {"entity_id": ent, "brightness": br}
                        )
                elif command[0] == "RightLight":
                    ent = command[1]
                    val = command[2]

                    if not ent in self.entities:
                        self.entities[ent] = RightLight(ent, self.hass, self._debug_rl)
                        # _LOGGER.error(f"{self._name} error: Unknown entity '{ent}' in button_map.json.  Should be one of: {self.entities.keys()}")
                        # continue

                    rl = self.entities[ent]

                    if val == "Disable":
                        await rl.disable()
                    elif val in rl.getColorModes():
                        await rl.turn_on(mode=val)
                    elif (val == 0) or (val == "Off"):
                        await rl.disable_and_turn_off()
                    else:
                        await rl.turn_on(brightness=val, brightness_override=0)
                elif command[0] == "Scene":
                    if self._debug:
                        _LOGGER.error(f"{self._name} JSON Switch Scene: {command[1]}")
                    await self.hass.services.async_call(
                        "scene", "turn_on", {"entity_id": command[1]}
                    )
                else:
                    _LOGGER.error(
                        f"{self._name} error - unrecognized button_map.json command type: {command[0]}"
                    )

    @callback
    async def motion_sensor_message_received(
        self, topic: str, payload: str, qos: int
    ) -> None:
        """A new MQTT message has been received."""
        if self._occupancy == payload["occupancy"]:
            # No change to state
            return

        self._occupancy = payload["occupancy"]

        # Disable motion sensor tracking if the lights are switched on or the harmony is on
        if self.switched_on or (self.has_harmony and self._harmony_on):
            return

        if self._occupancy:
            await self.async_turn_on(
                brightness=self.motion_sensor_brightness, source="MotionSensor"
            )
        else:
            await self.async_turn_off()

    @callback
    async def harmony_update(self, this_event):
        """Track harmony updates"""
        ev = this_event.as_dict()
        ns = ev["data"]["new_state"].state
        if ns == "on":
            self._harmony_on = True
        else:
            self._harmony_on = False
