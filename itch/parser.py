from typing import IO, BinaryIO, Iterator

from itch.messages import MESSAGES, MarketMessage
from itch.messages import messages as msgs


class MessageParser(object):
    """
    A market message parser for ITCH 5.0 data.

    """

    def __init__(self, message_type: bytes = MESSAGES):
        self.message_type = message_type

    def read_message_from_file(
        self, file: BinaryIO, cachesize: int = 65_536, save_file: IO = None
    ) -> Iterator[MarketMessage]:
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
                The size of each data chunk to read. Defaults to 65536 bytes (64KB).
            save_file (IO, optional):
                A binary file-like object (opened in binary write mode) where filtered messages are saved.

        Yields:
            MarketMessage:
                The next parsed MarketMessage object from the file.

        Raises:
            ValueError:
                If a message does not start with the expected 0x00 byte, indicating
                an unexpected file format or possible corruption.

        Notes:
            - Each message starts with a 0x00 byte.
            - The following byte specifies the message length.
            - The complete message consists of the first 2 bytes and 'message length' bytes of body.
            - If a system message (message_type == b'S') with event_code == b'C' is encountered,
                parsing stops immediately.

        Example:
            >>> data_file = "01302020.NASDAQ_ITCH50.gz"
            >>> message_type = b"AFE" # Example message type to filter
            >>> parser = MessageParser(message_type=message_type)
            >>> with gzip.open(data_file, "rb") as itch_file:
            >>> message_count = 0
            >>> start_time = time.time()
            >>> for message in parser.read_message_from_file(itch_file):
            >>>     message_count += 1
            >>>     if message_count <= 5:
            >>>         print(message)
            >>> end_time = time.time()
            >>> print(f"Processed {message_count} messages in {end_time - start_time:.2f} seconds")
            >>> print(f"Average time per message: {(end_time - start_time) / message_count:.6f} seconds")
        """
        if not file.readable():
            raise ValueError("file must be opened in binary read mode")

        if save_file is not None:
            if not save_file.writable():
                raise ValueError("save_file must be opened in binary write mode")

        data_buffer = b""
        offset = 0

        while True:
            if len(data_buffer) - offset < 2:
                data_buffer = data_buffer[offset:]
                offset = 0
                new_data = file.read(cachesize)
                if not new_data:
                    break
                data_buffer += new_data

                if len(data_buffer) < 2:
                    break

            if data_buffer[offset : offset + 1] != b"\x00":
                raise ValueError(
                    "Unexpected byte: "
                    + str(data_buffer[offset : offset + 1], encoding="ascii")
                )

            message_len = data_buffer[offset + 1]
            total_len = 2 + message_len

            if len(data_buffer) - offset < total_len:
                data_buffer = data_buffer[offset:]
                offset = 0

                new_data = file.read(cachesize)
                if not new_data:
                    break
                data_buffer += new_data
                continue

            message_data = data_buffer[offset + 2 : offset + total_len]
            message = self.get_message_type(message_data)

            if message.message_type in self.message_type:
                if save_file is not None:
                    msg_len_to_bytes = message.message_size.to_bytes()
                    save_file.write(b"\x00" + msg_len_to_bytes + message.to_bytes())
                yield message

            if message.message_type == b"S":  # System message
                if message.event_code == b"C":  # End of messages
                    break
            offset += total_len

    def read_message_from_bytes(
        self, data: bytes, save_file: IO = None
    ) -> Iterator[MarketMessage]:
        """
        Process one or multiple ITCH binary messages from a raw bytes input.

        Args:
            data (bytes): Binary blob containing one or more ITCH messages.

        save_file (IO, optional):
            A binary file-like object (opened in binary write mode) where filtered messages are saved.

        Yields:
            MarketMessage:
                The next parsed MarketMessage object from the bytes input.

        Notes:
            - Each message must be prefixed with a 0x00 header and a length byte.
            - No buffering is done here — this is meant for real-time decoding.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes or bytearray not " + str(type(data)))

        if save_file is not None:
            if not save_file.writable():
                raise ValueError("save_file must be opened in binary write mode")

        offset = 0
        data_view = memoryview(data)
        data_len = len(data_view)

        while offset + 2 <= data_len:
            if data_view[offset : offset + 1] != b"\x00":
                raise ValueError(
                    f"Unexpected start byte at offset {offset:offset+1}: "
                    f"{data_view[offset : offset + 1].tobytes()}"
                )
            msg_len = data_view[offset + 1]
            total_len = 2 + msg_len

            if offset + total_len > data_len:
                break

            raw_msg = data_view[offset + 2 : offset + total_len]
            message = self.get_message_type(raw_msg.tobytes())

            if message.message_type in self.message_type:
                if save_file is not None:
                    msg_len_to_bytes = message.message_size.to_bytes()
                    save_file.write(b"\x00" + msg_len_to_bytes + message.to_bytes())
                yield message

            if message.message_type == b"S":  # System message
                if message.event_code == b"C":  # End of messages
                    break

            offset += total_len

    def get_message_type(self, message: bytes) -> MarketMessage:
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
