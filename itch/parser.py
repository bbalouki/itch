from queue import Queue
from typing import BinaryIO, List, Type

from itch.messages import MESSAGES, MarketMessage
from itch.messages import messages as msgs


class MessageParser(object):
    """
    A market message parser for ITCH 5.0 data.

    """

    def __init__(self, message_type: bytes = MESSAGES):
        self.message_type = message_type

    def read_message_from_file(
        self,
        file: BinaryIO,
        cachesize: int = 4096,
    ) -> List[MarketMessage]:
        """
        Reads and parses market messages from a binary file-like object.

        This method processes binary data in chunks, extracts individual messages
        according to a specific format, and returns a list of successfully decoded 
        MarketMessage objects. Parsing stops either when the end of the file is 
        reached or when a system message with an end-of-messages event code is encountered.

        Args:
            file (BinaryIO): 
                A binary file-like object (opened in binary mode) from which market messages are read.
            cachesize (int, optional): 
                The size (in bytes) of each data chunk read from the file. Defaults to 4096 bytes.

        Returns:
            List[MarketMessage]: 
                A list of parsed MarketMessage objects that match the allowed message types 
                defined in self.message_type.

        Raises:
            ValueError: 
                If a message does not start with the expected 0x00 byte, indicating 
                an unexpected file format or possible corruption.

        Message Format:
            - Each message starts with a 0x00 byte.
            - The following byte specifies the message length.
            - The complete message consists of the first 2 bytes and 'message length' bytes of body.
            - If a system message (message_type == b'S') with event_code == b'C' is encountered, 
            parsing stops immediately.

        Example:
            >>> with open('market_data.bin', 'rb') as binary_file:
            >>>     messages = reader.read_message_from_file(binary_file, cachesize=4096)
            >>>     for message in messages:
            >>>         print(message)
    """
        max_message_size = 52
        file_end_reached = False

        data_buffer = file.read(cachesize)
        buffer_len = len(data_buffer)
        messages: List[MarketMessage] = []

        while not file_end_reached:
            if buffer_len < 2:
                new_data = file.read(cachesize)
                if not new_data:
                    break
                data_buffer += new_data
                buffer_len = len(data_buffer)
                continue

            if data_buffer[0:1] != b"\x00":
                raise ValueError(
                    "Unexpected byte: " + str(data_buffer[0:1], encoding="ascii")
                )

            message_len = data_buffer[1]
            total_len = 2 + message_len

            if buffer_len < total_len:
                # Wait for more data if message is incomplete
                new_data = file.read(cachesize)
                if not new_data:
                    break
                data_buffer += new_data
                buffer_len = len(data_buffer)
                continue
            message_data = data_buffer[2:total_len]
            message = self.get_message_type(message_data)

            if message.message_type in self.message_type:
                messages.append(message)

            if message.message_type == b"S":  # System message
                if message.event_code == b"C":  # End of messages
                    break

            # Update buffer
            data_buffer = data_buffer[total_len:]
            buffer_len = len(data_buffer)

            if buffer_len < max_message_size and not file_end_reached:
                new_data = file.read(cachesize)
                if not new_data:
                    file_end_reached = True
                else:
                    data_buffer += new_data
                    buffer_len = len(data_buffer)

        return messages

    def read_message_from_bytes(self, data: bytes):
        """
        Process one or multiple ITCH binary messages from a raw bytes input.

        Args:
            data (bytes): Binary blob containing one or more ITCH messages.

        Returns:
            Queue: A queue containing parsed ITCH message objects.

        Notes:
            - Each message must be prefixed with a 0x00 header and a length byte.
            - No buffering is done here — this is meant for real-time decoding.
        """

        offset = 0
        messages = Queue()
        while offset + 2 <= len(data):
            # Each message starts with: 1-byte header (0x00) 1-byte length
            if data[offset : offset + 1] != b"\x00":
                raise ValueError(
                    f"Unexpected start byte at offset {offset}: "
                    f"{str(data[offset : offset + 1], encoding='ascii')}"
                )

            msg_len = data[offset + 1]
            total_len = 2 + msg_len

            if offset + total_len > len(data):
                break

            raw_msg = data[offset + 2 : offset + total_len]
            message = self.get_message_type(raw_msg)

            if message.message_type in self.message_type:
                messages.put(message)

            if message.message_type == b"S":  # System message
                if message.event_code == b"C":  # End of messages
                    break

            offset += total_len

        return messages

    def get_message_type(self, message: bytes) -> Type[MarketMessage]:
        """
        Take an entire bytearray and return the appropriate ITCH message
        instance based on the message type indicator (first byte of the message).

        All message type indicators are single ASCII characters.
        """
        message_type = message[0:1]
        try:
            return msgs[message_type](message)
        except Exception:
            raise ValueError(
                f"Unknown message type: {message_type.decode(encoding='ascii')}"
            )
