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

    async def connect(self):
        try:
            _LOGGER.info("Connecting to HAPCAN bridge at %s:%s", self.host, self.port)
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.is_connected = True
            _LOGGER.info("Connected to HAPCAN bridge at %s:%s", self.host, self.port)
            asyncio.create_task(self.listen())
        except Exception as e:
            self.is_connected = False
            _LOGGER.error(
                "Failed to connect to HAPCAN bridge at %s:%s - %s",
                self.host,
                self.port,
                e,
            )

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

    def send(self, data):
        """Wysyła dane do mostka HAPCAN."""
        if self.writer:
            self.writer.write(data)
            _LOGGER.info("Data sent: %s", self.message_to_string(data))
        else:
            _LOGGER.error("Not connected to HAPCAN bridge")

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

    def is_connected(self):
        return self.is_connected
