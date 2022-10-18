"""Platform for Crestron Light integration."""
import asyncio

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import LightEntity, LightEntityFeature, ColorMode, ATTR_TRANSITION, ATTR_BRIGHTNESS
from homeassistant.const import CONF_NAME, CONF_TYPE
from .const import HUB, DOMAIN, CONF_JOIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TYPE): vol.In(["brightness", "onoff"]),
        vol.Required(CONF_JOIN): cv.positive_int,           
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronLight(hub, config)]
    async_add_entities(entity)


class CrestronLight(LightEntity):
    def __init__(self, hub, config):
        self._hub = hub
        self._name = config.get(CONF_NAME)
        self._join = config.get(CONF_JOIN)
        if config.get(CONF_TYPE) == "brightness":
            self._color_mode = ColorMode.BRIGHTNESS
        else:
            self._color_mode = ColorMode.ONOFF

    async def async_added_to_hass(self):
        self._hub.register_callback(self.process_callback)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        self.async_write_ha_state()

    @property
    def available(self):
        return self._hub.is_available()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        if self._color_mode == ColorMode.BRIGHTNESS:
            return 'light-' + str(self._join)
        else:
            return 'toggle-light-' + str(self._join)

    @property
    def color_mode(self):
        return self._color_mode

    @property
    def supported_color_modes(self):
        return {ColorMode.BRIGHTNESS, ColorMode.ONOFF}

    @property
    def supported_features(self):
        if self._color_mode == ColorMode.BRIGHTNESS:
            return LightEntityFeature.TRANSITION

    @property
    def should_poll(self):
        return False

    @property
    def brightness(self):
        if self._color_mode == ColorMode.BRIGHTNESS:
            return min(255, int(self._hub.get_analog(self._join) / 255))

    @property
    def is_on(self):
        if self._color_mode == ColorMode.BRIGHTNESS:
            if int(self._hub.get_analog(self._join) / 255) > 0:
                return True
            else:
                return False
        elif self._color_mode == ColorMode.ONOFF:
            return self._hub.get_digital(self._join)

    async def async_turn_on(self, **kwargs):
        if self._color_mode == ColorMode.ONOFF:
                self._hub.set_digital(self._join, True)
        elif self._color_mode == ColorMode.BRIGHTNESS:
            if ATTR_BRIGHTNESS not in kwargs:
                # If light supports dimming and does not provide a brightness, still transition with 2 seconds
                await self.__transition(65535, 2)
            else:
                brightness = int(kwargs[ATTR_BRIGHTNESS] * 255)
                if ATTR_TRANSITION not in kwargs:
                    self._hub.set_analog(self._join, brightness)
                else:
                    await self.__transition(brightness, int(kwargs[ATTR_TRANSITION]))

    async def async_turn_off(self, **kwargs):
        if self._color_mode == ColorMode.ONOFF:
            self._hub.set_digital(self._join, False)
        if self._color_mode == ColorMode.BRIGHTNESS:
            if ATTR_TRANSITION not in kwargs:
                await self.__transition(0, 2)
            else:
                await self.__transition(0, int(kwargs[ATTR_TRANSITION]))

    async def __transition(self, brightness, transition_time):
        if transition_time == 0:
            self._hub.set_analog(self._join, int(brightness))
        else:
            incr_per_step = (brightness - self._hub.get_analog(self._join)) / (transition_time * 20)
            current_brightness = self._hub.get_analog(self._join)
            for i in range(transition_time * 20):
                current_brightness = current_brightness + incr_per_step
                self._hub.set_analog(self._join, int(current_brightness))
                await asyncio.sleep(0.05)
