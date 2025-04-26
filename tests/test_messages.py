import struct
from dataclasses import is_dataclass
from decimal import getcontext
from typing import Any, Dict, Type

import pytest

import itch.messages as msgs
from itch.messages import messages

from .data import DEFAULT_TIMESTAMP, TEST_DATA

# Set Decimal precision for potential future use
getcontext().prec = 28


# --- Helper Functions ---
def pack_message_data(
    msg_class: Type[msgs.MarketMessage], data: Dict[str, Any]
) -> bytes:
    """Packs sample data into a raw byte message according to the class format."""
    instance = msg_class.__new__(msg_class)

    # Set common attributes first
    instance.stock_locate = data["stock_locate"]
    instance.tracking_number = data["tracking_number"]

    # --- TRUNCATE TIMESTAMP ---
    # Ensure the timestamp used for packing fits within 48 bits,
    # consistent with the 6-byte specification 
    # and the HHHI format interpretation.
    timestamp_48bit = data["timestamp"] & ((1 << 48) - 1)
    instance.timestamp = timestamp_48bit
    # --------------------------

    # Also set price_precision if it exists on the class
    if hasattr(msg_class, "price_precision"):
        # Use the class default price_precision
        # unless overridden in sample_data
        instance.price_precision = data.get(
            "price_precision", msg_class.price_precision
        )

    # Set specific attributes from the data dict
    for key, value in data.items():
        # Skip keys already handled or class-level attributes
        # not directly part of the data payload structure usually
        if key not in [
            "stock_locate",
            "tracking_number",
            "timestamp",
            "message_type",
            "description",
            "message_format",
            "message_pack_format",
            "message_size",
            "price_precision",
        ]:
            try:
                # Ensure bytes fields have the correct length if specified 
                # by format (e.g., '8s', '4s')
                # Note: struct.pack usually handles padding/truncation for 's' format,
                # but ensure the input 'value' is bytes if the class expects bytes.
                if isinstance(getattr(msg_class, key, None), bytes) and isinstance(
                    value, str
                ):
                    value_to_set = value.encode("ascii")
                else:
                    value_to_set = value
                setattr(instance, key, value_to_set)
            except AttributeError:
                pytest.fail(f"Failed to set attribute '{key}' on {msg_class.__name__}")

    # Set message type needed for packing (must be set before calling pack)
    instance.message_type = msg_class.message_type

    # Now call pack - instance should have all attributes defined in 'data'
    try:
        packed_message = instance.pack()
    except struct.error as e:
        print(f"Struct error during pack for {msg_class.__name__}: {e}")
        raise
    return packed_message


# --- Test Fixtures ---
@pytest.fixture(scope="module", params=list(TEST_DATA.keys()))
def message_params(request):
    """Provides message type byte, class, and sample data for parametrization."""
    message_type_byte = request.param
    message_class = None

    def get_all_subclasses(cls):
        all_subs = set()
        q = [cls]
        while q:
            parent = q.pop()
            for child in parent.__subclasses__():
                if child not in all_subs:
                    all_subs.add(child)
                    q.append(child)
        return all_subs

    found_classes = {
        cls.message_type: cls
        for cls in get_all_subclasses(msgs.MarketMessage)
        if hasattr(cls, "message_type") and cls.message_type
    }
    message_class = found_classes.get(message_type_byte)

    if message_class is None:
        message_class = messages.get(message_type_byte)

    if message_class is None:
        pytest.skip(f"No message class found for type {message_type_byte!r}")

    sample_data = TEST_DATA[message_type_byte]
    return message_type_byte, message_class, sample_data


# --- Test Cases ---
def test_market_message_base_timestamp():
    """Tests the timestamp splitting and setting logic in the base class."""
    msg = msgs.MarketMessage()  # noqa: F405
    original_ts = 0x123456789ABC  # Example 6-byte timestamp
    msg.timestamp = original_ts

    ts1, ts2 = msg.split_timestamp()

    # Expected values based on 6 bytes (48 bits)
    # High 32 bits (first 4 bytes of 6 bytes)
    # Note: Python treats the 6 bytes as the lower part of a 64-bit int
    # So 0x123456789ABC >> 32 = 0x12
    # And ts2 = 0x123456789ABC - (0x12 << 32) = 0x3456789ABC
    # Let's test with the actual DEFAULT_TIMESTAMP which is likely larger
    ts_large = DEFAULT_TIMESTAMP  # 1651500000 * 1_000_000_000
    msg.timestamp = ts_large
    ts1_large, ts2_large = msg.split_timestamp()

    # Reconstruct
    msg.set_timestamp(ts1_large, ts2_large)
    assert msg.timestamp == ts_large

    # Check split values manually (example)
    # ts_large = 1651500000000000000 (0x16F_D944_68B4_0000) -> Python int
    # Actual ITCH 6-byte ts would be the lower 48 bits
    ts_48bit = ts_large & ((1 << 48) - 1)  # Mask to get lower 48 bits
    msg.timestamp = ts_48bit  # Simulate setting from 48-bit source

    expected_ts1 = ts_48bit >> 32
    expected_ts2 = ts_48bit & 0xFFFFFFFF  # Lower 32 bits

    ts1_real, ts2_real = msg.split_timestamp()

    assert ts1_real == expected_ts1
    assert ts2_real == expected_ts2

    msg.set_timestamp(ts1_real, ts2_real)
    assert msg.timestamp == ts_48bit


def test_market_message_decode_price():
    """Tests the price decoding logic."""
    msg = msgs.AddOrderNoMPIAttributionMessage.__new__(
        msgs.AddOrderNoMPIAttributionMessage
    )
    msg.price_precision = 4
    msg.price = 1234567  # Integer representation (123.4567)
    assert msg.decode_price("price") == pytest.approx(123.4567)

    msg_mwcb = msgs.MWCBDeclineLeveMessage.__new__(msgs.MWCBDeclineLeveMessage)
    msg_mwcb.price_precision = 8
    msg_mwcb.level1_price = 12345678901  # Integer (123.45678901)
    assert msg_mwcb.decode_price("level1_price") == pytest.approx(123.45678901)

    # Test with a non-price attribute 
    # (should ideally raise error or handle gracefully)
    msg.stock = b"XYZ"
    # decode_price expects the attribute to be numeric.
    # This case might not naturally occur if called correctly, 
    # but good to know behavior.
    with pytest.raises(TypeError):  # Attempting division on bytes
        msg.decode_price("stock")

    # Test trying to decode a method
    with pytest.raises(ValueError, match="Please check the price attribute for pack"):
        msg.decode_price("pack")


# Helper Function for Verifying Unpacked Attributes
def _verify_unpacked_attributes(instance, message_class, sample_data):
    """Verifies attributes of the message object after unpacking."""
    for key, expected_value_original in sample_data.items():
        assert hasattr(instance, key), (
            f"Attribute '{key}' missing after unpack in {message_class.__name__}"
        )
        actual_value = getattr(instance, key)

        if key == "timestamp":
            expected_48bit_timestamp = expected_value_original & ((1 << 48) - 1)
            assert actual_value == expected_48bit_timestamp, (
                f"Unpacked attr '{key}' mismatch: Expected 48-bit value "
                f"{expected_48bit_timestamp}, Got {actual_value}"
            )
            continue

        # Define price/level/collar/dlcr fields
        is_price_field = "price" in key and key not in [
            "price_precision",
            "decode_price",
        ]
        is_level_field = key.startswith("level") and "price" in key
        is_collar_field = "collar" in key and key not in ["auction_collar_extention"]
        is_dlcr_price_field = key in [
            "minimum_allowable_price",
            "maximum_allowable_price",
            "near_execution_price",
            "lower_price_range_collar",
            "upper_price_range_collar",
        ]

        if is_price_field or is_level_field or is_collar_field or is_dlcr_price_field:
            assert isinstance(actual_value, int), (
                f"Unpacked attr '{key}' should be int, got {type(actual_value)}"
            )
            assert actual_value == expected_value_original, (
                f"Unpacked attr '{key}' mismatch: Expected "
                f"{expected_value_original}, Got {actual_value}"
            )
        elif isinstance(expected_value_original, bytes):
            assert isinstance(actual_value, bytes), (
                f"Unpacked attr '{key}' should be bytes, got {type(actual_value)}"
            )
            # Special check for reserved field padding difference
            if message_class is msgs.StockTradingActionMessage and key == "reserved":
                assert (
                    actual_value == b"\x00"
                )  # Check against the actual unpacked value
            else:
                assert actual_value == expected_value_original, (
                    f"Unpacked attr '{key}' mismatch: Expected "
                    f"{expected_value_original!r}, Got {actual_value!r}"
                )
        elif isinstance(expected_value_original, str):
            # Check type it *should* be after unpacking based on class def
            if isinstance(getattr(message_class, key, None), bytes):
                assert isinstance(actual_value, bytes), (
                    f"Unpacked attr '{key}' should be bytes (from str data)," 
                    f"got {type(actual_value)}"
                )
                assert actual_value == expected_value_original.encode("ascii"), (
                    f"Unpacked attr '{key}' mismatch: Expected "
                    f"{expected_value_original.encode('ascii')!r}, Got {actual_value!r}"
                )
            else:  # Should be str (unlikely with struct)
                assert isinstance(actual_value, str), (
                    f"Unpacked attr '{key}' should be str, got {type(actual_value)}"
                )
                assert actual_value == expected_value_original, (
                    f"Unpacked attr '{key}' mismatch: Expected "
                    f"{expected_value_original!r}, Got {actual_value!r}"
                )
        else:  # Other types (int, bool etc.)
            assert type(actual_value) is type(expected_value_original), (
                f"Unpacked attr '{key}' type mismatch: Expected "
                f"{type(expected_value_original)}, Got {type(actual_value)}"
            )
            assert actual_value == expected_value_original, (
                f"Unpacked attr '{key}' mismatch: Expected "
                f"{expected_value_original}, Got {actual_value}"
            )


# Helper Function for Verifying Decoded Attributes
def _verify_decoded_attributes(decoded_object, instance, message_class, sample_data):
    """Verifies attributes of the decoded dataclass object."""
    for key, expected_value_original in sample_data.items():
        assert hasattr(decoded_object, key), (
            f"Attribute '{key}' missing in decoded {message_class.__name__}"
        )
        decoded_value = getattr(decoded_object, key)

        if key == "timestamp":
            expected_48bit_timestamp = expected_value_original & ((1 << 48) - 1)
            assert decoded_value == expected_48bit_timestamp, (
                f"Decoded attr '{key}' mismatch: Expected 48-bit value "
                f"{expected_48bit_timestamp}, Got {decoded_value}"
            )
            continue

        # Define price/level/collar/dlcr fields
        is_price_field = "price" in key and key not in [
            "price_precision",
            "decode_price",
        ]
        is_level_field = key.startswith("level") and "price" in key
        is_collar_field = "collar" in key and key not in ["auction_collar_extention"]
        is_dlcr_price_field = key in [
            "minimum_allowable_price",
            "maximum_allowable_price",
            "near_execution_price",
            "lower_price_range_collar",
            "upper_price_range_collar",
        ]

        if is_price_field or is_level_field or is_collar_field or is_dlcr_price_field:
            # Use instance's precision as decode relies on it
            precision = getattr(instance, "price_precision", 4)
            if key in ["level1_price", "level2_price", "level3_price"]:
                precision = 8
            expected_float = float(expected_value_original) / (10**precision)
            assert isinstance(decoded_value, float), (
                f"Decoded attr '{key}' should be float, got {type(decoded_value)}"
            )
            assert decoded_value == pytest.approx(expected_float), (
                f"Decoded attr '{key}' mismatch: Expected approx "
                f"{expected_float}, Got {decoded_value}"
            )
        elif isinstance(expected_value_original, bytes):
            expected_str = expected_value_original.decode("ascii").rstrip()
            assert isinstance(decoded_value, str), (
                f"Decoded attr '{key}' should be str, got {type(decoded_value)}"
            )
            # Handle reserved field specifically if needed in decoded output
            if message_class is msgs.StockTradingActionMessage and key == "reserved":
                assert (
                    decoded_value == b"\x00".decode("ascii").rstrip()
                )  # Decode/rstrip expected value
            else:
                assert decoded_value == expected_str, (
                    f"Decoded attr '{key}' mismatch: Expected "
                    f"{expected_str!r}, Got {decoded_value!r}"
                )
        elif isinstance(expected_value_original, str):
            # If original was string, compare directly 
            # (decode handles stripping for bytes fields)
            if isinstance(getattr(message_class, key, None), bytes):
                expected_str = expected_value_original.rstrip()
                assert decoded_value == expected_str, (
                    f"Decoded attribute '{key}' mismatch: Expected "
                    f"{expected_str!r}, Got {decoded_value!r}"
                )
            else:  # If original was string and class field is string
                assert decoded_value == expected_value_original, (
                    f"Decoded attribute '{key}' mismatch: Expected "
                    f"{expected_value_original!r}, Got {decoded_value!r}"
                )
        else:  # Other types (int, bool etc.) should match directly
            assert decoded_value == expected_value_original, (
                f"Decoded attr '{key}' mismatch: Expected "
                f"{expected_value_original}, Got {decoded_value}"
            )


def test_pack_unpack_decode_consistency(message_params):
    """
    Tests message lifecycle: pack -> unpack -> verify -> repack -> decode -> verify.
    Relies on helper functions for verification steps.
    """
    message_type_byte, message_class, sample_data = message_params

    print(f"\nTesting: {message_class.__name__} ({message_type_byte.decode()})")

    # Step 1: Pack sample data
    try:
        expected_packed_message = pack_message_data(message_class, sample_data)
    except Exception as e:
        pytest.fail(f"Failed to pack sample data for {message_class.__name__}: {e}")

    assert expected_packed_message.startswith(message_type_byte)
    assert len(expected_packed_message) == message_class.message_size, (
        f"Packed size mismatch for {message_class.__name__}: Expected "
        f"{message_class.message_size}, Got {len(expected_packed_message)}"
    )

    # Step 2: Initialize from bytes
    try:
        instance = message_class(expected_packed_message)
    except Exception as e:
        pytest.fail(
            f"Failed to initialize {message_class.__name__} from packed bytes: {e}"
        )

    # Step 2 Verification: Check attributes after initialization
    _verify_unpacked_attributes(instance, message_class, sample_data)

    # Step 3: Pack the initialized object and compare
    repacked_message = instance.pack()
    assert repacked_message == expected_packed_message, (
        f"Repacked message does not match original for {message_class.__name__}"
    )

    # Step 4: Decode the object and verify
    try:
        decoded_object = instance.decode(prefix="Test")
    except Exception as e:
        pytest.fail(f"Failed to decode {message_class.__name__}: {e}")

    assert is_dataclass(decoded_object), (
        f"Decoded object for {message_class.__name__} is not a dataclass"
    )
    assert decoded_object.__class__.__name__ == f"Test{message_class.__name__}"

    # Step 4 Verification: Check decoded attributes 
    _verify_decoded_attributes(decoded_object, instance, message_class, sample_data)


def test_get_attributes(message_params):
    """Tests the get_attributes method."""
    _, message_class, sample_data = message_params
    # Create a dummy instance
    packed_message = pack_message_data(message_class, sample_data)
    instance = message_class(packed_message)

    non_callable_attrs = instance.get_attributes(call_able=False)
    callable_attrs = instance.get_attributes(call_able=True)

    # Check some expected non-callable attributes
    assert "message_type" in non_callable_attrs
    assert "description" in non_callable_attrs
    assert "timestamp" in non_callable_attrs
    if "stock" in sample_data:
        assert "stock" in non_callable_attrs
    if "price" in sample_data:
        assert "price" in non_callable_attrs
    if "level1_price" in sample_data:
        assert "level1_price" in non_callable_attrs

    # Check some expected callable attributes
    assert "pack" in callable_attrs
    assert "decode" in callable_attrs
    assert "set_timestamp" in callable_attrs
    assert "split_timestamp" in callable_attrs
    assert "decode_price" in callable_attrs
    assert "get_attributes" in callable_attrs

    # Ensure no overlap
    assert not set(non_callable_attrs) & set(callable_attrs)

    # Ensure attributes from sample data are mostly in non_callable_attrs
    for key in sample_data.keys():
        # Need to handle price precision which is class level but shows up
        if key != "price_precision":
            assert key in non_callable_attrs
