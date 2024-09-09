"""Platform for Crestron Thermostat integration."""

import voluptuous as vol
import logging

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntityFeature, ClimateEntity
from homeassistant.components.climate.const import (
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
    CONF_PULSED,
    CONF_DIVISOR,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_PULSED): cv.boolean,
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
        vol.Optional(CONF_DIVISOR): int,
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

        self._pulsed = config.get(CONF_PULSED, False)
        self._divisor = config.get(CONF_DIVISOR, 1)

        self._fan_modes = []
        features = [ClimateEntityFeature.TURN_OFF, ClimateEntityFeature.TURN_ON]
        if config.get(CONF_FAN_ON_JOIN):
            self._fan_modes.append(FAN_ON)
            features.append(ClimateEntityFeature.FAN_MODE)
        if config.get(CONF_FAN_AUTO_JOIN):
            self._fan_modes.append(FAN_AUTO)
            features.append(ClimateEntityFeature.FAN_MODE)
        if len(self._fan_modes) == 0:
            self._fan_modes = None

        self._hvac_modes = []
        if config.get(CONF_MODE_HEAT_JOIN):
            self._hvac_modes.append(HVAC_MODE_HEAT)
            features.append(ClimateEntityFeature.TARGET_TEMPERATURE)
        if config.get(CONF_MODE_COOL_JOIN):
            self._hvac_modes.append(HVAC_MODE_COOL)
            features.append(ClimateEntityFeature.TARGET_TEMPERATURE)
        if config.get(CONF_MODE_AUTO_JOIN):
            self._hvac_modes.append(HVAC_MODE_HEAT_COOL)
            features.append(ClimateEntityFeature.TARGET_TEMPERATURE_RANGE)
        if config.get(CONF_MODE_OFF_JOIN):
            self._hvac_modes.append(HVAC_MODE_OFF)
        if len(self._hvac_modes) == 0:
            self._hvac_modes = None

        self._supported_features = None
        deuplicated_features = list(set(features))
        for deuplicated_feature in deuplicated_features:
            if self._supported_features is None:
                self._supported_features = deuplicated_feature
            else:
                self._supported_features = (
                    self._supported_features | deuplicated_feature
                )

        self._should_poll = False
        self._temperature_unit = unit

        self._name = config.get(CONF_NAME)
        self._heat_sp_join = config.get(CONF_HEAT_SP_JOIN)
        self._cool_sp_join = config.get(CONF_COOL_SP_JOIN)
        self._reg_temp_join = config.get(CONF_REG_TEMP_JOIN)
        self._mode_heat_join = config.get(CONF_MODE_HEAT_JOIN)
        self._mode_cool_join = config.get(CONF_MODE_COOL_JOIN)
        self._mode_auto_join = config.get(CONF_MODE_AUTO_JOIN)
        self._mode_off_join = config.get(CONF_MODE_OFF_JOIN)
        self._fan_on_join = config.get(CONF_FAN_ON_JOIN)
        self._fan_auto_join = config.get(CONF_FAN_AUTO_JOIN)
        self._h1_join = config.get(CONF_H1_JOIN)
        self._h2_join = config.get(CONF_H2_JOIN)
        self._c1_join = config.get(CONF_C1_JOIN)
        self._c2_join = config.get(CONF_C2_JOIN)
        self._fa_join = config.get(CONF_FA_JOIN)

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
    def unique_id(self):
        return "climate-" + str(self.name)

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
        return self._hub.get_analog(self._reg_temp_join) / self._divisor

    @property
    def target_temperature(self):
        if self._heat_sp_join is not None and self.hvac_mode == HVAC_MODE_HEAT:
            return self._hub.get_analog(self._heat_sp_join) / self._divisor
        if self._cool_sp_join is not None and self.hvac_mode == HVAC_MODE_COOL:
            return self._hub.get_analog(self._heat_sp_join) / self._divisor
        return None

    @property
    def target_temperature_high(self):
        if self._cool_sp_join is not None:
            return self._hub.get_analog(self._cool_sp_join) / self._divisor
        return None

    @property
    def target_temperature_low(self):
        if self._heat_sp_join is not None:
            return self._hub.get_analog(self._heat_sp_join) / self._divisor
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

        if self._mode_off_join is not None and self._hub.get_digital(
            self._mode_off_join
        ):
            return CURRENT_HVAC_OFF
        return CURRENT_HVAC_IDLE

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_HEAT_COOL:
            if self._mode_auto_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_auto_join, True, self._pulsed
                )
            if self._mode_cool_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_cool_join, False, self._pulsed
                )
            if self._mode_off_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_off_join, False, self._pulsed
                )
            if self._mode_heat_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_heat_join, False, self._pulsed
                )
        if hvac_mode == HVAC_MODE_HEAT:
            if self._mode_auto_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_auto_join, False, self._pulsed
                )
            if self._mode_cool_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_cool_join, False, self._pulsed
                )
            if self._mode_off_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_off_join, False, self._pulsed
                )
            if self._mode_heat_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_heat_join, True, self._pulsed
                )
        if hvac_mode == HVAC_MODE_COOL:
            if self._mode_auto_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_auto_join, False, self._pulsed
                )
            if self._mode_cool_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_cool_join, True, self._pulsed
                )
            if self._mode_off_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_off_join, False, self._pulsed
                )
            if self._mode_heat_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_heat_join, False, self._pulsed
                )
        if hvac_mode == HVAC_MODE_OFF:
            if self._mode_auto_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_auto_join, False, self._pulsed
                )
            if self._mode_cool_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_cool_join, False, self._pulsed
                )
            if self._mode_off_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_off_join, True, self._pulsed
                )
            if self._mode_heat_join is not None:
                await self._hub.set_digital_helper(
                    self._mode_heat_join, False, self._pulsed
                )

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == FAN_AUTO:
            if self._fan_on_join is not None:
                await self._hub.set_digital_helper(
                    self._fan_on_join, False, self._pulsed
                )
            if self._fan_auto_join is not None:
                await self._hub.set_digital_helper(
                    self._fan_auto_join, True, self._pulsed
                )
        if fan_mode == FAN_ON:
            if self._fan_on_join is not None:
                await self._hub.set_digital_helper(
                    self._fan_on_join, True, self._pulsed
                )
            if self._fan_auto_join is not None:
                await self._hub.set_digital_helper(
                    self._fan_auto_join, False, self._pulsed
                )

    async def async_set_temperature(self, **kwargs):
        if self._heat_sp_join is not None:
            self._hub.set_analog(
                self._heat_sp_join, int(kwargs["target_temp_low"]) * self._divisor
            )
        if self._cool_sp_join is not None:
            self._hub.set_analog(
                self._cool_sp_join, int(kwargs["target_temp_high"]) * self._divisor
            )
