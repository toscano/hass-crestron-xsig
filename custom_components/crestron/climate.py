"""Platform for Crestron Thermostat integration."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_IDLE,
    FAN_ON,
    FAN_AUTO,
)

from homeassistant.const import CONF_NAME

from .const import (
    HUB,
    DOMAIN,
    CONF_HEAT_SP_JOIN,
    CONF_COOL_SP_JOIN,
    CONF_REG_TEMP_JOIN,
    CONF_MODE_HEAT_JOIN,
    CONF_MODE_COOL_JOIN,
    CONF_MODE_AUTO_JOIN,
    CONF_MODE_OFF_JOIN,
    CONF_FAN_ON_JOIN,
    CONF_FAN_AUTO_JOIN,
    CONF_H1_JOIN,
    CONF_H2_JOIN,
    CONF_C1_JOIN,
    CONF_C2_JOIN,
    CONF_FA_JOIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_HEAT_SP_JOIN): cv.positive_int,
        vol.Optional(CONF_COOL_SP_JOIN): cv.positive_int,
        vol.Optional(CONF_REG_TEMP_JOIN): cv.positive_int,
        vol.Optional(CONF_MODE_HEAT_JOIN): cv.positive_int,
        vol.Optional(CONF_MODE_COOL_JOIN): cv.positive_int,
        vol.Optional(CONF_MODE_AUTO_JOIN): cv.positive_int,
        vol.Optional(CONF_MODE_OFF_JOIN): cv.positive_int,
        vol.Optional(CONF_FAN_ON_JOIN): cv.positive_int,
        vol.Optional(CONF_FAN_AUTO_JOIN): cv.positive_int,
        vol.Optional(CONF_H1_JOIN): cv.positive_int,
        vol.Optional(CONF_H2_JOIN): cv.positive_int,
        vol.Optional(CONF_C1_JOIN): cv.positive_int,
        vol.Optional(CONF_C2_JOIN): cv.positive_int,
        vol.Optional(CONF_FA_JOIN): cv.positive_int,
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    hub = hass.data[DOMAIN][HUB]
    entity = [CrestronThermostat(hub, config, hass.config.units.temperature_unit)]
    async_add_entities(entity)


class CrestronThermostat(ClimateEntity):
    def __init__(self, hub, config, unit):
        self._hub = hub

        self._fans = []
        features = []
        if config[CONF_FAN_ON_JOIN]:
            self._fans.append(FAN_ON)
            features.append(SUPPORT_FAN_MODE)
        if config[CONF_FAN_AUTO_JOIN]:
            self._fans.append(FAN_AUTO)
            features.append(SUPPORT_FAN_MODE)
        if self._fans.__len__ == 0:
            self._fans = None

        self._hvac_modes = []
        if config[CONF_MODE_HEAT_JOIN]:
            self._hvac_modes.append(HVAC_MODE_HEAT)
            features.append(SUPPORT_TARGET_TEMPERATURE)
        if config[CONF_MODE_COOL_JOIN]:
            self._hvac_modes.append(HVAC_MODE_COOL)
            features.append(SUPPORT_TARGET_TEMPERATURE)
        if config[CONF_MODE_AUTO_JOIN]:
            self._hvac_modes.append(HVAC_MODE_HEAT_COOL)
            features.append(SUPPORT_TARGET_TEMPERATURE_RANGE)
        if config[CONF_MODE_OFF_JOIN]:
            self._hvac_modes.append(HVAC_MODE_OFF)
        if self._hvac_modes.__len__ == 0:
            self._hvac_modes = None

        deuplicated_features = list(set(features))
        if deuplicated_features.__len__ > 0:
            for deuplicated_feature in deuplicated_features:
                self._supported_features = (
                    self._supported_features | deuplicated_feature
                )
        else:
            self._supported_features = None

        self._should_poll = False
        self._temperature_unit = unit

        self._name = config[CONF_NAME]
        self._heat_sp_join = config[CONF_HEAT_SP_JOIN]
        self._cool_sp_join = config[CONF_COOL_SP_JOIN]
        self._reg_temp_join = config[CONF_REG_TEMP_JOIN]
        self._mode_heat_join = config[CONF_MODE_HEAT_JOIN]
        self._mode_cool_join = config[CONF_MODE_COOL_JOIN]
        self._mode_auto_join = config[CONF_MODE_AUTO_JOIN]
        self._mode_off_join = config[CONF_MODE_OFF_JOIN]
        self._fan_on_join = config[CONF_FAN_ON_JOIN]
        self._fan_auto_join = config[CONF_FAN_AUTO_JOIN]
        self._h1_join = config[CONF_H1_JOIN]
        self._h2_join = config.get(CONF_H2_JOIN)
        self._c1_join = config[CONF_C1_JOIN]
        self._c2_join = config.get(CONF_C2_JOIN)
        self._fa_join = config[CONF_FA_JOIN]

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
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def fan_modes(self):
        return self._fan_modes

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def should_poll(self):
        return self._should_poll

    @property
    def temperature_unit(self):
        return self._temperature_unit

    @property
    def current_temperature(self):
        return self._hub.get_analog(self._reg_temp_join) / 10

    @property
    def target_temperature(self):
        if self._heat_sp_join is not None and self.hvac_mode == HVAC_MODE_HEAT:
            return self._hub.get_analog(self._heat_sp_join) / 10
        if self._cool_sp_join is not None and self.hvac_mode == HVAC_MODE_COOL:
            return self._hub.get_analog(self._heat_sp_join) / 10
        return None

    @property
    def target_temperature_high(self):
        if self._cool_sp_join is not None:
            return self._hub.get_analog(self._cool_sp_join) / 10
        return None

    @property
    def target_temperature_low(self):
        if self._heat_sp_join is not None:
            return self._hub.get_analog(self._heat_sp_join) / 10
        return None

    @property
    def hvac_mode(self):
        if self._mode_auto_join is not None and self._hub.get_digital(
            self._mode_auto_join
        ):
            return HVAC_MODE_HEAT_COOL
        if self._mode_heat_join is not None and self._hub.get_digital(
            self._mode_heat_join
        ):
            return HVAC_MODE_HEAT
        if self._mode_cool_join is not None and self._hub.get_digital(
            self._mode_cool_join
        ):
            return HVAC_MODE_COOL
        if self._mode_off_join is not None and self._hub.get_digital(
            self._mode_off_join
        ):
            return HVAC_MODE_OFF
        return HVAC_MODE_OFF

    @property
    def fan_mode(self):
        if self._hub.get_digital(self._fan_auto_join):
            return FAN_AUTO
        if self._hub.get_digital(self._fan_on_join):
            return FAN_ON
        return None

    @property
    def hvac_action(self):
        if (self._h1_join is not None and self._hub.get_digital(self._h1_join)) or (
            self._h2_join is not None and self._hub.get_digital(self._h2_join)
        ):
            return CURRENT_HVAC_HEAT
        if (self._c1_join is not None and self._hub.get_digital(self._c1_join)) or (
            self._c2_join is not None and self._hub.get_digital(self._c2_join)
        ):
            return CURRENT_HVAC_COOL

        return CURRENT_HVAC_IDLE

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_HEAT_COOL:
            if self._mode_auto_join is not None:
                self._hub.set_digital(self._mode_auto_join, True)
            if self._mode_cool_join is not None:
                self._hub.set_digital(self._mode_cool_join, False)
            if self._mode_off_join is not None:
                self._hub.set_digital(self._mode_off_join, False)
            if self._mode_heat_join is not None:
                self._hub.set_digital(self._mode_heat_join, False)
        if hvac_mode == HVAC_MODE_HEAT:
            if self._mode_auto_join is not None:
                self._hub.set_digital(self._mode_auto_join, False)
            if self._mode_cool_join is not None:
                self._hub.set_digital(self._mode_cool_join, False)
            if self._mode_off_join is not None:
                self._hub.set_digital(self._mode_off_join, False)
            if self._mode_heat_join is not None:
                self._hub.set_digital(self._mode_heat_join, True)
        if hvac_mode == HVAC_MODE_COOL:
            if self._mode_auto_join is not None:
                self._hub.set_digital(self._mode_auto_join, False)
            if self._mode_cool_join is not None:
                self._hub.set_digital(self._mode_cool_join, True)
            if self._mode_off_join is not None:
                self._hub.set_digital(self._mode_off_join, False)
            if self._mode_heat_join is not None:
                self._hub.set_digital(self._mode_heat_join, False)
        if hvac_mode == HVAC_MODE_OFF:
            if self._mode_auto_join is not None:
                self._hub.set_digital(self._mode_auto_join, False)
            if self._mode_cool_join is not None:
                self._hub.set_digital(self._mode_cool_join, False)
            if self._mode_off_join is not None:
                self._hub.set_digital(self._mode_off_join, True)
            if self._mode_heat_join is not None:
                self._hub.set_digital(self._mode_heat_join, False)

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == FAN_AUTO:
            if self._fan_on_join is not None:
                self._hub.set_digital(self._fan_on_join, False)
            if self._fan_auto_join is not None:
                self._hub.set_digital(self._fan_auto_join, True)
        if fan_mode == FAN_ON:
            if self._fan_on_join is not None:
                self._hub.set_digital(self._fan_on_join, True)
            if self._fan_auto_join is not None:
                self._hub.set_digital(self._fan_auto_join, False)

    async def async_set_temperature(self, **kwargs):
        if self._heat_sp_join is not None:
            self._hub.set_analog(
                self._heat_sp_join, int(kwargs["target_temp_low"]) * 10
            )
        if self._cool_sp_join is not None:
            self._hub.set_analog(
                self._cool_sp_join, int(kwargs["target_temp_high"]) * 10
            )
