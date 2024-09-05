# home-assistant-crestron-component
Integration for Home Assistant for the Crestron XSIG symbol

Currently supported devices:
  - Lights
  - Thermostats
  - Shades
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

> Caution: Join numbers can be confusing when mixing analog/serials and digtals on the same XSIG symbol.  Even though the symbol starts numbering the digitals at "1", the XSIG will actually send the join number corresponding to where the signal appears sequentially in the entire list of signals.
> For example, if you have 25 analog signals followed by 10 digital signals attached to the same XSIG, the digitals will be sent as 26-35, even though they are labeled 1 - 10 on the symbol.  You can either account for this in your configuration on the HA side, or just use one symbol for Analogs and another for Digitals.
> Since the XSIG lets you combine Analog/Serial joins on the same symbol, you can have one XSIG for Analog/Serial joins and another for digitals.  This keeps the join numbering simple.

## Home Assistant configuration.yaml

The `crestron:` entry is mandatory as is the `port:` definition under it.  So at a minimum, you will need:

```yaml
crestron:
  port: 16384
```

Then, if you want to make use of the control surface (touchpanels/kepads) syncing capability, you will need to add either a `to_joins`, a `from_joins` section, or both (see below).

Finally, add entries for each HA component/platform type to your configuration.yaml for the appropriate entity type in Home Assistant:

| Crestron Device                                | Home Assistant component type |
|------------------------------------------------|-------------------------------|
| Light                                          | light                         |
| Thermostat                                     | climate                       |
| Shades                                         | cover                         |
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
 - _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
 - _join_: If light supports brightness: the analog join on the XSIG symbol that represents the light's brightness. If not: the digital join on the XSIG symbol that represents the light's state.
 - _type_: ```brightness``` or ```onoff```

### Thermostat

This platform should work with anything that looks like a CHV-TSTAT/THSTAT (analog joins for heat, cooling setpoints, digital joins for modes, fan modes, and relay states).  I tested this with multiple CHV-TSTAT and CHV-THSTATs.

>TODO: Add support for humidity control on CHV_THSTAT.

```yaml
climate:
  - platform: crestron
    name: "Upstairs Thermostat"
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
    fa_join: 10
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _heat_sp_join_: analog join that represents the heat setpoint
- _cool_sp_join_: analog join that represents the cool setpoint
- _reg_temp_join_: analog join that represents the room temperature read by the thermostat.  The CHV-TSTAT calls this the "regulation temperture" because it my be derived from averaging a bunch of room temperature sensors.  This is so called because it is the temperature used by the thermostat to decide when to make calls for heating or cooling.
- _mode_heat_join_: digital feedback (read-only) join that is high when the thermostat is in heating mode
- _mode_heat_join_: digital feedback (read-only) join that is high when the thermostat is in cooling mode
- _mode_auto_join_: digital feedback (read-only) join that is high when the thermostat is in auto mode
- _mode_off_join_: digital feedback (read-only) join that is high when the thermostat mode is set to off
- _fan_on_join_: digital feedback (read-only) join that is high when the thermostat fan mode is set to (always) on
- _fan_on_join_: digital feedback (read-only) join that is high when the thermostat fan mode is set to auto
- _h1_join_: digital feedback (read-only) join that represents the state of the stage 1 heat relay
- _h2_join_: digital feedback (read-only) join that represents the state of the stage 2 heat relay
- _c1_join_: digital feedback (read-only) join that represents the state of the stage 1 cool relay
- _fa_join_: digital feedback (read-only) join that represents the state of the stage fan relay

### Shades

This should work with any shade that uses an analog join for position plus digital joins for is_opening/closing, is_closed and stop.  I tested with CSM-QMTDC shades.

```yaml
cover:
  - platform: crestron
    name: "Living Room Shades"
    type: shade
    pos_join: 26
    is_opening_join: 41
    is_closing_join: 42
    stop_join: 43
    is_closed_join: 44
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _pos_join_: analog join that represents the shade position.  The value follow the typical definition for a Crestron analog shade (0 = closed, 65535 = open).
- _is_opening_join_: digital feedback (read-only) join that is high when shade is in the process of opening
- _is_closing_join_: digital feedback (read-only) join that is high when shade is in the process of closed
- _is_closed_join_: digital feedback (read-only) join that is high when shade is fully closed
- _stop_join_: digital join that can be pulsed high to stop the shade opening/closing

### Binary Sensor

This can represent any read-only digital signal on the control system.  I typically comment out the "in" signals on the XSIG symbol to keep the "in" and "out" signals lined up.

```yaml
binary_sensor:
  - platform: crestron
    name: "Air Compressor"
    is_on_join: 57
    device_class: power
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _is_on_join_: digital feedback (read-only) join to represent as a binary sensor in Home Assistant
- _device_class_: any device class [supported by the binary_sensor](https://www.home-assistant.io/integrations/binary_sensor/) integration.  This mostly affects how the value will be expressed in various UIs.

### Sensor

This can represent any read-only analog signal on the control system.  I typically comment out the "in" signals on the XSIG symbol to keep the "in" and "out" signals lined up.  Remember that an analog join on the control system is a 16-bit value that can range from 0-65535.  So for many symbol types (especially those representing a brightness or percent) you will need to make use of the `divisor:` parameter.

Example divisors:
 - For sensors that return 10ths of a degree: 10
 - For joins that represent a percent: 655.35 (to convert the 1-65535 range to 1-100)

```yaml
sensor:
  - platform: crestron
    name: "Outside Temperature"
    value_join: 1
    device_class: "temperature"
    unit_of_measurement: "F"
    divisor: 10
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _value_join_: analog join to represent as a sensor in Home Assistant
- _device_class_: any device class [supported by the sensor](https://www.home-assistant.io/integrations/sensor/) integration.  This mostly affects how the value will be expressed in various UIs.
- _unit_of_measurement_: Unit of measurement appropriate for the device class as documented [here](https://developers.home-assistant.io/docs/core/entity/sensor/).
- _divisor_: (optional) number to divide the analog join by to get the correct sensor value.  For example, a crestron temperature sensor returns tenths of a degree (754 represents 75.4 degrees), so you would use a divisor of 10.  Defaults to 1.

### Switch

This could represent any digital signal on the contol system that you want to be able to control/view from HA.

```yaml
switch:
  - platform: crestron
    name: "Dummy Switch"
    switch_join: 65
    pulsed: False
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _switch_join_: digital join to represent as a switch in Home Assistant
- _pulsed_: indicates whether the switch is switched by a signal pulse, or that it switches by providing the requested state.

### Media Player

Use media_player to represent the output of a multi-zone switcher.  For example a PAD-8A is an 8x8 (8 inputs x 8 outputs) audio switcher.  This can be represented by 8 media player components (one for each output).  The component supports source selection (input selection) and volume + mute control.  So it is modeled as a "speaker" media player type in Home Assistant.

This works rather nicely with the template media player integration to allow intuitive control of source devices connected to a multi-zone switcher like the PAD8A.

```yaml
media_player:
  - platform: crestron
    name: "Kitchen Speakers"
    mute_join: 27
    volume_join: 19
    source_number_join: 13
    sources:
      1: "Android TV"
      2: "Roku"
      3: "Apple TV"
      4: "Chromecast"
      7: "Volumio"
      8: "Crestron Streamer"
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _mute_join_: digital join that represents the mute state of the channel.  Note this is not a toggle. Both to and from the control system True = muted, False = not muted.  This might require some extra logic on the control system side if you only have logic that takes a toggle.
- _volume_join_: analog join that represents the volume of the channel (0-65535)
- _source_number_join_: analog join that represents the selected input for the output channel.  1 would correspond to input 1, 2 to input 2, and so on.
- _sources_: a dictionary of _input_ to _name_ mappings.  The input number is the actual input (corresponding to the source_number_join) number, whereas the name will be shown in the UI when selecting inputs/sources.  So when a user selects the _name_ in the UI, the _source_number_join_ will be set to _input_.

### Button (virtual)

This represents action triggers in the control system caused by signal pulses on a digital join. These actions are triggered in Home Assistant by means of a virtual button.
For instance, a virtual button in a Crestron touch panel that triggers a sequence of events programmed in the control system (e.g. turning all lights off) can also be triggered by Home Assistant by means of a Button.

When a virtual button is pressed in Home Assistant, the associated digital join will change to HIGH and change to LOW right after, generating a signal pulse that can be recognized by the control system as an event.

```yaml
button:
  - platform: crestron
    name: "Dummy Button"
    button_join: 70
```

- _name_: The entity id will be derived from this string (lower-cased with _ for spaces).  The friendly name will be set to this string.
- _button_join_: digital join to represent as a button in Home Assistant

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
 - _script_: This is a standard HA script.  It follows the [HA scripting sytax](https://www.home-assistant.io/docs/scripts/).

