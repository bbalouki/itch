# Nasdaq TotalView-ITCH 5.0 Parser
[![PYPI Version](https://img.shields.io/pypi/v/itchfeed)](https://pypi.org/project/itchfeed/)
[![PyPi status](https://img.shields.io/pypi/status/itchfeed.svg?maxAge=60)](https://pypi.python.org/pypi/itchfeed)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/itchfeed)](https://pypi.org/project/itchfeed/)
[![PyPI Downloads](https://static.pepy.tech/badge/itchfeed)](https://pepy.tech/projects/itchfeed)
[![CodeFactor](https://www.codefactor.io/repository/github/bbalouki/itch/badge)](https://www.codefactor.io/repository/github/bbalouki/itch)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-grey?logo=Linkedin&logoColor=white)](https://www.linkedin.com/in/bertin-balouki-simyeli-15b17a1a6/)
[![PayPal Me](https://img.shields.io/badge/PayPal%20Me-blue?logo=paypal)](https://paypal.me/bertinbalouki?country.x=SN&locale.x=en_US)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

*   [Overview](#overview)
*   [Features](#features)
*   [Installation](#installation)
*   [Usage](#usage)
    *   [Parsing from a Binary File](#parsing-from-a-binary-file)
    *   [Parsing from Raw Bytes](#parsing-from-raw-bytes)
    *   [Creating Messages Programmatically](#creating-messages-programmatically)
    *   [Example with Real-World Sample Data](#example-with-real-world-sample-data)
*   [Interpreting Market Data (Conceptual Overview)](#interpreting-market-data-conceptual-overview)
*   [Supported Message Types](#supported-message-types)
*   [Data Representation](#data-representation)
    *   [Common Attributes of `MarketMessage`](#common-attributes-of-marketmessage)
    *   [Common Methods of `MarketMessage`](#common-methods-of-marketmessage)
    *   [Serializing Messages with `pack()`](#serializing-messages-with-pack)
    *   [Data Types in Parsed Messages](#data-types-in-parsed-messages)
*   [Error Handling](#error-handling)
    *   [Handling Strategies](#handling-strategies)
*   [Contributing](#contributing)
*   [License](#license)
*   [References](#references)

A Python library for parsing binary data conforming to the Nasdaq TotalView-ITCH 5.0 protocol specification. This parser converts the raw byte stream into structured Python objects, making it easier to work with Nasdaq market data.

## Overview

The Nasdaq TotalView-ITCH 5.0 protocol is a binary protocol used by Nasdaq to disseminate full order book depth, trade information, and system events for equities traded on its execution system. This parser handles the low-level details of reading the binary format, unpacking fields according to the specification, and presenting the data as intuitive Python objects.

## Features

*   **Parses ITCH 5.0 Binary Data:** Accurately interprets the binary message structures defined in the official specification.
*   **Supports All Standard Message Types:** Implements classes for all messages defined in the ITCH 5.0 specification (System Event, Stock Directory, Add Order, Trade, etc.).
*   **Object-Oriented Representation:** Each ITCH message type is represented by a dedicated Python class (`SystemEventMessage`, `AddOrderMessage`, etc.), inheriting from a common `MarketMessage` base class.
*   **Flexible Input:** Reads and parses messages from:
    *   Binary files (`.gz` or similar).
    *   Raw byte streams (e.g., from network sockets).
*   **Data Decoding:** Provides a `.decode()` method on each message object to convert it into a human-readable `dataclass` representation, handling:
    *   Byte-to-string conversion (ASCII).
    *   Stripping padding spaces.
    *   Price decoding based on defined precision.
*   **Timestamp Handling:** Correctly reconstructs the 6-byte (48-bit) nanosecond timestamps.
*   **Price Handling:** Decodes fixed-point price fields into floating-point numbers based on the standard 4 or 8 decimal place precision.
*   **Pure Python:** Relies only on the Python standard library. No external dependencies required.

## Installation

The recommended way to install `itchfeed` is from PyPI using `pip`:
```bash
pip install itchfeed
```

If you want to contribute to development or need the latest unreleased version, you can clone the repository:
```bash
git clone https://github.com/bbalouki/itch.git
cd itch
# Then you might install it in editable mode or run tests, etc.
```

After installation (typically via pip), import the necessary modules directly into your Python project:
    ```python
    from itch.parser import MessageParser
    from itch.messages import ModifyOrderMessage
    ```

## Usage

### Parsing from a Binary File

This is useful for processing historical ITCH data stored in files. The `MessageParser` handles buffering efficiently.

```python
from itch.parser import MessageParser
from itch.messages import AddOrderMessage, TradeMessage

# Initialize the parser.
# By default, MessageParser() will parse all known message types.
# Optionally, you can filter for specific messages by providing the `message_type` parameter.
# This parameter takes a bytes string containing the characters of the message types you want to parse.
# For example, to only parse Add Order (No MPID 'A'), Stock Directory ('R'), and Stock Trading Action ('H') messages:
# parser = MessageParser(message_type=b"ARH")
# Refer to the MESSAGES constant in `itch.messages` or the table in the "Supported Message Types"
# section for all available type codes.
parser = MessageParser() # Parses all messages by default

# Path to your ITCH 5.0 data file
itch_file_path = 'path/to/your/data'
# you can find sample data [here](https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/)

# The `read_message_from_file()` method reads the ITCH data in chunks.
# - `cachesize` (optional, default: 65536 bytes): This parameter determines the size of data chunks
#   read from the file at a time. Adjusting this might impact performance for very large files
#   or memory usage, but the default is generally suitable.
# The parsing process stops when either:
# 1. The end of the file is reached.
# 2. A System Event Message (type 'S') with an event_code of 'C' (End of Messages)
#    is encountered, signaling the end of the ITCH feed for the session.

try:
    with open(itch_file_path, 'rb') as itch_file:
        # read_message_from_file returns a list of parsed message objects
        parsed_messages = parser.read_message_from_file(itch_file) # You can also pass cachesize here, e.g., parser.read_message_from_file(itch_file, cachesize=131072)

        print(f"Parsed {len(parsed_messages)} messages.")

        # Process the messages
        for message in parsed_messages:
            # Access attributes directly
            print(f"Type: {message.message_type.decode()}, Timestamp: {message.timestamp}")

            if isinstance(message, AddOrderMessage):
                print(f"  Add Order: Ref={message.order_reference_number}, "
                      f"Side={message.buy_sell_indicator.decode()}, "
                      f"Shares={message.shares}, Stock={message.stock.decode().strip()}, "
                      f"Price={message.decode_price('price')}") 

            elif isinstance(message, TradeMessage): 
                 print(f"  Trade: Match={message.match_number}")
                 # Access specific trade type attributes...

            # Get a human-readable dataclass representation
            decoded_msg = message.decode()
            print(f"  Decoded: {decoded_msg}")

except FileNotFoundError:
    print(f"Error: File not found at {itch_file_path}")
except Exception as e:
    print(f"An error occurred: {e}")

```

### Parsing from Raw Bytes

This is suitable for real-time processing, such as reading from a network stream.

```python
from itch.parser import MessageParser
from itch.messages import AddOrderMessage
from queue import Queue

# Initialize the parser
parser = MessageParser()

# Simulate receiving a chunk of binary data (e.g., from a network socket)
# This chunk contains multiple ITCH messages, each prefixed with 0x00 and length byte
# Example: \x00\x0bS...\x00\x25R...\x00\x27F...
raw_binary_data: bytes = b"..." # Your raw ITCH 5.0 data chunk

# read_message_from_bytes returns a queue of parsed message objects
message_queue: Queue = parser.read_message_from_bytes(raw_binary_data)

print(f"Parsed {message_queue.qsize()} messages from the byte chunk.")

# Process messages from the queue
while not message_queue.empty():
    message = message_queue.get()

    print(f"Type: {message.message_type.decode()}, Timestamp: {message.timestamp}")

    if isinstance(message, AddOrderMessage):
         print(f"  Add Order: Ref={message.order_reference_number}, "
               f"Stock={message.stock.decode().strip()}, Price={message.decode_price('price')}")

    # Use the decoded representation
    decoded_msg = message.decode(prefix="Decoded")
    print(f"  Decoded: {decoded_msg}")

```

### Creating Messages Programmatically

In addition to parsing, `itch` provides a simple way to create ITCH message objects from scratch. This is particularly useful for:
- **Testing:** Generating specific message sequences to test your own downstream applications.
- **Simulation:** Building custom market simulators that produce ITCH-compliant data streams.
- **Data Generation:** Creating custom datasets for analysis or backtesting.

The `create_message` function is the primary tool for this purpose. It takes a `message_type` and keyword arguments corresponding to the desired message attributes.

Here's a basic example of how to create a `SystemEventMessage` to signal the "Start of Messages":

```python
from itch.messages import create_message, SystemEventMessage

# Define the attributes for the message
event_attributes = {
    "stock_locate": 1,
    "tracking_number": 2,
    "timestamp": 1651500000 * 1_000_000_000,
    "event_code": b"O"
}

# Create the message object
system_event_message = create_message(b"S", **event_attributes)

# You can now work with this object just like one from the parser
print(isinstance(system_event_message, SystemEventMessage))
# Expected output: True

print(system_event_message)
# Expected output: SystemEventMessage(description='System Event Message', event_code='O', message_format='!HHHIc', message_pack_format='!cHHHIc', message_size=12, message_type='S', price_precision=4, stock_locate=1, timestamp=86311638581248, tracking_number=2)
```

### Example with Real-World Sample Data

You can also use the sample data provided in `tests/data.py` to create messages, simulating a more realistic scenario.

```python
from itch.messages import create_message, AddOrderNoMPIAttributionMessage
from tests.data import TEST_DATA

# Get the sample data for an "Add Order" message (type 'A')
add_order_data = TEST_DATA[b"A"]

# Create the message
add_order_message = create_message(b"A", **add_order_data)

# Verify the type
print(isinstance(add_order_message, AddOrderNoMPIAttributionMessage))
# Expected output: True

# Access its attributes
print(f"Stock: {add_order_message.stock.decode().strip()}")
# Expected output: Stock: AAPL

print(f"Price: {add_order_message.decode_price('price')}")
# Expected output: Price: 150.1234

# Test all message types in the sample data
for message_type, sample_data in TEST_DATA.items():
    print(f"Creating message of type {message_type}")
    message = create_message(message_type, **sample_data)
    print(f"Created message: {message}")
    print(f"Packed message: {message.pack()}")
    print(f"Message size: {message.message_size}")
    print(f"Message Attributes: {message.get_attributes()}")
    assert len(message.pack()) ==  message.message_size
    print()
```

By leveraging `create_message`, you can build robust test suites for your trading algorithms, compliance checks, or data analysis pipelines without needing a live data feed.

## Interpreting Market Data (Conceptual Overview)

Parsing individual ITCH messages is the first step; understanding market dynamics often requires processing and correlating a sequence of these messages. This library provides the tools to decode messages, but interpreting their collective meaning requires building further logic.

A common use case is to build and maintain a local representation of the order book for a particular stock. Here's a simplified, high-level overview of how different messages interact in this context:

*   **Building the Book:**
    *   `AddOrderNoMPIAttributionMessage` (Type `A`) and `AddOrderMPIDAttribution` (Type `F`) represent new orders being added to the order book. These messages provide the initial size, price, and side (buy/sell) of the order, along with a unique `order_reference_number`.

*   **Modifying and Removing Orders:**
    *   `OrderExecutedMessage` (Type `E`) and `OrderExecutedWithPriceMessage` (Type `C`) indicate that a portion or all of an existing order (identified by `order_reference_number`) has been executed. The executed shares should be subtracted from the remaining quantity of the order on the book. If the execution fully fills the order, it's removed.
    *   `OrderCancelMessage` (Type `X`) indicates that a number of shares from an existing order (identified by `order_reference_number`) have been canceled. The canceled shares should be subtracted from the order's quantity. If this results in zero shares, the order is removed.
    *   `OrderDeleteMessage` (Type `D`) indicates that an entire existing order (identified by `order_reference_number`) has been deleted from the book.
    *   `OrderReplaceMessage` (Type `U`) is effectively a cancel-and-replace operation. The order identified by `order_reference_number` should be removed, and a new order with a `new_order_reference_number` and new characteristics (size, price) should be added to the book.

*   **Observing Trades:**
    *   `NonCrossTradeMessage` (Type `P`) and `CrossTradeMessage` (Type `Q`) provide information about actual trades that have occurred. While `OrderExecutedMessage` and `OrderExecutedWithPriceMessage` detail the impact on specific orders in the book, `TradeMessage` types provide a direct stream of trade prints.

**Important Considerations:**

This is a very simplified overview. Building a complete and accurate order book or a sophisticated trading analysis tool requires:
*   Careful handling of message sequences and their `timestamp` order.
*   Managing state for each `order_reference_number` across multiple messages.
*   Understanding the nuances of different order types, market events (like halts or auctions signaled by `StockTradingActionMessage` or `NOIIMessage`), and how they impact the book.
*   Adhering closely to the official Nasdaq TotalView-ITCH 5.0 specification for detailed business logic.

This library aims to handle the binary parsing, allowing you to focus on implementing this higher-level interpretative logic.

## Supported Message Types

The parser supports the following ITCH 5.0 message types. Each message object has attributes corresponding to the fields defined in the specification. Refer to the class docstrings in `itch.messages` for detailed attribute descriptions.

| Type (Byte) | Class Name                        | Description                                      |
| :---------- | :-------------------------------- | :----------------------------------------------- |
| `S`         | `SystemEventMessage`              | System Event Message. Signals a market or data feed handler event. <br> `event_code` indicates the type: <br> - `O`: Start of Messages <br> - `S`: Start of System Hours <br> - `Q`: Start of Market Hours <br> - `M`: End of Market Hours <br> - `E`: End of System Hours <br> - `C`: End of Messages |
| `R`         | `StockDirectoryMessage`           | Stock Directory Message. Disseminated for all active symbols at the start of each trading day. <br> Key fields include: <br> - `market_category`: (e.g., `Q`: NASDAQ Global Select Market) <br> - `financial_status_indicator`: (e.g., `D`: Deficient) <br> - `issue_classification`: (e.g., `A`: American Depositary Share) <br> - `issue_sub_type`: (e.g., `AI`: ADR representing an underlying foreign issuer) |
| `H`         | `StockTradingActionMessage`       | Stock Trading Action Message. Indicates the current trading status of a security. <br> Key fields: <br> - `trading_state`: (e.g., `H`: Halted, `T`: Trading) <br> - `reason`: (e.g., `T1`: Halt due to news pending) |
| `Y`         | `RegSHOMessage`                   | Reg SHO Short Sale Price Test Restricted Indicator. <br> `reg_sho_action` indicates status: <br> - `0`: No price test in place <br> - `1`: Restriction in effect (intra-day drop) <br> - `2`: Restriction remains in effect |
| `L`         | `MarketParticipantPositionMessage`| Market Participant Position message. Provides status for each Nasdaq market participant firm in an issue. <br> Key fields: <br> - `primary_market_maker`: (e.g., `Y`: Yes, `N`: No) <br> - `market_maker_mode`: (e.g., `N`: Normal) <br> - `market_participant_state`: (e.g., `A`: Active) |
| `V`         | `MWCBDeclineLeveMessage`          | Market-Wide Circuit Breaker (MWCB) Decline Level Message. Informs recipients of the daily MWCB breach points. |
| `W`         | `MWCBStatusMessage`               | Market-Wide Circuit Breaker (MWCB) Status Message. Informs when a MWCB level has been breached. |
| `K`         | `IPOQuotingPeriodUpdateMessage`   | IPO Quoting Period Update Message. Indicates anticipated IPO quotation release time. |
| `J`         | `LULDAuctionCollarMessage`        | LULD Auction Collar Message. Indicates auction collar thresholds for a paused security. |
| `h`         | `OperationalHaltMessage`          | Operational Halt Message. Indicates an interruption of service on the identified security impacting only the designated Market Center. |
| `A`         | `AddOrderNoMPIAttributionMessage` | Add Order (No MPID Attribution). A new unattributed order has been accepted and added to the displayable book. |
| `F`         | `AddOrderMPIDAttribution`         | Add Order (MPID Attribution). A new attributed order or quotation has been accepted. |
| `E`         | `OrderExecutedMessage`            | Order Executed Message. An order on the book has been executed in whole or in part. |
| `C`         | `OrderExecutedWithPriceMessage`   | Order Executed With Price Message. An order on the book has been executed at a price different from its initial display price. |
| `X`         | `OrderCancelMessage`              | Order Cancel Message. An order on the book is modified due to a partial cancellation. |
| `D`         | `OrderDeleteMessage`              | Order Delete Message. An order on the book is being cancelled. |
| `U`         | `OrderReplaceMessage`             | Order Replace Message. An order on the book has been cancel-replaced. |
| `P`         | `NonCrossTradeMessage`            | Trade Message (Non-Cross). Provides execution details for normal match events involving non-displayable order types. |
| `Q`         | `CrossTradeMessage`               | Cross Trade Message. Indicates completion of a cross process (Opening, Closing, Halt/IPO) for a specific security. |
| `B`         | `BrokenTradeMessage`              | Broken Trade / Order Execution Message. An execution on Nasdaq has been broken. |
| `I`         | `NOIIMessage`                     | Net Order Imbalance Indicator (NOII) Message. <br> Key fields: <br> - `cross_type`: Context of the imbalance (e.g., `O`: Opening Cross, `C`: Closing Cross, `H`: Halt/IPO Cross, `A`: Extended Trading Close). <br> - `price_variation_indicator`: Deviation of Near Indicative Clearing Price from Current Reference Price (e.g., `L`: Less than 1%). <br> - `imbalance_direction`: (e.g., `B`: Buy imbalance, `S`: Sell imbalance, `N`: No imbalance, `O`: Insufficient orders to calculate) |
| `N`         | `RetailPriceImprovementIndicator` | Retail Price Improvement Indicator (RPII). Identifies retail interest on Bid, Ask, or both. |
| `O`         | `DLCRMessage`                     | Direct Listing with Capital Raise Message. Disseminated for DLCR securities once volatility test passes. |

## Data Representation

All message classes inherit from `itch.messages.MarketMessage`. This base class provides a common structure and utility methods for all ITCH message types.

### Common Attributes of `MarketMessage`

Each instance of a `MarketMessage` (and its subclasses) will have the following attributes:

*   `message_type` (bytes): A single byte character identifying the type of the ITCH message (e.g., `b'S'` for System Event, `b'A'` for Add Order).
*   `description` (str): A human-readable description of the message type (e.g., "System Event Message", "Add Order No MPID Attribution Message").
*   `message_format` (str): An internal string defining the `struct` format for packing/unpacking the core message fields. This is primarily for internal parser use.
*   `message_pack_format` (str): An internal string, often similar to `message_format`, specifically for packing operations. This is primarily for internal parser use.
*   `message_size` (int): The size of the binary message in bytes, as read from the message header or defined by the specification.
*   `timestamp` (int): A 64-bit integer representing the time of the event in nanoseconds since midnight. This is reconstructed from the 6-byte raw timestamp. See `set_timestamp()` and `split_timestamp()` methods.
*   `stock_locate` (int): A code used to identify the stock for Nasdaq messages. Usually, this is the first field after the Message Type.
*   `tracking_number` (int): A tracking number assigned by Nasdaq to each message.
*   `price_precision` (int): An integer (typically 4 or 8) indicating the number of decimal places for price fields within this message type. This is crucial for correctly interpreting price data. See `decode_price()`.

### Common Methods of `MarketMessage`

The `MarketMessage` base class, and therefore all specific message classes, provide these useful methods:

*   `set_timestamp(timestamp_high: int, timestamp_low: int)`:
    *   This method is typically used internally by the parser. It reconstructs the full 48-bit nanosecond timestamp from two parts provided by unpacking the raw message bytes.
    *   `timestamp_high`: The higher-order 2 bytes (16 bits) of the 6-byte ITCH timestamp.
    *   `timestamp_low`: The lower-order 4 bytes (32 bits) of the 6-byte ITCH timestamp.
    *   These are combined to set the `timestamp` attribute (a 64-bit integer representing nanoseconds since midnight) of the message object. The full 48-bit value is stored within this 64-bit integer.
*   `split_timestamp(timestamp_nanoseconds: int = None) -> tuple[int, int]`:
    *   Takes an optional 64-bit integer timestamp (nanoseconds since midnight); if `None`, it uses the message's current `timestamp` attribute (which holds the 48-bit value).
    *   Splits this timestamp into two integer components: the higher-order 2 bytes (16 bits) and the lower-order 4 bytes (32 bits), matching how they are packed in the raw ITCH message. This is primarily for internal use during packing.
*   `decode_price(attribute_name: str) -> float`:
    *   Takes the string name of a price attribute within the message object (e.g., `'price'`, `'execution_price'`).
    *   Retrieves the raw integer value of that attribute.
    *   Divides the raw integer by `10 ** self.price_precision` to convert it into a floating-point number with the correct decimal places. For example, if `price_precision` is 4 and the raw price is `1234500`, this method returns `123.45`.
*   `decode() -> dataclass`:
    *   This is a key method for usability. It processes the raw byte fields of the message object and converts them into a more human-readable Python `dataclass`.
    *   Specifically, it:
        *   Converts alpha-numeric byte strings (like stock symbols or MPIDs) into standard Python strings, stripping any right-padding spaces.
        *   Converts price fields into floating-point numbers using the `decode_price()` logic internally.
        *   Keeps other fields (like share counts or reference numbers) in their appropriate integer or byte format if no further conversion is needed.
    *   The returned `dataclass` provides a clean, immutable, and easily inspectable representation of the message content.
*   `get_attributes() -> dict`:
    *   Returns a dictionary of all attributes (fields) of the message instance, along with their current values.
    *   This can be useful for generic inspection or logging of message contents without needing to know the specific type of the message beforehand.

### Serializing Messages with `pack()`

Each specific message class (e.g., `SystemEventMessage`, `AddOrderNoMPIAttributionMessage`) also provides a `pack()` method. This method is the inverse of the parsing process.

*   **Purpose:** It serializes the message object, with its current attribute values, back into its raw ITCH 5.0 binary format. The output is a `bytes` object representing the exact byte sequence that would appear in an ITCH data feed for that message.
*   **Usefulness:**
    *   **Generating Test Data:** Create custom ITCH messages for testing your own ITCH processing applications.
    *   **Modifying Messages:** Parse an existing message, modify some of its attributes, and then `pack()` it back into binary form.
    *   **Creating Custom ITCH Feeds:** While more involved, you could use this to construct sequences of ITCH messages for specialized scenarios.

**Example:**

```python
from itch.messages import SystemEventMessage
import time

# 1. Create a SystemEventMessage instance.
#    For direct packing, you need to provide all fields that are part of its `message_pack_format`.
#    The `SystemEventMessage` constructor in `itch.messages` expects the raw bytes of the message body
#    (excluding the common message type, stock_locate, tracking_number, and timestamp parts that are
#    handled by its `__init__` if you were parsing).
#    When creating from scratch for packing, it's often easier to instantiate and then set attributes.
#    Let's assume SystemEventMessage can be instantiated with default or required values.
#    (Note: The actual SystemEventMessage.__init__ takes raw message bytes, so direct instantiation
#     for packing requires setting attributes manually if not using raw bytes for construction)

event_msg = SystemEventMessage.__new__(SystemEventMessage) # Create instance without calling __init__
event_msg.message_type = b'S' # Must be set for pack() to know its type
event_msg.stock_locate = 0 # Placeholder or actual value
event_msg.tracking_number = 0 # Placeholder or actual value
event_msg.event_code = b'O' # Example: Start of Messages

# 2. Set the timestamp.
#    The `timestamp` attribute (nanoseconds since midnight) must be set.
#    The `pack()` method will internally use `split_timestamp()` to get the parts.
current_nanoseconds = int(time.time() * 1e9) % (24 * 60 * 60 * int(1e9))
event_msg.timestamp = current_nanoseconds # Directly set the nanosecond timestamp

# 3. Pack the message into binary format.
#    The pack() method prepends the message type and then packs stock_locate,
#    tracking_number, the split timestamp, and then the message-specific fields.
packed_bytes = event_msg.pack()

# 4. The result is a bytes object
print(f"Packed {len(packed_bytes)} bytes: {packed_bytes.hex().upper()}")
print(f"Type of packed_bytes: {type(packed_bytes)}")

# Example Output (will vary based on actual timestamp and other values if not fixed):
# Packed 12 bytes: 53000000002F39580A004F
# Type of packed_bytes: <class 'bytes'>
```
The `message_pack_format` attribute of each message class dictates how its fields are packed. Note that for messages read by the `MessageParser`, fields like `stock_locate` and `tracking_number` are prepended during parsing; when packing an object directly, ensure all fields defined in its `message_pack_format` are appropriately set.

### Data Types in Parsed Messages

*   **Strings:** Alpha fields (e.g., stock symbols, MPIDs) are initially parsed as `bytes`. The `decode()` method converts these to standard Python strings (ASCII) and typically removes any right-padding spaces used in the fixed-width ITCH fields.
*   **Prices:** As mentioned under `decode_price()`, price fields are stored as raw integers in the initial message object. The `decode_price()` method or the comprehensive `decode()` method should be used to obtain correctly scaled floating-point values.
*   **Timestamps:** Handled by `set_timestamp()` and `split_timestamp()` as described above, resulting in a nanosecond-precision integer for the `timestamp` attribute.
*   **Decoded Objects:** The `message.decode()` method is the recommended way to get a fully processed, user-friendly representation of any message, with all fields converted to appropriate Python types (strings, floats, integers).

## Error Handling

When parsing ITCH data, the `MessageParser` may encounter issues due to malformed data, incorrect file formats, or unexpected message types. These situations typically result in a `ValueError` being raised.

Common scenarios that can lead to a `ValueError` include:

*   **Unexpected Byte:** When reading from a file or a raw byte stream, each ITCH message is expected to be prefixed by a `0x00` byte followed by a byte indicating the length of the upcoming message. If the parser encounters a byte other than `0x00` where this prefix is expected, it suggests data corruption, that the file is not a valid ITCH feed, or that the stream is out of sync.
*   **Unknown Message Type:** After successfully reading the length-prefixed message, the first byte of the actual message content indicates its type (e.g., `S` for System Event, `A` for Add Order). If this byte does not correspond to one of the known ITCH 5.0 message types, the parser will raise an error.
*   **Malformed Message Structure:** Even if the message type is known, errors can occur if the message's length does not match the expected length for that type, or if the internal structure cannot be unpacked correctly according to the defined format. This often points to data corruption or a non-standard message.

### Handling Strategies

It's crucial to anticipate these errors in your application:

*   **Use `try-except` Blocks:** Wrap your parsing calls (especially `read_message_from_file` or `read_message_from_bytes`) in `try-except ValueError as e:` blocks.
    ```python
    try:
        # ... parsing operations ...
        messages = parser.read_message_from_file(itch_file)
    except ValueError as e:
        print(f"An error occurred during parsing: {e}")
        # Log the error, problematic data chunk, or take other actions
    ```
*   **Logging:** When an error is caught, log the exception details. If possible, log the problematic chunk of data that caused the error. This is invaluable for debugging and understanding the nature of the data issue.
*   **Application-Specific Decisions:**
    *   **Skip and Continue:** For some applications, it might be acceptable to log the error, skip the problematic message or data chunk, and attempt to continue parsing the rest of the stream/file. This can be useful for robustly processing large datasets where a small amount of corrupted data is tolerable.
    *   **Halt Processing:** In other scenarios, particularly where data integrity is paramount, any parsing error might necessitate halting the entire process and flagging the data source as invalid.

Choosing the right strategy depends on the requirements of your application and the expected quality of your ITCH data sources.

## Contributing

Contributions are welcome! If you find a bug, have a suggestion, or want to add a feature:

1.  **Check Issues:** See if an issue for your topic already exists.
2.  **Open an Issue:** If not, open a new issue describing the bug or feature request.
3.  **Fork and Branch:** Fork the repository and create a new branch for your changes.
4.  **Implement Changes:** Make your code changes, ensuring adherence to the ITCH 5.0 specification. Add tests if applicable.
5.  **Submit Pull Request:** Open a pull request from your branch to the main repository, referencing the relevant issue.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## References
*   **Nasdaq TotalView-ITCH 5.0 Specification:** The official [documentation](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf) is the definitive source for protocol details.
