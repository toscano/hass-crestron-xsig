"""Platform for Crestron Media Player integration."""

import asyncio
import logging
import math

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_MUTE_JOIN,
    CONF_OFF_JOIN,
    CONF_ON_JOIN,
    CONF_SOURCE_NUM_JOIN,
    CONF_SOURCES,
    CONF_VOLUME_DOWN_JOIN,
    CONF_VOLUME_JOIN,
    CONF_VOLUME_UP_JOIN,
    DOMAIN,
    HUB,
)

_LOGGER = logging.getLogger(__name__)

SOURCES_SCHEMA = vol.Schema(
    {
        cv.positive_int: cv.string,
    }
)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_MUTE_JOIN): cv.positive_int,
        vol.Required(CONF_SOURCE_NUM_JOIN): cv.positive_int,
        vol.Required(CONF_VOLUME_UP_JOIN): cv.positive_int,
        vol.Required(CONF_VOLUME_DOWN_JOIN): cv.positive_int,
        vol.Required(CONF_OFF_JOIN): cv.positive_int,
        vol.Required(CONF_VOLUME_JOIN): cv.positive_int,
        vol.Required(CONF_ON_JOIN): cv.positive_int,
        vol.Required(CONF_SOURCES): SOURCES_SCHEMA,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronRoom(hub, config)]
    async_add_entities(entity)


class CrestronRoom(MediaPlayerEntity):
    def __init__(self, hub, config):
        self._hub = hub
        self._name = config.get(CONF_NAME)
        self._device_class = "speaker"
        self._supported_features = (
            MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )
        self._mute_join = config.get(CONF_MUTE_JOIN)
        self._volume_up_join = config.get(CONF_VOLUME_UP_JOIN)
        self._volume_down_join = config.get(CONF_VOLUME_DOWN_JOIN)
        self._volume_level_join = config.get(CONF_VOLUME_JOIN)
        self._source_number_join = config.get(CONF_SOURCE_NUM_JOIN)
        self._sources = config.get(CONF_SOURCES)
        self._off_join = config.get(CONF_OFF_JOIN)
        self._on_join = config.get(CONF_ON_JOIN)

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
        return "media-player-" + str(self._source_number_join)

    @property
    def should_poll(self):
        return False

    @property
    def device_class(self):
        return self._device_class

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def state(self):
        if self._hub.get_digital(self._off_join) == 0:
            return STATE_OFF
        else:
            return STATE_ON

    @property
    def is_volume_muted(self):
        return self._hub.get_digital(self._mute_join)

    @property
    def volume_level(self):
        _LOGGER.info("Volume is: %s", self._hub.get_analog(self._volume_level_join))
        return self._hub.get_analog(self._volume_level_join) / 65535

    async def async_mute_volume(self, mute):
        if mute:
            self._hub.set_digital(self._mute_join, 1)
        else:
            self._hub.set_digital(self._mute_join, 0)

    @property
    def source_list(self):
        return list(self._sources.values())

    @property
    def source(self):
        source_num = self._hub.get_analog(self._source_number_join)
        _LOGGER.info("Source number: %s", source_num)
        if source_num == 0:
            return None
        else:
            return self._sources.get(source_num, None)

    async def async_select_source(self, source):
        for input_num, name in self._sources.items():
            _LOGGER.info("Input: %s %s", input_num, name)
            if name == source:
                self._hub.set_analog(self._source_number_join, int(input_num))

    async def async_set_volume_level(self, volume):
        _LOGGER.info("Volume: %s %s", volume)
        return self._hub.set_analog(self._volume_level_join, math.ceil(volume * 65535))

    async def async_turn_on(self):
        self._hub.set_digital(self._on_join, 1)

    async def async_turn_off(self):
        self._hub.set_digital(self._off_join, 1)
        await asyncio.sleep(0.05)
        self._hub.set_digital(self._off_join, 0)

    async def async_volume_up(self):
        self._hub.set_digital(self._volume_up_join, 1)
        await asyncio.sleep(0.05)
        self._hub.set_digital(self._volume_up_join, 0)

    async def async_volume_down(self):
        self._hub.set_digital(self._volume_down_join, 1)
        await asyncio.sleep(0.05)
        self._hub.set_digital(self._volume_down_join, 0)
