# home-assistant-crestron-component

Integration for Home Assistant for the Crestron XSIG symbol

> **A note about AI contribution to this project.** Anthropic's Claude has been used as a development assistant. Every contribution (AI or otherwise) is reviewed and tested on _real hardware_ by an experienced meat-and-bones developer with too many years of experience. Any contribution made by Claude, or any AI agent, will always be noted in the commit message with co-author attribution.

Currently supported devices:

- Lights (dimmed or switched)
- Thermostats
- Shades, Curtains and Elevators
- Binary Sensor
- Sensor
- Switch
- Media Player
- Button (virtual)

## Adding the component to Home Assistant

- Add the `crestron` directory to `config/custom_components`
- Add the appropriate sections to `configuration.yaml` (see below)
- Add a `crestron:` block to the root of your `configuration.yaml`
  - The component acts as a TCP server, so you must specify the port number to listen on using the `port:` parameter.
- Restart Home Assistant

## On the control system

- Add a TCP/IP Client device to the control system
- Configure the client device with the IP address of Home Assistant
- Set the port number on the TCP/IP client symbol to match what you have configured for `port:` in `configuration.yaml`
- Wire up logic to the `Connect` signal of your TCP/IP client (or just set it to `1` to have it connected all the time)
- Add an "Intersystem Communication" symbol (quick key = xsig).
- Connect the TX & RX of the XSIG symbol to the TCP/IP Client.
- Attach your Analog, Serial and Digital signals to the input/output joins.
  - Note you can use multiple XSIGs attached to the same TCP/IP Client serials.  I found its simplest to use one for digitals and one for analogs/serials to keep the numbering simpler (see below).

> Caution: Join numbers can be confusing when mixing analog/serials and digitals on the same XSIG symbol.  Even though the symbol starts numbering the digitals at "1", the XSIG will actually send the join number corresponding to where the signal appears sequentially in the entire list of signals.
> For example, if you have 25 analog signals followed by 10 digital signals attached to the same XSIG, the digitals will be sent as 26-35, even though they are labeled 1 - 10 on the symbol.  You can either account for this in your configuration on the HA side, or just use one symbol for Analogs and another for Digitals.
> Since the XSIG lets you combine Analog/Serial joins on the same symbol, you can have one XSIG for Analog/Serial joins and another for digitals.  This keeps the join numbering simple.

## Home Assistant configuration.yaml

The `crestron:` entry is mandatory as is the `port:` definition under it.  So at a minimum, you will need:

```yaml
crestron:
  port: 16384
```

Then, if you want to make use of the control surface (touch panels/keypads) syncing capability, you will need to add either a `to_joins`, a `from_joins` section, or both (see below).

Finally, add entries for each HA component/platform type to your configuration.yaml for the appropriate entity type in Home Assistant:

| Crestron Device                                | Home Assistant component type |
|------------------------------------------------|-------------------------------|
| Light                                          | light                         |
| Thermostat                                     | climate                       |
| Shades / Curtains / Elevators                  | cover                         |
| read-only Digital Join                         | binary_sensor                 |
| read-only Analog Join                          | sensor                        |
| read-write Digital Join                        | switch                        |
| Audio/Video Switcher                           | media_player                  |
| read-write Digital Join<br/>(for writing only) | button                        |

>To be clear: if you configure multiple platforms (light, cover, climate, ...) plus synchronization in both directions, your configuration.yaml will look something like:

```yaml
crestron:
  port: 32768
  to_joins:
  ...
  from_joins:
  ...
light:
  - platform: crestron
  ...
climate:
  - platform: crestron
  ...
cover:
  - platform: crestron
  ...
binary_sensor:
  - platform: crestron
  ...
sensor:
  - platform: crestron
  ...
switch:
  - platform: crestron
  ...
media_player:
  - platform: crestron
  ...
button:
  - platform: crestron
  ...
```

In the sections below, every entity takes a _name_ parameter.  The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.

### Lights

This platform supports monochromatic "brightness" type lights (basically, anything that can have its brightness represented by an analog join on the control system).  I tested this with a CLX-1DIM8 panel and multiple CLW-DIMEX switches.
Also there is support for lights that are switched (no brightness setting).

```yaml
light:
  - platform: crestron
    name: "Dummy Light"
    join: 9
    type: brightness
```

- _join_: (required) If light supports brightness: the analog join on the XSIG symbol that represents the light's brightness. If not: the digital join on the XSIG symbol that represents the light's state.
- _type_: (required) ```brightness``` or ```onoff```

`brightness` lights support the Home Assistant `transition` parameter.  Transitions are performed by Home Assistant, which steps the analog join 20 times per second for the duration of the transition.  Turning a `brightness` light on or off without an explicit `transition` uses a 2 second transition.

>Note: `onoff` lights are driven by a _pulse_ — the digital join is raised and dropped again 50ms later — and only when the light is not already in the requested state.  Your control system logic must treat the join as a toggle.

### Thermostat

This platform should work with anything that looks like a CHV-TSTAT/THSTAT (analog joins for heat, cooling setpoints, digital joins for modes, fan modes, and relay states).  I tested this with multiple CHV-TSTAT and CHV-THSTATs.

>TODO: Add support for humidity control on CHV_THSTAT.

```yaml
climate:
  - platform: crestron
    name: "Upstairs Thermostat"
    divisor: 10
    pulsed: False
    heat_sp_join: 2
    cool_sp_join: 3
    reg_temp_join: 4
    mode_heat_join: 1
    mode_cool_join: 2
    mode_auto_join: 3
    mode_off_join: 4
    fan_on_join: 5
    fan_auto_join: 6
    h1_join: 7
    h2_join: 8
    c1_join: 9
    c2_join: 11
    fa_join: 10
```

Every join below is optional.  The set of joins you configure determines which capabilities the entity advertises to Home Assistant: configuring `mode_heat_join` and/or `mode_cool_join` enables a target temperature, `mode_auto_join` enables a target temperature _range_, and configuring either fan join enables fan mode selection.  Omit the joins your thermostat does not have.

- _divisor_: (optional, default 1) number to divide analog temperature joins by (and multiply setpoints by when writing).  A Crestron thermostat that reports tenths of a degree (754 = 75.4&deg;) needs `10`.
- _pulsed_: (optional, default False) set to True if the mode and fan mode joins are driven by momentary pulses rather than held levels.  See [Pulsed vs. held joins](#pulsed-vs-held-joins).
- _heat_sp_join_: analog join that represents the heat setpoint
- _cool_sp_join_: analog join that represents the cool setpoint
- _reg_temp_join_: analog join that represents the room temperature read by the thermostat.  The CHV-TSTAT calls this the "regulation temperature" because it my be derived from averaging a bunch of room temperature sensors.  This is so called because it is the temperature used by the thermostat to decide when to make calls for heating or cooling.
- _mode_heat_join_: digital join that is high when the thermostat is in heating mode
- _mode_cool_join_: digital join that is high when the thermostat is in cooling mode
- _mode_auto_join_: digital join that is high when the thermostat is in auto mode
- _mode_off_join_: digital join that is high when the thermostat mode is set to off
- _fan_on_join_: digital join that is high when the thermostat fan mode is set to (always) on
- _fan_auto_join_: digital join that is high when the thermostat fan mode is set to auto
- _h1_join_: digital feedback (read-only) join that represents the state of the stage 1 heat relay
- _h2_join_: digital feedback (read-only) join that represents the state of the stage 2 heat relay
- _c1_join_: digital feedback (read-only) join that represents the state of the stage 1 cool relay
- _c2_join_: digital feedback (read-only) join that represents the state of the stage 2 cool relay
- _fa_join_: digital feedback (read-only) join that represents the state of the stage fan relay

>Note: the mode and fan mode joins are read-_write_.  Changing the HVAC mode or fan mode from Home Assistant sets the join for the selected mode high and the joins for the other modes low.  Only the relay joins (`h1`/`h2`/`c1`/`c2`/`fa`) are purely feedback; they drive the "heating"/"cooling"/"idle" action shown in the UI.

### Shades, Curtains and Elevators

The `cover` platform covers four different kinds of device, selected with the required `type:` parameter:

| `type:`           | For                                                       | Home Assistant device class |
|-------------------|-----------------------------------------------------------|-----------------------------|
| `analog_shade`    | Shades positioned by an analog join (e.g. CSM-QMTDC)      | shade                       |
| `digital_shade`   | Shades driven by open/close/stop pulses only              | shade                       |
| `digital_curtain` | As `digital_shade`, but presented as a curtain            | curtain                     |
| `elevator`        | A two-position lift driven by set/reset joins             | (none)                      |

`name`, `type`, `is_opening_join` and `is_closing_join` are required for all four types.  Which of the remaining joins you need depends on the type.

#### `analog_shade`

```yaml
cover:
  - platform: crestron
    name: "Living Room Shades"
    type: analog_shade
    pos_join: 26
    is_opening_join: 41
    is_closing_join: 42
    stop_join: 43
    is_closed_join: 44
```

- _pos_join_: analog join that represents the shade position.  The value follows the typical definition for a Crestron analog shade (0 = closed, 65535 = open).
- _is_opening_join_: digital feedback (read-only) join that is high when shade is in the process of opening
- _is_closing_join_: digital feedback (read-only) join that is high when shade is in the process of closing
- _is_closed_join_: digital feedback (read-only) join that is high when shade is fully closed
- _stop_join_: digital join that is pulsed high to stop the shade opening/closing

Open and close set `pos_join` to 65535 and 0 respectively; setting a position from the UI writes `position * 655`.

#### `digital_shade` / `digital_curtain`

For shades that expose no position, only "go fully open", "go fully closed" and "stop".

```yaml
cover:
  - platform: crestron
    name: "Kitchen Curtain"
    type: digital_curtain
    is_opening_join: 51
    is_closing_join: 52
    is_moving_join: 53
    open_full_join: 54
    close_full_join: 55
    stop_join: 56
```

- _is_opening_join_: digital feedback (read-only) join that is high when the last/current direction of travel is open
- _is_closing_join_: digital feedback (read-only) join that is high when the last/current direction of travel is closed
- _is_moving_join_: digital feedback (read-only) join that is high while the motor is running.  This is combined with the direction joins to work out whether the cover is opening, closing or closed.
- _open_full_join_: digital join pulsed high (200ms) to drive the cover fully open
- _close_full_join_: digital join pulsed high (200ms) to drive the cover fully closed
- _stop_join_: digital join pulsed high (200ms) to stop the cover

>Note: after a manual stop the position is unknown, so the entity reports its state as unknown until the next full open or close.

#### `elevator`

Models a two-position lift (for example a TV lift) as a cover, where "open" = up and "closed" = down.  The up/down commands are latched with separate set and reset joins, and a main engine join actually starts the motor.  Safety logic is expected to live on the control system; this platform only refuses to issue a new movement command while the IR sensor join is high.

```yaml
cover:
  - platform: crestron
    name: "Media Room Lift"
    type: elevator
    is_opening_join: 61
    is_opened_join: 62
    is_closing_join: 63
    is_closed_join: 64
    up_set_join: 65
    up_reset_join: 66
    down_set_join: 67
    down_reset_join: 68
    main_engine_join: 69
    ir_sensor_join: 70
```

- _is_opening_join_: digital feedback (read-only) join that is high when the elevator is latched to travel up
- _is_opened_join_: digital feedback (read-only) join that is high when the elevator is fully up
- _is_closing_join_: digital feedback (read-only) join that is high when the elevator is latched to travel down
- _is_closed_join_: digital feedback (read-only) join that is high when the elevator is fully down
- _up_set_join_: digital join pulsed high to latch the direction to up
- _up_reset_join_: digital join pulsed high to clear the up latch
- _down_set_join_: digital join pulsed high to latch the direction to down
- _down_reset_join_: digital join pulsed high to clear the down latch
- _main_engine_join_: digital join pulsed high to start (and, from the stop command, to stop) the motor.  It is also read as feedback for whether the motor is running.
- _ir_sensor_join_: digital feedback (read-only) join that is high when the safety sensor is obstructed.  Open and close commands are ignored while it is high.

### Binary Sensor

This can represent any read-only digital signal on the control system.  I typically comment out the "in" signals on the XSIG symbol to keep the "in" and "out" signals lined up.

```yaml
binary_sensor:
  - platform: crestron
    name: "Air Compressor"
    is_on_join: 57
    device_class: power
    inverted: False
```

- _is_on_join_: (required) digital feedback (read-only) join to represent as a binary sensor in Home Assistant
- _device_class_: (required) any device class [supported by the binary_sensor](https://www.home-assistant.io/integrations/binary_sensor/) integration.  This mostly affects how the value will be expressed in various UIs.
- _inverted_: (optional, default False) set to True to report the sensor as on when the join is low.  Useful for normally-closed contacts.

### Sensor

This can represent any read-only analog signal on the control system.  I typically comment out the "in" signals on the XSIG symbol to keep the "in" and "out" signals lined up.  Remember that an analog join on the control system is a 16-bit value that can range from 0-65535.  So for many symbol types (especially those representing a brightness or percent) you will need to make use of the `divisor:` parameter.

```yaml
sensor:
  - platform: crestron
    name: "Outside Temperature"
    value_join: 1
    device_class: "temperature"
    unit_of_measurement: "F"
    divisor: 10
```

- _value_join_: (required) analog join to represent as a sensor in Home Assistant
- _device_class_: (required) any device class [supported by the sensor](https://www.home-assistant.io/integrations/sensor/) integration.  This mostly affects how the value will be expressed in various UIs.
- _unit_of_measurement_: (required) Unit of measurement appropriate for the device class as documented in the [developer docs](https://developers.home-assistant.io/docs/core/entity/sensor/).
- _divisor_: (optional, default 1) number to divide the analog join by to get the correct sensor value.  For example, a crestron temperature sensor returns tenths of a degree (754 represents 75.4 degrees), so you would use a divisor of 10.

>Note: `divisor` must be a whole number — a fractional value such as `655.35` is rejected by config validation.  To scale a 0-65535 join to a percent, use a `divisor` of `655` (accurate to within 0.1%) or leave the divisor at 1 and scale in a template sensor.

### Switch

This could represent any digital signal on the control system that you want to be able to control/view from HA.

```yaml
switch:
  - platform: crestron
    name: "Dummy Switch"
    switch_join: 65
    pulsed: False
    device_class: switch
```

- _switch_join_: (required) digital join to represent as a switch in Home Assistant
- _pulsed_: (required) indicates whether the switch is switched by a signal pulse, or that it switches by providing the requested state.  See [Pulsed vs. held joins](#pulsed-vs-held-joins).
- _device_class_: (optional, default `switch`) either `switch` or `outlet`.

### Media Player

Use media_player to represent the output of a multi-zone switcher.  For example a PAD-8A is an 8x8 (8 inputs x 8 outputs) audio switcher.  This can be represented by 8 media player components (one for each output).  The component supports power, source selection (input selection) and volume + mute control.  So it is modeled as a "speaker" media player type in Home Assistant.

This works rather nicely with the template media player integration to allow intuitive control of source devices connected to a multi-zone switcher like the PAD8A.

All of the joins below are required.

```yaml
media_player:
  - platform: crestron
    name: "Kitchen Speakers"
    on_join: 25
    off_join: 26
    mute_join: 27
    volume_join: 19
    volume_up_join: 28
    volume_down_join: 29
    source_number_join: 13
    sources:
      1: "Android TV"
      2: "Roku"
      3: "Apple TV"
      4: "Chromecast"
      7: "Volumio"
      8: "Crestron Streamer"
```

- _on_join_: digital join set high to turn the zone on.  This is not pulsed — the join is left high.
- _off_join_: digital join that serves double duty.  It is pulsed high to turn the zone off, and it is also the power feedback: the entity reports `on` while this join is high and `off` while it is low.
- _mute_join_: digital join that represents the mute state of the channel.  Note this is not a toggle. Both to and from the control system True = muted, False = not muted.  This might require some extra logic on the control system side if you only have logic that takes a toggle.
- _volume_join_: analog join that represents the volume of the channel (0-65535)
- _volume_up_join_: digital join pulsed high for a volume step up
- _volume_down_join_: digital join pulsed high for a volume step down
- _source_number_join_: analog join that represents the selected input for the output channel.  1 would correspond to input 1, 2 to input 2, and so on.  A value of 0 is reported to Home Assistant as no source selected.
- _sources_: a dictionary of _input_ to _name_ mappings.  The input number is the actual input (corresponding to the source_number_join) number, whereas the name will be shown in the UI when selecting inputs/sources.  So when a user selects the _name_ in the UI, the _source_number_join_ will be set to _input_.

### Button (virtual)

This represents action triggers in the control system caused by signal pulses on a digital join. These actions are triggered in Home Assistant by means of a virtual button.
For instance, a virtual button in a Crestron touch panel that triggers a sequence of events programmed in the control system (e.g. turning all lights off) can also be triggered by Home Assistant by means of a Button.

When a virtual button is pressed in Home Assistant, the associated digital join will change to HIGH and change to LOW 200ms later, generating a signal pulse that can be recognized by the control system as an event.

```yaml
button:
  - platform: crestron
    name: "Dummy Button"
    button_join: 70
```

- _button_join_: (required) digital join to represent as a button in Home Assistant

### Pulsed vs. held joins

Several platforms distinguish between a join that is _held_ at the requested state and one that is _pulsed_ to toggle it.  Which one you need depends on how the symbol on the control system is wired.

- **Held** (`pulsed: False`): Home Assistant writes the requested value to the join and leaves it there.  Turning the entity on sets the join high; turning it off sets it low.
- **Pulsed** (`pulsed: True`): Home Assistant raises the join and drops it again 50ms later, and only does so when the join is not already in the requested state.  Use this for symbols that take a toggle.

The `pulsed:` option is available on `switch` (required) and `climate` (optional, defaults to False).  The `light` platform's `onoff` type is always pulsed, and the pulse-driven joins on `cover`, `media_player` and `button` are always pulsed regardless of configuration.

### Control Surface Sync

If you have Crestron touch panels or keypads, it can be useful to keep certain feedback/display joins in sync with Home Assistant state and to be able to invoke Home Assistant functionality (via a script) when a button is pressed or a join changes.  This functionality was added with v0.2.  There are two directions to sync: from HA states to control system joins and from control system joins to HA (using scripts).

There are two sections in `configuration.yaml` under the root `crestron:` key:

- `to_joins` for syncing HA state to control system joins
- `from_joins` for invoking HA scripts when control system joins change

```yaml
crestron:
  port: 5555
  to_joins:
  ...
  from_joins:
  ...
```

#### From HA to the Control System

The `to_joins` section will list all the joins you want to map HA state changes to.  For each join, you list either:

- a simple `entity_id` with optional `attribute` to map entity state directly to a join.
- a `value_template` that lets you map almost any combination of state values (including the full power of [template logic](https://www.home-assistant.io/docs/configuration/templating/)) to the listed join.

```yaml
crestron:
  port: 12345
  ...
  to_joins:
    - join: d12
      entity_id: switch.compressor
    - join: a35
      value_template: "{{value|int * 10}}"
    - join: s4
      value_template: "Current weather conditions: {{state('weather.home')}}"
    - join: a2
      entity_id: media_player.kitchen
      attribute: volume_level
    - join: s4
      value_template: "http://homeassistant:8123{{ state_attr('media_player.volumio', 'entity_picture') }}"
```

- _to_joins_: begins the section
- _join_: for each join, list the join type and number.  The type prefix is 'a' for analog joins, 'd' for digital joins and 's' for serial joins.  So s32 would be serial join #32.  The value of this join will be set to either the state/attribute of the configured entity ID or the output of the configured template.
- _entity_id_: the entity ID to sync this join to.  If no _attribute_ is listed the join will be set to entity's state value whenever the state changes.
- _attribute_: use the listed attribute value for the join value instead of the entity's state.
- _value_template_: used instead of _entity_id_/_attribute_ if you need more flexibility on how to set the value (prefix/suffix or math operations) or even to set the join value based on multiple entity IDs/state values.  You have the full power of [HA templating](https://www.home-assistant.io/docs/configuration/templating/) to work with here.

>Note that when you specify an `entity_id`, all changes to that entity_id will result in a join update being sent to the control system.  When you specify a `value_template` a change to any referenced entity will trigger a join update.

also...

>For digital (`d`) joins, the resulting value must look like a boolean: `on`, `True`, `true`, `1` are sent as high and `off`, `False`, `false`, `0` as low.  Anything else (including `unavailable` or `unknown`) is ignored and the join is left at its previous value.  Serial (`s`) join values longer than 252 characters are dropped.

#### From Control System to HA

 The `from_joins` section will list all the joins you want to track from the control system.  When each join changes the configured functionality will be invoked.

 ```yaml
crestron:
  port: 54321
  ...
  from_joins:
    - join: a2
      script:
        service: input_text.set_value
        data:
          entity_id: input_text.test
          value: "Master BR temperature is {{value|int / 10}}"
    - join: d35
      script:
        service: media_player.media_previous_track
        data:
          entity_id: media_player.volumio
    - join: d36
      script:
        service: media_player.media_play_pause
        data:
          entity_id: media_player.volumio
    - join: d37
      script:
        service: media_player.media_next_track
        data:
          entity_id: media_player.volumio
    - join: d74
      script:
        service: media_player.select_source
        data:
          entity_id: media_player.volumio
          source: "{{state_attr('media_player.volumio', 'source_list')[0]}}"
    - join: d75
      script:
        service: media_player.select_source
        data:
          entity_id: media_player.volumio
          source: "{{state_attr('media_player.volumio', 'source_list')[1]}}"
    - join: d76
      script:
        service: media_player.select_source
        data:
          entity_id: media_player.volumio
          source: "{{state_attr('media_player.volumio', 'source_list')[2]}}"
```

- _from_joins_: begins the section
- _join_: for each join, list the join type and number.  The type prefix is 'a' for analog joins, 'd' for digital joins and 's' for serial joins.  So s32 would be serial join #32.  Any change in the listed join will invoke the configured behavior.
- _script_: This is a standard HA script.  It follows the [HA scripting syntax](https://www.home-assistant.io/docs/scripts/).  The new value of the join is available to the script as the `value` variable, as shown in the `a2` example above.

 >For digital joins, only the low-to-high transition runs the script.  The high-to-low transition is ignored so that a momentary button press does not fire the script twice.
