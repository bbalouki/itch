from typing import IO, BinaryIO, Callable, Iterator, Optional, Tuple

from itch.messages import MESSAGES, MarketMessage
from itch.messages import messages as msgs


class MessageParser(object):
    """
    A market message parser for ITCH 5.0 data.

    """

    def __init__(self, message_type: bytes = MESSAGES):
        self.message_type = message_type

    def get_message_type(self, message: bytes) -> MarketMessage:
        """
        Take an entire bytearray and return the appropriate ITCH message
        instance based on the message type indicator (first byte of the message).

        All message type indicators are single ASCII characters.
        """
        message_type = message[0:1]
        try:
            return msgs[message_type](message)  # type: ignore
        except Exception:
            raise ValueError(
                f"Unknown message type: {message_type.decode(encoding='ascii')}"
            )

    def _parse_message_from_buffer(
        self, buffer: memoryview, offset: int
    ) -> Optional[Tuple[MarketMessage, int]]:
        """
        Parses a single ITCH message from a memory buffer.

        This method checks for a 2-byte header (a null byte and a length byte),
        determines the full message size, and extracts the message if the
        complete message is present in the buffer.

        Args:
            buffer (memoryview):
                The buffer containing the binary data.
            offset (int):
                The starting position in the buffer to begin parsing.

        Returns:
            Optional[Tuple[MarketMessage, int]]:
                A tuple containing the parsed MarketMessage and the total length
                of the message including the header. Returns None if a complete
                message could not be parsed.

        Raises:
            ValueError:
                If the data at the current offset does not start with the
                expected 0x00 byte.
        """
        buffer_len = len(buffer)
        if offset + 2 > buffer_len:
            return None

        if buffer[offset : offset + 1] != b"\x00":
            raise ValueError(
                f"Unexpected start byte at offset {offset}: "
                f"{buffer[offset : offset + 1].tobytes()}"
            )

        msg_len = buffer[offset + 1]
        total_len = 2 + msg_len

        if offset + total_len > buffer_len:
            return None

        raw_msg = buffer[offset + 2 : offset + total_len]
        message = self.get_message_type(raw_msg.tobytes())
        return message, total_len

    def parse_file(
        self, file: BinaryIO, cachesize: int = 65_536, save_file: Optional[IO] = None
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
            >>> for message in parser.parse_file(itch_file):
            >>>     message_count += 1
            >>>     if message_count <= 5:
            >>>         print(message)
            >>> end_time = time.time()
            >>> print(f"Processed {message_count} messages in {end_time - start_time:.2f} seconds")
            >>> print(f"Average time per message: {(end_time - start_time) / message_count:.6f} seconds")
        """
        if not file.readable():
            raise ValueError("file must be opened in binary read mode")

        if save_file is not None and not save_file.writable():
            raise ValueError("save_file must be opened in binary write mode")

        data_buffer = b""
        offset = 0

        while True:
            parsed = self._parse_message_from_buffer(memoryview(data_buffer), offset)
            if parsed is None:
                data_buffer = data_buffer[offset:]
                offset = 0
                new_data = file.read(cachesize)
                if not new_data:
                    break
                data_buffer += new_data
                continue

            message, total_len = parsed

            if message.message_type in self.message_type:
                if save_file is not None:
                    msg_len_to_bytes = message.message_size.to_bytes()
                    save_file.write(b"\x00" + msg_len_to_bytes + message.to_bytes())
                yield message

            if (
                message.message_type == b"S"
                and getattr(message, "event_code", b"") == b"C"
            ):
                break

            offset += total_len

    def parse_stream(
        self, data: bytes, save_file: Optional[IO] = None
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
            raise TypeError("data must be bytes or bytearray, not " + str(type(data)))

        if save_file is not None and not save_file.writable():
            raise ValueError("save_file must be opened in binary write mode")

        offset = 0
        data_view = memoryview(data)

        while True:
            parsed = self._parse_message_from_buffer(data_view, offset)
            if parsed is None:
                break

            message, total_len = parsed

            if message.message_type in self.message_type:
                if save_file is not None:
                    msg_len_to_bytes = message.message_size.to_bytes()
                    save_file.write(b"\x00" + msg_len_to_bytes + message.to_bytes())
                yield message

            if (
                message.message_type == b"S"
                and getattr(message, "event_code", b"") == b"C"
            ):
                break

            offset += total_len

    def parse_messages(
        self,
        data: BinaryIO | bytes | bytearray,
        callback: Callable[[MarketMessage], None],
    ) -> None:
        """
        Parses messages from data and invokes a callback for each message.
        """
        parser_func = (
            self.parse_stream
            if isinstance(data, (bytes, bytearray))
            else self.parse_file
        )
        for message in parser_func(data):
            callback(message)
