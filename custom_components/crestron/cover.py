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
    CONF_IS_OPENED_JOIN,
    CONF_IS_CLOSING_JOIN,
    CONF_IS_CLOSED_JOIN,
    CONF_STOP_JOIN,
    CONF_POS_JOIN,
    CONF_IS_MOVING_JOIN,
    CONF_OPEN_FULL_JOIN,
    CONF_CLOSE_FULL_JOIN,
    CONF_MAIN_ENGINE_JOIN,
    CONF_IR_SENSOR_JOIN,
    CONF_UP_SET_JOIN,
    CONF_UP_RESET_JOIN,
    CONF_DOWN_SET_JOIN,
    CONF_DOWN_RESET_JOIN
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TYPE): vol.In(["analog_shade", "digital_shade", "digital_curtain", "elevator"]),
        vol.Required(CONF_IS_OPENING_JOIN): cv.positive_int,
        vol.Required(CONF_IS_CLOSING_JOIN): cv.positive_int,
        vol.Optional(CONF_STOP_JOIN): cv.positive_int,
        vol.Optional(CONF_IS_MOVING_JOIN): cv.positive_int,
        vol.Optional(CONF_IS_CLOSED_JOIN): cv.positive_int,
        vol.Optional(CONF_IS_OPENED_JOIN): cv.positive_int,
        vol.Optional(CONF_POS_JOIN): cv.positive_int,    
        vol.Optional(CONF_OPEN_FULL_JOIN): cv.positive_int,
        vol.Optional(CONF_CLOSE_FULL_JOIN): cv.positive_int,
        vol.Optional(CONF_MAIN_ENGINE_JOIN): cv.positive_int,
        vol.Optional(CONF_IR_SENSOR_JOIN): cv.positive_int
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    if config.get(CONF_TYPE) == 'elevator':
        # Elevators can be modeled as covers but their implementation
        # is much different than other shades hence they have their own class
        entity = [CrestronElevator(hub, config)]
    else:
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

class CrestronElevator(CoverEntity):
    def __init__(self, hub, config):
        self._hub = hub
        self._type = config.get(CONF_TYPE)
        self._supported_features = (
            SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
        )
        self._should_poll = False

        self._name = config.get(CONF_NAME)
        # Join for detecting moving elevator UP
        self._is_opening_join = config.get(CONF_IS_OPENING_JOIN)
        # Join for detecting elevator is UP
        self._is_opened_join = config.get(CONF_IS_OPENED_JOIN)
        # Join for SET-ing the elevator to UP
        self._up_set_join = config.get(CONF_UP_SET_JOIN)
        # Join for RESET-ing the elevator from UP
        # instead of a single switch (up/down)
        self._up_reset_join = config.get(CONF_UP_RESET_JOIN)
        # Join for detecting moving elevator DOWN
        self._is_closing_join = config.get(CONF_IS_CLOSING_JOIN)
        # Join for detecting elevator is DOWN
        self._is_closed_join = config.get(CONF_IS_CLOSED_JOIN)
        # Join for main engine
        self._down_set_join = config.get(CONF_DOWN_SET_JOIN)
        # Join for RESET-ing the elevator from DOWN
        # instead of a single switch (up/down)
        self._down_reset_join = config.get(CONF_DOWN_RESET_JOIN)
        self._main_engine_join = config.get(CONF_MAIN_ENGINE_JOIN)        
        # Join for IR sensor
        # Safety logic (i.e. stopping on detection) is handled by Crestron
        self._ir_sensor_join = config.get(CONF_IR_SENSOR_JOIN)

    async def async_added_to_hass(self):
        self._hub.register_callback(self.process_callback)

    async def async_will_remove_from_hass(self):
        self._hub.remove_callback(self.process_callback)

    async def process_callback(self, cbtype, value):
        self.async_write_ha_state()

    @property
    def unique_id(self):
       return 'elevator-' + str(self._is_opening_join) + str(self._is_closing_join)
       
    @property
    def available(self):
        return self._hub.is_available()

    @property
    def name(self):
        return self._name

    @property
    def device_class(self):
        # Custom class, does not match any existing device classes
        return None

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def should_poll(self):
        return self._should_poll

    @property
    def is_opening(self):
        return self._hub.get_digital(self._is_opening_join) and self._hub.get_digital(self._main_engine_join)

    @property
    def is_closing(self):
        return self._hub.get_digital(self._is_closing_join) and self._hub.get_digital(self._main_engine_join)
        
    @property
    def is_closed(self):
        if self._hub.get_digital(self._is_closed_join):
            return True
        elif self._hub.get_digital(self._is_opened_join):
            return False
        else:
            return None

    @property
    def icon(self):
        if self._hub.get_digital(self._is_closed_join):
            # Elevator is down
            return "mdi:home-floor-negative-1"
        elif self._hub.get_digital(self._is_opened_join):
            # Elevator is up
            return "mdi:home-floor-0"
        elif self._hub.get_digital(self._is_closing_join) and self._hub.get_digital(self._main_engine_join):
            # Elevator is moving down
            return "mdi:arrow-down-box"
        elif self._hub.get_digital(self._is_opening_join) and self._hub.get_digital(self._main_engine_join):
            # Elevator is moving up
            return "mdi:arrow-up-box"
        else:
            # Unknown state (most likely stopped halfway)
            return "mdi:help-box"

    async def async_open_cover(self, **kwargs):
        # Elevator going UP
        if not self._hub.get_digital(self._ir_sensor_join):
            # Check if UP is ON
            if not self._hub.get_digital(self._is_opening_join):
                # SET UP
                self._hub.set_digital(self._up_set_join, 1)
                await asyncio.sleep(0.05)
                self._hub.set_digital(self._up_set_join, 0)
            # Check if DOWN is OFF
            if self._hub.get_digital(self._is_closing_join):
                # RESET DOWN
                self._hub.set_digital(self._down_reset_join, 1)
                await asyncio.sleep(0.05)
                self._hub.set_digital(self._down_reset_join, 0)
            # Check if main engine is ON
            if not self._hub.get_digital(self._main_engine_join):
                self._hub.set_digital(self._main_engine_join, 1)
                await asyncio.sleep(0.05)
                self._hub.set_digital(self._main_engine_join, 0)

    async def async_close_cover(self, **kwargs):
        # Elevator going DOWN
        if not self._hub.get_digital(self._ir_sensor_join):
            # Check if UP is OFF
            if self._hub.get_digital(self._is_opening_join):
                # RESET UP
                self._hub.set_digital(self._up_reset_join, 1)
                await asyncio.sleep(0.05)
                self._hub.set_digital(self._up_reset_join, 0)
            # Check if DOWN is ON
            if not self._hub.get_digital(self._is_closing_join):
                # SET DOWN
                self._hub.set_digital(self._down_set_join, 1)
                await asyncio.sleep(0.05)
                self._hub.set_digital(self._down_set_join, 0)
            # Check if main engine is ON
            if not self._hub.get_digital(self._main_engine_join):
                self._hub.set_digital(self._main_engine_join, 1)
                await asyncio.sleep(0.05)
                self._hub.set_digital(self._main_engine_join, 0)

    async def async_stop_cover(self, **kwargs):
        if self._hub.get_digital(self._main_engine_join):
            # Turn off engine
            self._hub.set_digital(self._main_engine_join, 1)
            await asyncio.sleep(0.05)
            self._hub.set_digital(self._main_engine_join, 0)
        # Check if UP is OFF
        if self._hub.get_digital(self._is_opening_join):
            # RESET UP
            self._hub.set_digital(self._up_reset_join, 1)
            await asyncio.sleep(0.05)
            self._hub.set_digital(self._up_reset_join, 0)
        # Check if DOWN is OFF
        if self._hub.get_digital(self._is_closing_join):
            # RESET DOWN
            self._hub.set_digital(self._down_reset_join, 1)
            await asyncio.sleep(0.05)
            self._hub.set_digital(self._down_reset_join, 0)
