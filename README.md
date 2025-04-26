# Nasdaq TotalView-ITCH 5.0 Parser
[![PYPI Version](https://img.shields.io/pypi/v/itchfeed)](https://pypi.org/project/itchfeed/)
[![PyPi status](https://img.shields.io/pypi/status/itchfeed.svg?maxAge=60)](https://pypi.python.org/pypi/itchfeed)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/itchfeed)](https://pypi.org/project/itchfeed/)
[![CodeFactor](https://www.codefactor.io/repository/github/bbalouki/itch/badge)](https://www.codefactor.io/repository/github/bbalouki/itch)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-grey?logo=Linkedin&logoColor=white)](https://www.linkedin.com/in/bertin-balouki-simyeli-15b17a1a6/)
[![PayPal Me](https://img.shields.io/badge/PayPal%20Me-blue?logo=paypal)](https://paypal.me/bertinbalouki?country.x=SN&locale.x=en_US)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
*   **Pure Python:** Relies only on the Python standard library . No external dependencies required.

## Installation

You can install this project using ``pip``

1.  **Clone the repository (or download the source code):**
    ```bash
    pip install itchfeed
    ```
2.  **Import the necessary modules** directly into your Python project:
    ```python
    from itch.parser import MessageParser
    from itch.messages import ModifyOrderMessage
    ```

## Usage

### Parsing from a Binary File

This is useful for processing historical ITCH data stored in files. The `MessageParser` handles buffering efficiently.

```python
from itch import MessageParser
from itch.messages import AddOrderMessage, TradeMessage

# Initialize the parser. Optionally filter messages by type.
# parser = MessageParser(message_type=b"AP") # Only parse AddOrder and NonCrossTrade messages
parser = MessageParser()

# Path to your ITCH 5.0 data file
itch_file_path = 'path/to/your/data'
# you can find sample data [here](https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/)

try:
    with open(itch_file_path, 'rb') as itch_file:
        # read_message_from_file returns a list of parsed message objects
        parsed_messages = parser.read_message_from_file(itch_file)

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
from itch import MessageParser
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

## Supported Message Types

The parser supports the following ITCH 5.0 message types. Each message object has attributes corresponding to the fields defined in the specification. Refer to the class docstrings in `itch.messages` for detailed attribute descriptions.

| Type (Byte) | Class Name                        | Description                                      |
| :---------- | :-------------------------------- | :----------------------------------------------- |
| `S`         | `SystemEventMessage`              | System Event Message                             |
| `R`         | `StockDirectoryMessage`           | Stock Directory Message                          |
| `H`         | `StockTradingActionMessage`       | Stock Trading Action Message                     |
| `Y`         | `RegSHOMessage`                   | Reg SHO Short Sale Price Test Restricted Indicator |
| `L`         | `MarketParticipantPositionMessage`| Market Participant Position message              |
| `V`         | `MWCBDeclineLeveMessage`          | Market-Wide Circuit Breaker (MWCB) Decline Level |
| `W`         | `MWCBStatusMessage`               | Market-Wide Circuit Breaker (MWCB) Status        |
| `K`         | `IPOQuotingPeriodUpdateMessage`   | IPO Quoting Period Update Message                |
| `J`         | `LULDAuctionCollarMessage`        | LULD Auction Collar Message                      |
| `h`         | `OperationalHaltMessage`          | Operational Halt Message                         |
| `A`         | `AddOrderNoMPIAttributionMessage` | Add Order (No MPID Attribution)                  |
| `F`         | `AddOrderMPIDAttribution`         | Add Order (MPID Attribution)                     |
| `E`         | `OrderExecutedMessage`            | Order Executed Message                           |
| `C`         | `OrderExecutedWithPriceMessage`   | Order Executed With Price Message                |
| `X`         | `OrderCancelMessage`              | Order Cancel Message                             |
| `D`         | `OrderDeleteMessage`              | Order Delete Message                             |
| `U`         | `OrderReplaceMessage`             | Order Replace Message                            |
| `P`         | `NonCrossTradeMessage`            | Trade Message (Non-Cross)                        |
| `Q`         | `CrossTradeMessage`               | Cross Trade Message                              |
| `B`         | `BrokenTradeMessage`              | Broken Trade / Order Execution Message           |
| `I`         | `NOIIMessage`                     | Net Order Imbalance Indicator (NOII) Message     |
| `N`         | `RetailPriceImprovementIndicator` | Retail Price Improvement Indicator (RPII)        |
| `O`         | `DLCRMessage`                     | Direct Listing with Capital Raise Message        |

## Data Representation

*   **Base Class:** All message classes inherit from `itch.messages.MarketMessage`. This base class provides common attributes like `message_type`, `description`, `stock_locate`, `tracking_number`, and `timestamp`.
*   **Timestamp:** Timestamps are stored as 64-bit integers representing nanoseconds since midnight. The `set_timestamp` and `split_timestamp` methods handle the conversion from/to the 6-byte representation used in the raw messages.
*   **Prices:** Price fields (e.g., `price`, `execution_price`, `level1_price`) are stored as integers in the raw message objects. Use the `message.decode_price('attribute_name')` method to get the correctly scaled floating-point value (usually 4 or 8 decimal places, defined by `message.price_precision`).
*   **Strings:** Alpha fields are stored as `bytes`. The `.decode()` method converts these to ASCII strings and removes right-padding spaces.
*   **Decoded Objects:** The `message.decode()` method returns a standard Python `dataclass` instance. This provides a clean, immutable, and easily inspectable representation of the message content with correct data types (float for prices, string for text).

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
