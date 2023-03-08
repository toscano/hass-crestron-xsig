"""Platform for Crestron Shades integration."""

import asyncio
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.cover import (
    CoverEntity,
    DEVICE_CLASS_SHADE,
    DEVICE_CLASS_CURTAIN,
    SUPPORT_OPEN,
    SUPPORT_CLOSE,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    STATE_OPENING,
    STATE_OPEN,
    STATE_CLOSING,
    STATE_CLOSED,
)
from homeassistant.const import CONF_NAME, CONF_TYPE
from .const import (
    HUB,
    DOMAIN,
    CONF_IS_OPENING_JOIN,
    CONF_IS_CLOSING_JOIN,
    CONF_IS_CLOSED_JOIN,
    CONF_STOP_JOIN,
    CONF_POS_JOIN,
    CONF_IS_MOVING_JOIN,
    CONF_OPEN_FULL_JOIN,
    CONF_CLOSE_FULL_JOIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TYPE): vol.In(["analog_shade", "digital_shade", "digital_curtain"]),
        vol.Required(CONF_IS_OPENING_JOIN): cv.positive_int,
        vol.Required(CONF_IS_CLOSING_JOIN): cv.positive_int,
        vol.Required(CONF_STOP_JOIN): cv.positive_int,
        vol.Optional(CONF_IS_MOVING_JOIN): cv.positive_int,
        vol.Optional(CONF_IS_CLOSED_JOIN): cv.positive_int,
        vol.Optional(CONF_POS_JOIN): cv.positive_int,    
        vol.Optional(CONF_OPEN_FULL_JOIN): cv.positive_int,
        vol.Optional(CONF_CLOSE_FULL_JOIN): cv.positive_int
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronShade(hub, config)]
    async_add_entities(entity)

class CrestronShade(CoverEntity):
    def __init__(self, hub, config):
        self._hub = hub
        self._type = config.get(CONF_TYPE)
        if (self._type == "analog_shade"):
            self._digital = False
            self._device_class = DEVICE_CLASS_SHADE
            self._supported_features = (
                SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION | SUPPORT_STOP
            )
            self._is_closed_join = config.get(CONF_IS_CLOSED_JOIN)
            self._pos_join = config.get(CONF_POS_JOIN)
        elif (self._type == "digital_shade"):
            self._digital = True
            self._device_class = DEVICE_CLASS_SHADE
            self._supported_features = (
                SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
            )
            self._is_moving_join = config.get(CONF_IS_MOVING_JOIN)
            self._open_full_join = config.get(CONF_OPEN_FULL_JOIN)
            self._close_full_join = config.get(CONF_CLOSE_FULL_JOIN)
        elif (self._type == "digital_curtain"):
            self._digital = True
            self._device_class = DEVICE_CLASS_CURTAIN
            self._supported_features = (
                SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
            )
            self._is_moving_join = config.get(CONF_IS_MOVING_JOIN)
            self._open_full_join = config.get(CONF_OPEN_FULL_JOIN)
            self._close_full_join = config.get(CONF_CLOSE_FULL_JOIN)

        self._should_poll = False

        self._name = config.get(CONF_NAME)
        self._is_opening_join = config.get(CONF_IS_OPENING_JOIN)
        self._is_closing_join = config.get(CONF_IS_CLOSING_JOIN)
        self._stop_join = config.get(CONF_STOP_JOIN)        
        self._manual_stop = False

    async def async_added_to_hass(self):
        self._hub.register_callback(self.process_callback)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        self.async_write_ha_state()

    @property
    def unique_id(self):
       return 'cover-' + str(self._is_opening_join) + str(self._is_closing_join)
       
    @property
    def available(self):
        return self._hub.is_available()

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        return self._device_class

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def should_poll(self):
        return self._should_poll

    @property
    def current_cover_position(self):
        if not self._digital:
            return self._hub.get_analog(self._pos_join) / 655.35

    @property
    def is_opening(self):
        if self._digital:
            return self._hub.get_digital(self._is_opening_join) and self._hub.get_digital(self._is_moving_join)
        else:
            return self._hub.get_digital(self._is_opening_join)

    @property
    def is_closing(self):
        if self._digital:
            return self._hub.get_digital(self._is_closing_join) and self._hub.get_digital(self._is_moving_join)
        else:
            return self._hub.get_digital(self._is_closing_join)

    @property
    def is_closed(self):
        if self._digital:
            if self._manual_stop:
                return None
            else:
                return self._hub.get_digital(self._is_closing_join) and not self._hub.get_digital(self._is_moving_join)
        else:
            return self._hub.get_digital(self._is_closed_join)

    async def async_set_cover_position(self, **kwargs):
        if not self._digital:
            self._hub.set_analog(self._pos_join, int(kwargs["position"]) * 655)
            self._manual_stop = False

    async def async_open_cover(self, **kwargs):
        self._manual_stop = False
        if self._digital:
            self._hub.set_digital(self._open_full_join, 1)
            await asyncio.sleep(0.2)
            self._hub.set_digital(self._open_full_join, 0)
        else:
            self._hub.set_analog(self._pos_join, 0xFFFF)

    async def async_close_cover(self, **kwargs):
        self._manual_stop = False
        if self._digital:
            self._hub.set_digital(self._close_full_join, 1)
            await asyncio.sleep(0.2)
            self._hub.set_digital(self._close_full_join, 0)
        else:
            self._hub.set_analog(self._pos_join, 0)

    async def async_stop_cover(self, **kwargs):
        self._manual_stop = True
        self._hub.set_digital(self._stop_join, 1)
        await asyncio.sleep(0.2)
        self._hub.set_digital(self._stop_join, 0)
