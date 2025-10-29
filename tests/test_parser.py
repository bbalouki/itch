import unittest
from io import BytesIO

import pytest

from itch.messages import create_message
from itch.parser import MessageParser
from .data import TEST_DATA


class TestMessageParser(unittest.TestCase):
    def setUp(self):
        self.parser = MessageParser()

    def test_parse_stream_single_message(self):
        """Test that the parser correctly parses a single message from a stream."""
        raw_message = create_message(b"S", **TEST_DATA[b"S"]).to_bytes()
        message_len = len(raw_message).to_bytes(1, "big")
        data = b"\x00" + message_len + raw_message
        messages = list(self.parser.parse_stream(data))
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(
            messages[0], type(create_message(b"S", **TEST_DATA[b"S"]))
        )

    def test_parse_stream_multiple_messages(self):
        """Test that the parser correctly parses multiple messages from a stream."""
        raw_message_1 = create_message(b"S", **TEST_DATA[b"S"]).to_bytes()
        raw_message_2 = create_message(b"A", **TEST_DATA[b"A"]).to_bytes()
        message_len_1 = len(raw_message_1).to_bytes(1, "big")
        message_len_2 = len(raw_message_2).to_bytes(1, "big")
        data = (
            b"\x00"
            + message_len_1
            + raw_message_1
            + b"\x00"
            + message_len_2
            + raw_message_2
        )
        messages = list(self.parser.parse_stream(data))
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(
            messages[0], type(create_message(b"S", **TEST_DATA[b"S"]))
        )
        self.assertIsInstance(
            messages[1], type(create_message(b"A", **TEST_DATA[b"A"]))
        )

    def test_parse_file(self):
        """Test that the parser correctly parses messages from a file."""
        raw_message = create_message(b"S", **TEST_DATA[b"S"]).to_bytes()
        message_len = len(raw_message).to_bytes(1, "big")
        data = b"\x00" + message_len + raw_message
        file = BytesIO(data)
        messages = list(self.parser.parse_file(file))
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(
            messages[0], type(create_message(b"S", **TEST_DATA[b"S"]))
        )

    def test_unknown_message_type(self):
        """Test that the parser raises a ValueError for an unknown message type."""
        raw_message = b"\x00\x01\x00"
        with self.assertRaises(ValueError):
            list(self.parser.parse_stream(raw_message))

    def test_incomplete_message(self):
        """Test that the parser handles incomplete messages."""
        raw_message = create_message(b"S", **TEST_DATA[b"S"]).to_bytes()
        message_len = len(raw_message).to_bytes(1, "big")
        data = b"\x00" + message_len + raw_message[:-1]
        messages = list(self.parser.parse_stream(data))
        self.assertEqual(len(messages), 0)

    def test_stop_on_system_event_c(self):
        """Test that the parser stops on a system event message with event code 'C'."""
        kwargs = TEST_DATA[b"S"].copy()
        kwargs["event_code"] = b"C"
        raw_message_1 = create_message(b"S", **kwargs).to_bytes()
        raw_message_2 = create_message(b"A", **TEST_DATA[b"A"]).to_bytes()
        message_len_1 = len(raw_message_1).to_bytes(1, "big")
        message_len_2 = len(raw_message_2).to_bytes(1, "big")
        data = (
            b"\x00"
            + message_len_1
            + raw_message_1
            + b"\x00"
            + message_len_2
            + raw_message_2
        )
        messages = list(self.parser.parse_stream(data))
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], type(create_message(b"S", **kwargs)))


@pytest.mark.parametrize("message_type", TEST_DATA.keys())
def test_parse_all_message_types(message_type):
    """Test that the parser correctly parses all message types."""
    parser = MessageParser()
    kwargs = TEST_DATA[message_type]
    raw_message = create_message(message_type, **kwargs).to_bytes()
    message_len = len(raw_message).to_bytes(1, "big")
    data = b"\x00" + message_len + raw_message
    messages = list(parser.parse_stream(data))
    assert len(messages) == 1
    assert isinstance(messages[0], type(create_message(message_type, **kwargs)))


if __name__ == "__main__":
    unittest.main()
