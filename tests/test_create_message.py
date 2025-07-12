import pytest
from itch.messages import create_message, messages
from .data import TEST_DATA

@pytest.mark.parametrize("message_type, sample_data", TEST_DATA.items())
def test_create_message_and_pack(message_type, sample_data):
    """
    Tests that create_message correctly creates a message that can be packed,
    and that the packed message can be unpacked to match the original data.
    """
    # Create a message using the new function
    created_message = create_message(message_type, **sample_data)

    # Pack the created message
    packed_message = created_message.pack()

    # Unpack the message using the original class constructor
    message_class = messages[message_type]
    unpacked_message = message_class(packed_message)

    # Verify that the attributes of the unpacked message match the original data
    for key, expected_value in sample_data.items():
        if key == 'timestamp':
            # Timestamps are 48-bit, so we need to mask the original value
            expected_value &= ((1 << 48) - 1)
        assert getattr(unpacked_message, key) == expected_value, (
            f"Attribute '{key}' mismatch for message type {message_type.decode()}"
        )
