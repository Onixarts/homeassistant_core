import asyncio
import logging

from .hapcan_message import HapcanMessage

_LOGGER = logging.getLogger(__name__)


class HapcanBridge:
    def __init__(self, host, port, log_frames=False):
        self.host = host
        self.port = port
        self.log_frames = log_frames
        self.reader = None
        self.writer = None
        self.incoming_message = bytearray(15)  # assuming a fixed length of 15
        self.incoming_message_index = 0
        self.data_callback = None
        self.is_connected = False
        self.listetning_task = None
        self.sending_buffer = asyncio.Queue()
        self.sending_task = None

    async def connect(self):
        try:
            _LOGGER.info("Connecting to HAPCAN bridge at %s:%s", self.host, self.port)
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.is_connected = True
            _LOGGER.info("Connected to HAPCAN bridge at %s:%s", self.host, self.port)
            self.listetning_task = asyncio.create_task(self.listen())

            self.sending_task = asyncio.create_task(self.process_sending_buffer())

        except Exception as e:
            self.is_connected = False
            _LOGGER.error(
                "Failed to connect to HAPCAN bridge at %s:%s - %s",
                self.host,
                self.port,
                e,
            )
            await asyncio.sleep(5)

    def register_callback(self, callback):
        self.data_callback = callback

    async def listen(self):
        while True:
            try:
                data = await self.reader.read(1024)
                if data:
                    await self.handle_data(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Error while listening: %s", e)
                self.is_connected = False
                self.listetning_task = asyncio.create_task(self.connect())
                break

    async def handle_data(self, data):
        for byte in data:
            if self.incoming_message_index == 0 and byte != 0xAA:
                continue

            self.incoming_message[self.incoming_message_index] = byte

            if self.incoming_message_index == 12 and byte == 0xA5:
                self.message_received(self.incoming_message)
                self.incoming_message = bytearray(15)
                self.incoming_message_index = 0
                continue

            if self.incoming_message_index == 14:
                if byte == 0xA5:
                    self.message_received(self.incoming_message)
                else:
                    _LOGGER.warning(
                        "Invalid frame received: "
                        + self.message_to_string(self.incoming_message)
                    )
                self.incoming_message = bytearray(15)
                self.incoming_message_index = 0
                continue

            self.incoming_message_index += 1

    async def internal_send(self, payload):
        try:
            sum_val = 0
            if len(payload) == 15:
                for i in range(1, 13):
                    sum_val += payload[i]
                payload[13] = sum_val % 256
            elif len(payload) == 13:
                for i in range(1, 11):
                    sum_val += payload[i]
                payload[11] = sum_val % 256

            if self.log_frames:
                _LOGGER.info("Sending  >> %s", self.message_to_string(payload))

            if self.writer:
                self.writer.write(payload)
                await self.writer.drain()
            else:
                _LOGGER.error("Not connected to HAPCAN bridge")
        except Exception as e:
            _LOGGER.error(e)

    def send(self, msg):
        _LOGGER.debug("send")
        if self.is_connected:
            if msg.get("payload") is not None and isinstance(msg["payload"], bytearray):
                self.sending_buffer.put_nowait(msg["payload"])
                _LOGGER.info("Queued: %s", self.message_to_string(msg["payload"]))

    async def process_sending_buffer(self):
        while True:
            payload = await self.sending_buffer.get()
            await self.internal_send(payload)
            await asyncio.sleep(0.1)

    def message_received(self, frame):
        if self.log_frames:
            _LOGGER.info("Received << %s", self.message_to_string(frame))

        hapcan_msg = HapcanMessage(frame)

        if self.data_callback:
            self.data_callback({"payload": hapcan_msg, "topic": "Hapcan Message"})

    def message_to_string(self, hapcan_message):
        return " ".join(format(byte, "02X") for byte in hapcan_message)

    def close(self):
        if self.writer:
            self.writer.close()
            _LOGGER.info("Connection to HAPCAN bridge closed")
        self.is_connected = False

    def is_connected(self):
        return self.is_connected
