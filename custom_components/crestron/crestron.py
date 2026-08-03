import asyncio
import struct
import logging

_LOGGER = logging.getLogger(__name__)


class CrestronXsig:
    def __init__(self):
        """Initialize CrestronXsig object"""
        self._digital = {}
        self._analog = {}
        self._serial = {}
        self._writer = None
        self._callbacks = set()
        self._server = None
        self._available = False
        self._sync_all_joins_callback = None

    async def listen(self, port):
        """Start TCP XSIG server listening on configured port"""
        server = await asyncio.start_server(self.handle_connection, "0.0.0.0", port)
        self._server = server
        addr = server.sockets[0].getsockname()
        _LOGGER.info(f"Listening on {addr}:{port}")

    async def stop(self):
        """Stop TCP XSIG server"""
        self._available = False
        await self._notify("available", "False")
        _LOGGER.info("Stop called. Closing connection")
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        if self._server is not None:
            self._server.close()

    async def _notify(self, cbtype, value):
        """Dispatch a join change to every registered callback.

        Callbacks run arbitrary user configuration (from_joins scripts), so a
        failure in one must not take down the connection or stop the remaining
        callbacks from being notified.
        """
        for callback in self._callbacks:
            try:
                await callback(cbtype, value)
            except Exception:
                _LOGGER.exception(
                    f"Error in callback for {cbtype} = {value}.  Ignoring and continuing."
                )

    def _can_write(self):
        """Return True if there is a live transport to write to.

        A writer that has been reset by the peer stays truthy, so testing the
        object alone would let writes disappear into a dead socket.
        """
        return self._writer is not None and not self._writer.is_closing()

    def register_sync_all_joins_callback(self, callback):
        """Allow callback to be registred for when control system requests an update to all joins"""
        _LOGGER.debug("Sync-all-joins callback registered")
        self._sync_all_joins_callback = callback

    def register_callback(self, callback):
        """Allow callbacks to be registered for when dict entries change"""
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """Allow callbacks to be de-registered"""
        self._callbacks.discard(callback)

    async def handle_connection(self, reader, writer):
        """Parse packets from Crestron XSIG symbol"""
        self._writer = writer
        peer = writer.get_extra_info("peername")
        _LOGGER.info(f"Control system connection from {peer}")
        try:
            _LOGGER.debug("Sending update request")
            writer.write(b"\xfd")
            self._available = True
            await self._notify("available", "True")

            connected = True
            while connected:
                data = await reader.read(1)
                if data:
                    # Sync all joins request
                    if data[0] == 0xFB:
                        _LOGGER.debug("Got update all joins request")
                        if self._sync_all_joins_callback is not None:
                            await self._sync_all_joins_callback()
                            _LOGGER.debug("Calling sync-all-joins callback")
                    else:
                        data += await reader.read(1)
                        # Digital Join
                        if (
                            data[0] & 0b11000000 == 0b10000000
                            and data[1] & 0b10000000 == 0b00000000
                        ):
                            header = struct.unpack("BB", data)
                            join = ((header[0] & 0b00011111) << 7 | header[1]) + 1
                            value = ~header[0] >> 5 & 0b1
                            self._digital[join] = True if value == 1 else False
                            _LOGGER.debug(f"Got Digital: {join} = {value}")
                            await self._notify(f"d{join}", str(value))
                        # Analog Join
                        elif (
                            data[0] & 0b11001000 == 0b11000000
                            and data[1] & 0b10000000 == 0b00000000
                        ):
                            data += await reader.read(2)
                            header = struct.unpack("BBBB", data)
                            join = ((header[0] & 0b00000111) << 7 | header[1]) + 1
                            value = (
                                (header[0] & 0b00110000) << 10
                                | header[2] << 7
                                | header[3]
                            )
                            self._analog[join] = value
                            _LOGGER.debug(f"Got Analog: {join} = {value}")
                            await self._notify(f"a{join}", str(value))
                        # Serial Join
                        elif (
                            data[0] & 0b11111000 == 0b11001000
                            and data[1] & 0b10000000 == 0b00000000
                        ):
                            data += await reader.readuntil(b"\xff")
                            header = struct.unpack("BB", data[:2])
                            join = ((header[0] & 0b00000111) << 7 | header[1]) + 1
                            string = data[2:-1].decode("utf-8")
                            self._serial[join] = string
                            _LOGGER.debug(f"Got String: {join} = {string}")
                            await self._notify(f"s{join}", string)
                        else:
                            _LOGGER.debug(f"Unknown Packet: {data.hex()}")
                else:
                    _LOGGER.info("Control system disconnected")
                    connected = False
        except asyncio.CancelledError:
            raise
        except ConnectionError as err:
            # Peer reset/aborted the link, often surfacing on the parked read
            _LOGGER.info(f"Connection to control system {peer} lost: {err}")
        except Exception:
            _LOGGER.exception(f"Error handling connection from {peer}.  Closing it.")
        finally:
            await self._close_connection(writer, peer)

    async def _close_connection(self, writer, peer):
        """Tear down a connection and mark the hub unavailable.

        Runs on every exit path from handle_connection, including exceptions,
        so the hub can never be left reporting available with a dead writer.
        """
        # A newer connection may already have replaced this one.  Only give up
        # availability if we are still the active writer.
        if self._writer is writer:
            self._writer = None
            if self._available:
                self._available = False
                await self._notify("available", "False")
        _LOGGER.info(f"Closing connection to control system {peer}")
        try:
            if not writer.is_closing():
                writer.close()
            await writer.wait_closed()
        except Exception as err:
            _LOGGER.debug(f"Error while closing connection to {peer}: {err}")

    def is_available(self):
        """Returns True if control system is connected"""
        return self._available

    def get_analog(self, join):
        """Return analog value for join"""
        return self._analog.get(join, 0)

    def get_digital(self, join):
        """Return digital value for join"""
        return self._digital.get(join, False)

    def get_serial(self, join):
        """Return serial value for join"""
        return self._serial.get(join, "")

    def set_analog(self, join, value):
        """Send Analog Join to Crestron XSIG symbol"""
        if self._can_write():
            data = struct.pack(
                ">BBBB",
                0b11000000 | (value >> 10 & 0b00110000) | (join - 1) >> 7,
                (join - 1) & 0b01111111,
                value >> 7 & 0b01111111,
                value & 0b01111111,
            )
            self._writer.write(data)
            _LOGGER.debug(f"Sending Analog: {join}, {value}")
        else:
            _LOGGER.info(f"Could not send Analog {join}.  No connection to hub")

    async def set_digital_helper(self, join, value, pulsed=False):
        if pulsed:
            # Pulsed switches can only be switched by signal pulses
            # Therefore, must check if switch is not already on
            if (value is True and not self.get_digital(join)) or (
                value is False and self.get_digital(join)
            ):
                self.set_digital(join, True)
                await asyncio.sleep(0.05)
                self.set_digital(join, False)
        else:
            self.set_digital(join, value=value)

    def set_digital(self, join, value):
        """Send Digital Join to Crestron XSIG symbol"""
        if self._can_write():
            data = struct.pack(
                ">BB",
                0b10000000 | (~value << 5 & 0b00100000) | (join - 1) >> 7,
                (join - 1) & 0b01111111,
            )
            self._writer.write(data)
            _LOGGER.debug(f"Sending Digital: {join}, {value}")
        else:
            _LOGGER.info(f"Could not send Digital {join}.  No connection to hub")

    def set_serial(self, join, string):
        """Send String Join to Crestron XSIG symbol"""
        if len(string) > 252:
            _LOGGER.info(f"Could not send. String too long ({len(string)}>252)")
            return
        elif self._can_write():
            data = struct.pack(
                ">BB", 0b11001000 | ((join - 1) >> 7), (join - 1) & 0b01111111
            )
            data += string.encode()
            data += b"\xff"
            self._writer.write(data)
            _LOGGER.debug(f"Sending Serial: {join}, {string}")
        else:
            _LOGGER.info(f"Could not send Serial {join}.  No connection to hub")
