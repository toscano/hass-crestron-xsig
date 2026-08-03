# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (`custom_components/crestron`) that talks to a Crestron control system over the XSIG (Intersystem Communications) binary protocol. Home Assistant runs the **TCP server**; the control system's TCP/IP Client symbol connects in. There is no build step, no dependency manifest, and no test suite — the code only runs inside a Home Assistant instance.

## Commands

```bash
./deploy-dev.sh    # rsync custom_components/crestron/ -> ha-dev:/root/config/custom_components/crestron
./deploy-prod.sh   # rsync custom_components/crestron/ -> crosby:~/docker/homeassistant/data/custom_components/crestron
```

Both require a Home Assistant restart to pick up changes. Testing is manual: deploy to the dev instance, restart, and watch the log (`home-assistant.crestron.log` in the repo root is a captured sample — it is gitignored and can be large).

Formatting is [black](https://black.readthedocs.io/) (configured in [.vscode/settings.json](.vscode/settings.json)); several files predate it and are not black-clean.

Version lives in [manifest.json](custom_components/crestron/manifest.json) and uses `yyyy.mm.dd` (as of commit 304202d). Bump it on every behavior change so HACS/HA sees the update.

## Architecture

Three layers, bottom-up:

**1. Protocol — [crestron.py](custom_components/crestron/crestron.py)**

`CrestronXsig` is pure asyncio with no Home Assistant imports. It owns the listening socket, decodes/encodes XSIG packets, and caches the last known value of every join in three dicts (`_digital`, `_analog`, `_serial`). Key protocol details encoded here:

- Joins are **1-based on the wire but 0-based in the packet** — every encode does `join - 1`, every decode does `+ 1`.
- Digital = 2 bytes, analog = 4 bytes, serial = 2-byte header + UTF-8 + `0xFF` terminator. Packet type is discriminated by masking the first byte (see the `if/elif` chain in `handle_connection`).
- Digital value is **inverted** on the wire (bit 5 of byte 0 is the *not*-value).
- Analog values are 16-bit (0–65535) split across three 7-bit fields.
- `0xFD` sent on connect asks the control system to send all its join values. `0xFB` received is the control system asking HA to send all of *its* values — this fires `_sync_all_joins_callback`.
- Only one connection is tracked (`self._writer` is overwritten by each new connection).
- Serial strings over 252 chars are dropped with a log line, not raised.

**2. Hub / config sync — [\_\_init\_\_.py](custom_components/crestron/__init__.py)**

`CrestronHub` wraps `CrestronXsig`, stores it at `hass.data[DOMAIN][HUB]`, and implements the bidirectional "control surface sync" configured under the root `crestron:` YAML key:

- `to_joins` (HA → control system): each entry is normalized into a `Template` — a bare `entity_id` becomes `{{states('...')}}`, an `entity_id` + `attribute` becomes `{{state_attr(...)}}`, or a `value_template` is used directly. All templates go into one `async_track_template_result` tracker; `template_change_callback` dispatches on the join's type prefix (`d`/`a`/`s`) to `set_digital`/`set_analog`/`set_serial`. Digital coercion accepts `on`/`off`/`True`/`true`/`False`/`false`/`1`/`0` and silently skips anything else.
- `from_joins` (control system → HA): registers `join_change_callback` on the hub, which runs the configured HA `script:` with `value` bound to the join's new value. Digital `0` transitions are deliberately ignored so momentary button presses don't fire the script twice.
- `sync_joins_to_hub` re-renders every `to_joins` template and pushes it — this is what the `0xFB` request triggers.

**3. Platforms — one file per HA domain**

`binary_sensor`, `sensor`, `switch`, `light`, `climate`, `cover`, `media_player`, `button`. All are YAML-only (`async_setup_platform`, no config flow) and follow an identical shape:

```python
hub = hass.data[DOMAIN][HUB]           # grab the shared CrestronXsig
async_added_to_hass  -> hub.register_callback(self.process_callback)
process_callback     -> self.async_write_ha_state()   # any join change re-renders every entity
should_poll          -> False
available            -> hub.is_available()
state properties     -> read hub.get_analog/get_digital/get_serial(join) on demand
```

Entities hold **no state of their own** — they are views over the hub's join dicts. `unique_id` is always `"<platform>-<join>"`, so changing a join number in YAML creates a new entity in the HA registry.

The callback is broadcast to *every* registered entity on *every* join change; entities do not filter by join. That's fine at this scale but means writes are O(entities) per packet.

### Conventions when adding a platform

1. Add `CONF_*_JOIN` names to [const.py](custom_components/crestron/const.py) (this is the single list of every YAML key).
2. Add the domain to `PLATFORMS` in [\_\_init\_\_.py](custom_components/crestron/__init__.py).
3. Define a `PLATFORM_SCHEMA` with `extra=vol.ALLOW_EXTRA` and `cv.positive_int` joins.
4. Follow the register-callback / `should_poll = False` / read-through-to-hub pattern above.
5. Document it in [README.md](README.md).

### Pulsed vs. level joins

Many Crestron symbols are driven by a momentary pulse rather than a held level. The pattern is `set_digital(join, True)` → `await asyncio.sleep(0.05)` → `set_digital(join, False)`, guarded by a read of the current state so a pulse isn't sent when the target is already in the desired state. This is implemented several times independently: `CrestronXsig.set_digital_helper`, `switch.async_turn_on/off`, `light` onoff mode, and `button.async_press` (which uses 0.2 s). Prefer `set_digital_helper` in new code.

## README

[README.md](README.md) is the user-facing config reference and is the only documentation of the YAML surface. It was reconciled against the schemas in August 2026 — keep it that way, and update it in the same commit as any `PLATFORM_SCHEMA` change.

Two things it documents that are not obvious from the schemas alone:

- The elevator cover type reads `up_set_join`, `up_reset_join`, `down_set_join` and `down_reset_join` via `config.get`, but they are **not** in `PLATFORM_SCHEMA`. They only validate because of `extra=vol.ALLOW_EXTRA`, so a typo in one of those four keys fails silently at runtime (the join comes back as `None`).
- `media_player`'s `off_join` is both the power feedback and the turn-off trigger: the entity reports `on` while that join is high, and turning off pulses it.
