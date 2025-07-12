import struct
from dataclasses import make_dataclass
from typing import Dict, List, Tuple, Type

MESSAGES = b"SAFECXDUBHRYPQINLVWKJhO"


class MarketMessage(object):
    """
    The TotalView ITCH feed is composed of a series of messages that describe orders added to, removed from, and executed
    on Nasdaq as well as disseminate Cross and Stock Directory information.
    This is the base class for all message type.

    All Message have the following attributes:
    - message_type: A single letter that identify the message
    - description: Describe the message
    - message_format: string format using to unpack the message
    - message_pack_format: string format using to pack the message
    - message_size: The size in bytes of the message
    - timestamp: Time at which the message was generated (Nanoseconds past midnight)
    - stock_locate: Locate code identifying the security
    - tracking_number: Nasdaq internal tracking number
    """

    message_type: bytes
    description: str
    message_format: str
    message_pack_format: str
    message_size: int
    timestamp: int
    stock_locate: int
    tracking_number: int
    price_precision: int = 4

    def __repr__(self):
        return repr(self.decode())

    def pack(self) -> bytes:
        """
        Packs the message into bytes using the defined message_pack_format.
        This method should be overridden by subclasses to include specific fields.
        """
        pass

    def set_timestamp(self, ts1: int, ts2: int):
        """
        Reconstructs a 6-byte timestamp (48 bits) from two 32-bit unsigned integers.

        This method combines the high 32 bits (`ts1`) and low 32 bits (`ts2`) into a single
        64-bit integer to reconstruct the complete timestamp. For more details on how the
        timestamp is processed and split, refer to the `split_timestamp()` method.

        Args:
            ts1 (int): The high-order 32 bits (most significant 32 bits).
            ts2 (int): The low-order 32 bits (least significant 32 bits).
        """
        self.timestamp = ts2 | (ts1 << 32)

    def split_timestamp(self) -> Tuple[int, int]:
        """
        Splits a 6-byte timestamp (48 bits) into two 32-bit unsigned integers.

        The ITCH protocol defines the timestamp as a **6-byte (48-bit) unsigned integer**.
        Python's native `struct` module does not support 6-byte integers, so we manage
        the timestamp as a 64-bit integer for simplicity. This method splits it into two
        32-bit integers for easier handling, packing, and unpacking.

        Process:
            1. The timestamp is a 6-byte unsigned integer that we treat as a 64-bit integer
               for ease of use (since Python handles 64-bit integers natively).
            2. We extract the **high 32 bits** (most significant bits) and the **low 32 bits**
               (least significant bits) using bitwise operations.

            - The high 32 bits are extracted by shifting the 64-bit timestamp 32 bits to the right
              (`self.timestamp >> 32`).
            - The low 32 bits are isolated by subtracting the high 32 bits (shifted back to the left)
              from the original 64-bit value (`self.timestamp - (ts1 << 32)`).

        Returns:
            Tuple[int, int]: A tuple containing two integers:
                - `ts1`: The high 32 bits (most significant 32 bits)
                - `ts2`: The low 32 bits (least significant 32 bits)

        Example:
            If `self.timestamp = 0x123456789ABC` (in hex, which is 6 bytes long),
            then:
                ts1 = 0x12345678  # high 32 bits
                ts2 = 0x9ABCDEF0  # low 32 bits
        """
        ts1 = self.timestamp >> 32
        ts2 = self.timestamp - (ts1 << 32)
        return (ts1, ts2)
        ts1 = self.timestamp >> 32
        ts2 = self.timestamp - (ts1 << 32)
        return (ts1, ts2)

    def decode_price(self, price_attr: str) -> float:
        precision = getattr(self, "price_precision")
        price = getattr(self, price_attr)
        if callable(price):
            raise ValueError(f"Please check the price attribute for {price_attr}")
        return price / (10**precision)

    def decode(self, prefix: str = ""):
        """
        Converts the message into a human-readable dataclass with all built-in fields.
        - All bytes fields are converted to ASCII strings.
        - Trailing spaces are stripped from ASCII fields (left-justified padded).

        Args:
            prefix : The prefix to the dataclass create from the Original message
        """
        builtin_attrs = {}
        for attr in dir(self):
            if attr.startswith("__"):
                continue
            value = getattr(self, attr)
            if "price" in attr and attr != "price_precision" and attr != "decode_price":
                value = self.decode_price(attr)
            if callable(value):
                continue
            if isinstance(value, (int, float, str, bool)):
                builtin_attrs[attr] = value
            elif isinstance(value, bytes):
                try:
                    builtin_attrs[attr] = value.decode(encoding="ascii").rstrip()
                except UnicodeDecodeError:
                    builtin_attrs[attr] = value
        fields = [(k, type(v)) for k, v in builtin_attrs.items()]

        decoded_class_name = f"{prefix}{self.__class__.__name__}"
        DecodedMessageClass = make_dataclass(decoded_class_name, fields)
        return DecodedMessageClass(**builtin_attrs)

    def get_attributes(self, call_able=False) -> List[str]:
        attrs = [attr for attr in dir(self) if not attr.startswith("__")]
        if call_able:
            return [a for a in attrs if callable(getattr(self, a))]
        else:
            return [a for a in attrs if not callable(getattr(self, a))]


class SystemEventMessage(MarketMessage):
    """
    The system event message type is used to signal a market or data feed handler event.

    Attributes:
        - event_code: see ``itch.indicators.SYSTEM_EVENT_CODES``
    """

    message_type = b"S"
    description = "System Event Message"
    message_format = "!HHHIc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    event_code: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.event_code,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.event_code,
        )
        return message


class StockDirectoryMessage(MarketMessage):
    """
    At the start of each trading day, Nasdaq disseminates stock directory messages for all active symbols in the Nasdaq
    execution system.

    Market data redistributors should process this message to populate the Financial Status Indicator (required displayfield) and
    the Market Category (recommended display field) for Nasdaq listed issues

    Attributes:
        - stock : Denotes the security symbol for the issue in the Nasdaq execution system.

        - market_category : see  ``itch.indicators.MARKET_CATEGORY``.

        - financial_status_indicator : see ``itch.indicators.FINANCIAL_STATUS_INDICATOR``.

        - round_lot_size : Denotes the number of shares that represent a round lot for the issue

        - round_lots_only : Indicates if Nasdaq system limits order entry for issue
            (``b"Y": "Only round lots", b"N": "Odd and Mixed lots"``)

        - issue_classification : Identifies the security class for the issue as assigned by Nasdaq.
            see ``itch.indicators.ISSUE_CLASSIFICATION_VALUES``.

        - issue_sub_type : Identifies the security sub-•-type for the issue as assigned by Nasdaq.
            See ``itch.indicators.ISSUE_SUB_TYPE_VALUES``

        - authenticity : Denotes if an issue or quoting participant record is set-•-up in Nasdaq systems in a live/production, test, or demo state.
            Please note that firms should only show live issues and quoting participants on public quotation displays.
            (``b"P"=Live/Production, b"T"=Test``)

        - short_sale_threshold_indicator : Indicates if a security is subject to mandatory close-•-out of short sales under SEC Rule 203(b)(3):
            b"Y": "Issue is restricted under SEC Rule 203(b)(3)"
            b"N": "Issue is not restricted"
            b" ": "Threshold Indicator not available"

        - ipo_flag : Indicates if the Nasdaq security is set up for IPO release. This field is intended to help Nasdaq market
            participant firms comply with FINRA Rule 5131(b):
            b"Y": "Nasdaq listed instrument is set up as a new IPO security"
            b"N": "Nasdaq listed instrument is not set up as a new IPO security"
            b" ": "Not available"

        - luld_ref : Indicates which Limit Up / Limit Down price band calculationparameter is to be used for the instrument.
            Refer to [LULD Rule ](https://www.nasdaqtrader.com/content/MarketRegulation/LULD_FAQ.pdf) for details:
            b"1": "Tier 1 NMS Stocks and select ETPs"
            b"2": "Tier 2 NMS Stocks"
            b" ": "Not available"

        - etp_flag : Indicates whether the security is an exchange traded product (ETP):
            b"Y": "Tier 1 NMS Stocks and select ETPs"
            b"N": "Instrument is not an ETP"
            b" ": "Not available"

        - etp_leverage_factor : Tracks the integral relationship of the ETP to the underlying index.
            Example: If the underlying Index increases by a value of 1 and the ETP's Leverage factor is 3, indicates the ETF will increase/decrease (see Inverse) by 3.
            Leverage Factor is rounded to the nearest integer below, e.g. leverage factor 1 would represent leverage factors of 1 to 1.99.
            This field is used for LULD Tier I price band calculation purpose.

        - inverse_indicator : Indicates the directional relationship between the ETP and Underlying index:
            b"Y": "ETP is an Inverse ETP "
            b"N": "ETP is not an Inverse ETP "
        Example: An ETP Leverage Factor of 3 and an Inverse value of "Y" indicates the ETP will decrease by a value of 3.

    """

    message_type = b"R"
    description = "Stock Directory Message"
    message_format = "!HHHI8sccIcc2scccccIc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    market_category: bytes
    financial_status_indicator: bytes
    round_lot_size: int
    round_lots_only: bytes
    issue_classification: bytes
    issue_sub_type: bytes
    authenticity: bytes
    short_sale_threshold_indicator: bytes
    ipo_flag: bytes
    luld_ref: bytes
    etp_flag: bytes
    etp_leverage_factor: int
    inverse_indicator: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.market_category,
            self.financial_status_indicator,
            self.round_lot_size,
            self.round_lots_only,
            self.issue_classification,
            self.issue_sub_type,
            self.authenticity,
            self.short_sale_threshold_indicator,
            self.ipo_flag,
            self.luld_ref,
            self.etp_flag,
            self.etp_leverage_factor,
            self.inverse_indicator,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.market_category,
            self.financial_status_indicator,
            self.round_lot_size,
            self.round_lots_only,
            self.issue_classification,
            self.issue_sub_type,
            self.authenticity,
            self.short_sale_threshold_indicator,
            self.ipo_flag,
            self.luld_ref,
            self.etp_flag,
            self.etp_leverage_factor,
            self.inverse_indicator,
        )
        return message


class StockTradingActionMessage(MarketMessage):
    """
    Nasdaq uses this administrative message to indicate the current trading status of a security to the trading
    community.

    Prior to the start of system hours, Nasdaq will send out a Trading Action spin. In the spin, Nasdaq will send out a
    Stock Trading Action message with the “T” (Trading Resumption) for all Nasdaq--- and other exchange-•-listed
    securities that are eligible for trading at the start of the system hours.  If a security is absent from the pre-•-
    opening Trading Action spin, firms should assume that the security is being treated as halted in the Nasdaq
    platform at the start of the system hours. Please note that securities may be halted in the Nasdaq system for
    regulatory or operational reasons.

    After the start of system hours, Nasdaq will use the Trading Action message to relay changes in trading status for an
    individual security. Messages will be sent when a stock is:
    - Halted
    - Paused*
    - Released for quotation
    - Released for trading

    The paused status will be disseminated for NASDAQ---listed securities only. Trading pauses on non---NASDAQ listed securities
    will be treated simply as a halt.

    Attributes:
        - stock : Stock symbol, right padded with spaces
        - trading_state : Indicates the current trading state for the stock, see `itch.indicators.TRADING_STATES`
        - reserved : Reserved
        - reason : Trading Action reason, see `itch.indicators.TRADING_ACTION_REASON_CODES`
    """

    message_type = b"H"
    description = "Stock Trading Action Message"
    message_format = "!HHHI8scc4s"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    trading_state: bytes
    reserved: bytes
    reason: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.trading_state,
            self.reserved,
            self.reason,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.trading_state,
            self.reserved,
            self.reason,
        )
        return message


class RegSHOMessage(MarketMessage):
    """
    In February 2011, the Securities and Exchange Commission (SEC) implemented changes to Rule 201 of the
    Regulation SHO (Reg SHO). For details, please refer to [SEC Release Number 34-61595](https://www.sec.gov/files/rules/final/2010/34-61595.pdf).
    In association with the Reg SHO rule change, Nasdaq will introduce the following Reg SHO Short Sale Price Test Restricted
    Indicator message format.

    For Nasdaq-listed issues, Nasdaq supports a full pre-•-opening spin of Reg SHO Short Sale Price Test Restricted
    Indicator messages indicating the Rule 201 status for all active issues. Nasdaq also sends the Reg SHO
    Short Sale Price Test Restricted Indicator message in the event of an intraday status change.

    For other exchange-listed issues, Nasdaq relays the Reg SHO Short Sale Price Test Restricted Indicator
    message when it receives an update from the primary listing exchange.

    Nasdaq processes orders based on the most Reg SHO Restriction status value.

    Attributes:
        - stock : Stock symbol, right padded with spaces
        - reg_sho_action : Denotes the Reg SHO Short Sale Price Test Restriction status for the issue at the time of the message dissemination:
            b"0": "No price test in place"
            b"1": "Reg SHO Short Sale Price Test Restriction in effect due to an intra-day price drop in security"
            b"2": " Reg SHO Short Sale Price Test Restriction remains in effect"
    """

    message_type = b"Y"
    description = "Reg SHO Short Sale Price Test Restricted Indicator"
    message_format = "!HHHI8sc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    reg_sho_action: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.reg_sho_action,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.reg_sho_action,
        )
        return message


class MarketParticipantPositionMessage(MarketMessage):
    """
    At the start of each trading day, Nasdaq disseminates a spin of market participant position messages. The
    message provides the Primary Market Maker status, Market Maker mode and Market Participant state for
    each Nasdaq market participant firm registered in an issue. Market participant firms may use these fields to
    comply with certain marketplace rules.

    Throughout the day, Nasdaq will send out this message only if Nasdaq Operations changes the status of a
    market participant firm in an issue.

    Attributes:
        - mpid : Denotes the market participant identifier for which the position message is being generated
        - stock : Stock symbol, right padded with spaces
        - primary_market_maker : Indicates if the market participant firm qualifies as a Primary Market Maker in accordance with Nasdaq marketplace rules
            see ``itch.indicators.PRIMARY_MARKET_MAKER``
        - market_maker_mode : Indicates the quoting participant's registration status in relation to SEC Rules 101 and 104 of Regulation M
            see ``itch.indicators.MARKET_MAKER_MODE``
        - market_participant_state : Indicates the market participant's current registration status in the issue
            see ``itch.indicators.MARKET_PARTICIPANT_STATE``
    """

    message_type = b"L"
    description = "Market Participant Position message"
    message_format = "!HHHI4s8sccc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    mpid: bytes
    stock: bytes
    primary_market_maker: bytes
    market_maker_mode: bytes
    market_participant_state: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.mpid,
            self.stock,
            self.primary_market_maker,
            self.market_maker_mode,
            self.market_participant_state,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.mpid,
            self.stock,
            self.primary_market_maker,
            self.market_maker_mode,
            self.market_participant_state,
        )
        return message


class MWCBDeclineLeveMessage(MarketMessage):
    """
    Informs data recipients what the daily  Market-Wide Circuit Breaker (MWCB)
    breach points are set to for the current trading day.

    Attributes:
        - level1_price : Denotes the MWCB Level 1 Value.
        - level2_price : Denotes the MWCB Level 2 Value.
        - level3_price : Denotes the MWCB Level 3 Value.
    """

    message_type = b"V"
    description = "Market wide circuit breaker Decline Level Message"
    message_format = "!HHHIQQQ"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1
    price_precision = 8
    level1_price: float
    level2_price: float
    level3_price: float

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.level1_price,
            self.level2_price,
            self.level3_price,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.level1_price,
            self.level2_price,
            self.level3_price,
        )
        return message


class MWCBStatusMessage(MarketMessage):
    """
    Informs data recipients when a MWCB has breached one of the established levels

    Attributes:
        - breached_level : Denotes the MWCB Level that was breached:
            b"1" = Level 1
            b"2" = Level 2
            b"3" = Level 3
    """

    message_type = b"W"
    description = "Market-Wide Circuit Breaker Status message"
    message_format = "!HHHIc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    breached_level: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.breached_level,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.breached_level,
        )
        return message


class IPOQuotingPeriodUpdateMessage(MarketMessage):
    """
    Indicates the anticipated IPO quotation release time of a security.

    Attributes:
        - stock : Stock symbol, right padded with spaces

        - ipo_release_time : Denotes the IPO release time, in seconds since midnight, for quotation to the nearest second.
        NOTE: If the quotation period is being canceled/postponed, we should state that:
            1. IPO Quotation Time will be set to 0
            2. 2. IPO Price will be set to 0

        - ipo_release_qualifier :
            b"A": "Anticipated Quotation Release Time"
            b"C": " IPO Release Canceled/Postponed"
            b"A" value would be used when Nasdaq Market Operations initially enters the IPO instrument for release
            b"C" value would be sued when Nasdaq Market Operations cancels or postpones the release of the new IPO instrument

        - ipo_price : Denotes the IPO Price to be used for intraday net change calculations Prices are given in decimal format with 6 whole number
            places followed by 4 decimal digits. The whole number portion is padded on the left with spaces; the decimal portion is padded on the right with zeroes. The decimal point is
            implied by position, it does not appear inside the price field
    """

    message_type = b"K"
    description = "IPO Quoting Period Update Message"
    message_format = "!HHHI8sIcI"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    ipo_release_time: int
    ipo_release_qualifier: bytes
    ipo_price: float

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.ipo_release_time,
            self.ipo_release_qualifier,
            self.ipo_price,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.ipo_release_time,
            self.ipo_release_qualifier,
            self.ipo_price,
        )
        return message


class LULDAuctionCollarMessage(MarketMessage):
    """
    Indicates the auction collar thresholds within which a paused security can reopen following a LULD Trading Pause.
    Stock 11 8 Alpha Stock symbol, right padded with spaces

    Attributes:
        - stock : Stock symbol, right padded with spaces
        - auction_collar_reference_price : Reference price used to set the Auction Collars
        - upper_auction_collar_price : Indicates the price of the Upper Auction Collar Threshold
        - lower_auctiin_collar_price : Indicates the price of the Lower Auction Collar Threshold
        - auction_collar_extention : Indicates the number of the extensions to the Reopening Auction
    """

    message_type = b"J"
    description = "LULD Auction Collar"
    message_format = "!HHHI8sIIII"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    auction_collar_reference_price: float
    upper_auction_collar_price: float
    lower_auction_collar_price: float
    auction_collar_extention: int

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.auction_collar_reference_price,
            self.upper_auction_collar_price,
            self.lower_auction_collar_price,
            self.auction_collar_extention,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.auction_collar_reference_price,
            self.upper_auction_collar_price,
            self.lower_auction_collar_price,
            self.auction_collar_extention,
        )
        return message


class OperationalHaltMessage(MarketMessage):
    """
    The Exchange uses this message to indicate the current Operational Status of a security to the trading
    community. An Operational Halt means that there has been an interruption of service on the identified
    security impacting only the designated Market Center. These Halts differ from the “Stock Trading
    Action” message types since an Operational Halt is specific to the exchange for which it is declared, and
    does not interrupt the ability of the trading community to trade the identified instrument on any other
    marketplace.

    Nasdaq uses this administrative message to indicate the current trading status of the three market centers
    operated by Nasdaq.

    Attributes:
        - stock : Denotes the security symbol for the issue in Nasdaq execution system
        - market_code :
            b"Q": "Nasdaq"
            b"B": "BX"
            b"X": "PSX"

        - operational_halt_action :
            b"H": "Operationally Halted on the identified Market"
            b"T": "Operational Halt has been lifted and Trading resumed "

    """

    message_type = b"h"
    description = "Operational Halt"
    message_format = "!HHHI8scc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    market_code: bytes
    operational_halt_action: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.market_code,
            self.operational_halt_action,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.market_code,
            self.operational_halt_action,
        )
        return message


class AddOrderMessage(MarketMessage):
    """
    An Add Order Message indicates that a new order has been accepted by the Nasdaq system and was added to the
    displayable book. The message includes a day-•-unique Order Reference Number used by Nasdaq to track the order. Nasdaq
    will support two variations of the Add Order message format.
    """

    order_reference_number: int
    buy_sell_indicator: bytes
    shares: int
    stock: bytes
    price: float


class AddOrderNoMPIAttributionMessage(AddOrderMessage):
    """
    This message will be generated for unattributed orders accepted by the Nasdaq system. (Note: If a firm wants to
    display a MPID for unattributed orders, Nasdaq recommends that it use the MPID of “NSDQ”.)

    Attributes:
        - order_reference_number : The unique reference number assigned to the new order at the time of receipt.
        - buy_sell_indicator : The type of order being added. b"B" = Buy Order. b"S" = Sell Order.
        - shares : The total number of shares associated with the order being added to the book.
        - stock : Stock symbol, right padded with spaces
        - price : The display price of the new order. Refer to Data Types for field processing notes.
    """

    message_type = b"A"
    description = "Add Order - No MPID Attribution Message"
    message_format = "!HHHIQcI8sI"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.buy_sell_indicator,
            self.shares,
            self.stock,
            self.price,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.buy_sell_indicator,
            self.shares,
            self.stock,
            self.price,
        )
        return message


class AddOrderMPIDAttribution(AddOrderMessage):
    """
    This message will be generated for attributed orders and quotations accepted by the Nasdaq system.

    Attributes:
        - order_reference_number : The unique reference number assigned to the new order at the time of receipt.
        - buy_sell_indicator : The type of order being added. “B” = Buy Order. “S” = Sell Order.
        - shares : The total number of shares associated with the order being added to the book.
        - stock : Stock symbol, right padded with spaces
        - price : The display price of the new order. Refer to Data Types for field processing notes.
        - attribution : Nasdaq Market participant identifier associated with the entered order
    """

    message_type = b"F"
    description = "Add Order - MPID Attribution Message"
    message_format = "!HHHIQcI8sI4s"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    attribution: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.buy_sell_indicator,
            self.shares,
            self.stock,
            self.price,
            self.attribution,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.buy_sell_indicator,
            self.shares,
            self.stock,
            self.price,
            self.attribution,
        )
        return message


class ModifyOrderMessage(MarketMessage):
    """
    Modify Order messages always include the Order Reference Number of the Add Order to which the update
    applies. To determine the current display shares for an order, ITCH subscribers must deduct the number of shares
    stated in the Modify message from the original number of shares stated in the Add Order message with the same
    reference number. Nasdaq may send multiple Modify Order messages for the same order reference number and
    the effects are cumulative. When the number of display shares for an order reaches zero, the order is dead and
    should be removed from the book.
    """

    order_reference_number: int


class OrderExecutedMessage(ModifyOrderMessage):
    """
    This message is sent whenever an order on the book is executed in whole or in part. It is possible to receive several
    Order Executed Messages for the same order reference number if that order is executed in several parts. The
    multiple Order Executed Messages on the same order are cumulative.

    By combining the executions from both types of Order Executed Messages and the Trade Message, it is possible to
    build a complete view of all non-•-cross executions that happen on Nasdaq. Cross execution information is available in
    one bulk print per symbol via the Cross Trade Message.

    Attributes:
        - order_reference_number : The unique reference number assigned to the new order at the time of receipt
        - executed_shares : The number of shares executed
        - match_number : The Nasdaq generated day unique Match Number of this execution.
            The Match Number is also referenced in the Trade Break Message

    """

    message_type = b"E"
    description = "Add Order - Order Executed Message"
    message_format = "!HHHIQIQ"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    executed_shares: int
    match_number: int

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.executed_shares,
            self.match_number,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.executed_shares,
            self.match_number,
        )
        return message


class OrderExecutedWithPriceMessage(ModifyOrderMessage):
    """
    This message is sent whenever an order on the book is executed in whole or in part at a price different from the
    initial display price. Since the execution price is different than the display price of the original Add Order, Nasdaq
    includes a price field within this execution message.

    It is possible to receive multiple Order Executed and Order Executed With Price messages for the same order if that
    order is executed in several parts. The multiple Order Executed messages on the same order are cumulative.

    These executions may be marked as non-•-printable.
    If the execution is marked as non-•-printed, it means that the shares will be included into a later bulk print (e.g., in the case of cross executions).
    If a firm is looking to use the data in time-•-and-•-sales displays or volume calculations,
    Nasdaq recommends that firms ignore messages marked as non- -- printable to prevent double counting.

    Attributes:
        - order_reference_number : The unique reference number assigned to the new order at the time of receipt
        - executed_shares : The number of shares executed
        - match_number : The Nasdaq generated day unique Match Number of this execution.
            The Match Number is also referenced in the Trade Break Message

        - printable : Indicates if the execution should be reflected on time and sales displays and volume calculations
            b"N" = Non-Printable
            b"Y" = Printable

        - execution_price : The Price at which the order execution occurred. Refer to Data Types for field processing notes
    """

    message_type = b"C"
    description = "Add Order - Order Executed with Price Message"
    message_format = "!HHHIQIQcI"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    executed_shares: int
    match_number: int
    printable: bytes
    execution_price: float

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.executed_shares,
            self.match_number,
            self.printable,
            self.execution_price,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.executed_shares,
            self.match_number,
            self.printable,
            self.execution_price,
        )
        return message


class OrderCancelMessage(ModifyOrderMessage):
    """
    This message is sent whenever an order on the book is modified as a result of a partial cancellation.

    Attributes:
        - order_reference_number : The reference number of the order being canceled
        - cancelled_shares : The number of shares being removed from the display size of the order as a result of a cancellation
    """

    message_type = b"X"
    description = "Order Cancel Message"
    message_format = "!HHHIQI"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    cancelled_shares: int

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.cancelled_shares,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.cancelled_shares,
        )
        return message


class OrderDeleteMessage(ModifyOrderMessage):
    """
    This message is sent whenever an order on the book is being cancelled. All remaining shares are no longer
    accessible so the order must be removed from the book.

    Attributes:
        - order_reference_number : The reference number of the order being canceled
    """

    message_type = b"D"
    description = "Order Delete Message"
    message_format = "!HHHIQ"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
        )
        return message


class OrderReplaceMessage(ModifyOrderMessage):
    """
    This message is sent whenever an order on the book has been cancel-•-replaced.  All remaining shares from the
    original order are no longer accessible, and must be removed. The new order details are provided for the
    replacement, along with a new order reference number which will be used henceforth. Since the side, stock
    symbol and attribution (if any) cannot be changed by an Order Replace event, these fields are not included in the
    message. Firms should retain the side, stock symbol and MPID from the original Add Order message.

    Attributes:
        - order_reference_number : The original order reference number of the order being replaced
        - new_order_reference_number : The new reference number for this order at time of replacement
            Please note that the Nasdaq system will use this new  order reference number for all subsequent updates
        - shares  : The new total displayed quantity
        - price : The new display price for the order. Please refer to Data Types for field processing notes
    """

    message_type = b"U"
    description = "Order Replace Message"
    message_format = "!HHHIQQII"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    new_order_reference_number: int
    shares: int
    price: float

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.new_order_reference_number,
            self.shares,
            self.price,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.new_order_reference_number,
            self.shares,
            self.price,
        )
        return message


class TradeMessage(MarketMessage):
    match_number: int


class NonCrossTradeMessage(TradeMessage):
    """
    The Trade Message is designed to provide execution details for normal match events involving non-•-displayable
    order types. (Note: There is a separate message for Nasdaq cross events.)
    Since no Add Order Message is generated when a non-•-displayed order is initially received, Nasdaq cannot use the
    Order Executed messages for all matches. Therefore this message indicates when a match occurs between non---
    displayable order types.

    A Trade Message is transmitted each time a non-•-displayable order is executed in whole or in part.
    It is possible to receive multiple Trade Messages for the same order if that order is executed in several parts.
    Trade Messages for the same order are cumulative.

    Trade Messages should be included in Nasdaq time-•-and-•-sales displays as well as volume and other market statistics.
    Since Trade Messages do not affect the book, however, they may be ignored by firms just looking to build
    and track the Nasdaq execution system display.

    Attributes:
        - order_reference_number : The unique reference number assigned to the order on the book being executed.
        - buy_sell_indicator :  The type of non-display order on the book being matched b"B" = Buy Order, b"S" = Sell Order
        - shares : The number of shares being matched in this execution
        - stock : Stock Symbol, right padded with spaces
        - price : The match price of the order
        - match_number : The Nasdaq generated session unique Match Number for this trade
            The Match Number is referenced in the Trade Break Message
    """

    message_type = b"P"
    description = "Trade Message"
    message_format = "!HHHIQcI8sIQ"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    order_reference_number: int
    buy_sell_indicator: bytes
    shares: int
    stock: bytes
    price: float

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.buy_sell_indicator,
            self.shares,
            self.stock,
            self.price,
            self.match_number,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.order_reference_number,
            self.buy_sell_indicator,
            self.shares,
            self.stock,
            self.price,
            self.match_number,
        )
        return message


class CrossTradeMessage(TradeMessage):
    """
    Cross Trade message indicates that Nasdaq has completed its cross process for a specific security. Nasdaq sends out
    a Cross Trade message for all active issues in the system following the Opening, Closing and EMC cross events.
    Firms may use the Cross Trade message to determine when the cross for each security has been completed.
    (Note: For the halted / paused securities, firms should use the Trading Action message to determine when an issue has been
    released for trading.)

    For most issues, the Cross Trade message will indicate the bulk volume associated with the cross event. If the order
    interest is insufficient to conduct a cross in a particular issue, however, the Cross Trade message may show the
    shares as zero.

    To avoid double counting of cross volume, firms should not include transactions marked as non-•-printable in time---
    and-•-sales displays or market statistic calculations.

    Attributes:
        - shares : The number of shares being matched in this execution
        - stock : Stock Symbol, right padded with spaces
        - cross_price : The match price of the order
        - match_number : The Nasdaq generated session unique Match Number for this trade
            The Match Number is referenced in the Trade Break Message
        - cross_type : The Nasdaq cross session for which the message is being generated:
            b"O": "Nasdaq Opening Cross"
            b"C": "Nasdaq Closing Cross"
            b"H": "Cross for IPO and halted / paused securities"
    """

    message_type = b"Q"
    description = "Cross Trade Message"
    message_format = "!HHHIQ8sIQc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    shares: int
    stock: bytes
    cross_price: float
    cross_type: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.shares,
            self.stock,
            self.cross_price,
            self.match_number,
            self.cross_type,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.shares,
            self.stock,
            self.cross_price,
            self.match_number,
            self.cross_type,
        )
        return message


class BrokenTradeMessage(TradeMessage):
    """
    The Broken Trade Message is sent whenever an execution on Nasdaq is broken. An execution may be broken if it is
    found to be “clearly erroneous” pursuant to [Nasdaq's Clearly Erroneous Policy](https://www.nasdaqtrader.com/Trader.aspx?id=ClearlyErroneous#:~:text=The%20terms%20of%20a%20transaction,or%20identification%20of%20the%20security.).
    A trade break is final; once a trade is broken, it cannot be reinstated.

    Firms that use the ITCH feed to create time---and---sales displays or calculate market statistics should be prepared
    to process the broken trade message. If a firm is only using the ITCH feed to build a book, however, it may ignore
    these messages as they have no impact on the current book.

    Attributes:
        - match_number : The Nasdaq Match Number of the execution that was broken.
            This refers to a Match Number from a previously transmitted Order Executed Message,
            Order Executed With Price Message, or Trade Message.
    """

    message_type = b"B"
    description = "Broken Trade Message"
    message_format = "!HHHIQ"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.match_number,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.match_number,
        )
        return message


class NOIIMessage(MarketMessage):
    """
    - Nasdaq begins disseminating Net Order Imbalance Indicators (NOII) at 9:25 a.m. for the Opening Cross and 3:50 p.m. for the Closing Cross.
    - Between 9:25 and 9:28 a.m. and 3:50 and 3:55 p.m., Nasdaq disseminates the NOII information every 10 seconds.
    - Between 9:28 and 9:30 a.m. and 3:55 and 4:00 p.m., Nasdaq disseminates the NOII information every second.
    - For Nasdaq Halt, IPO and Pauses, NOII messages will be disseminated at 1 second intervals starting 1 second after quoting period starts/trading action is released.
    - For more information, please see the [FAQ on Opening and Closing Crosses](https://www.nasdaqtrader.com/content/productsservices/trading/crosses/openclose_faqs.pdf).
    - Nasdaq will also disseminate an Extended Trading Close (ETC) message from 4:00 p.m. to 4:05 p.m. at five second intervals.
    - For more information, please see the [FAQ on Extended Trading Close](https://www.nasdaqtrader.com/content/productsservices/trading/After-Hour-Cross-FAQ-Factsheet-NAM.pdf).

    Attributes:
        - paired_shares : The total number of shares that are eligible to be matched at the Current Reference Price.
        - imbalance_shares : The number of shares not paired at the Current Reference Price.
        - imbalance_direction : The market side of the order imbalance:
            b"B": "buy imbalance"
            b"S": "sell imbalance"
            b"N": "no imbalance"
            b"O": "Insufficient orders to calculate"
            b"P": "Paused"

        - stock : Stock symbol, right padded with spaces
        - far_price : A hypothetical auction---clearing price for cross orders only. Refer to Data Types for field processing notes.
        - near_price : A hypothetical auction-•-clearing price for cross orders as well as continuous orders. Refer to Data Types for field
        - current_reference_price : The price at which the NOII shares are being calculated. Refer to Data Types for field processing notes.
        - cross_type : The type of Nasdaq cross for which the NOII message is being generated:
            b"O": "Nasdaq Opening Cross"
            b"C": "Nasdaq Closing Cross"
            b"H": "Cross for IPO and halted / paused securities"
            b"A": "Extended Trading Close"

        - variation_indicator : This field indicates the absolute value of the percentage of deviation of
            the Near Indicative Clearing Price to the  nearest Current Reference Price, see ``itch.indicators.``
    """

    message_type = b"I"
    description = "NOII Message"
    message_format = "!HHHIQQc8sIIIcc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    paired_shares: int
    imbalance_shares: bytes
    imbalance_direction: bytes
    stock: bytes
    far_price: float
    near_price: float
    current_reference_price: float
    cross_type: bytes
    variation_indicator: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.paired_shares,
            self.imbalance_shares,
            self.imbalance_direction,
            self.stock,
            self.far_price,
            self.near_price,
            self.current_reference_price,
            self.cross_type,
            self.variation_indicator,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.paired_shares,
            self.imbalance_shares,
            self.imbalance_direction,
            self.stock,
            self.far_price,
            self.near_price,
            self.current_reference_price,
            self.cross_type,
            self.variation_indicator,
        )
        return message


class RetailPriceImprovementIndicator(MarketMessage):
    """
    Identifies a retail interest indication of the Bid, Ask or both the Bid and Ask for Nasdaq-•-listed securities.

    Attributes:
        - stock : Stock symbol, right padded with spaces
        - interest_flag :
            b"B": "RPI orders available on the buy side"
            b"S": "RPI orders available on the sell side"
            b"A": "RPI orders available on both sides (buy and sell)"
            b"N": "No RPI orders available "
    """

    message_type = b"N"
    description = "Retail Interest message"
    message_format = "!HHHI8sc"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    interest_flag: bytes

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.interest_flag,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.interest_flag,
        )
        return message


class DLCRMessage(MarketMessage):
    """
    The following message is disseminated only for Direct Listing with Capital Raise (DLCR) securities.
    Nasdaq begins disseminating messages once per second as soon as the DLCR volatility test has successfully passed.

    Attributes:
        - stock : Stock symbol, right padded with spaces.
        - open_eligibility_status : Indicates if the security is eligible to be released for trading (b"N": Not Eligible, b"Y": Eligible)
        - minimum_allowable_price : 20% below Registration Statement Lower Price
        - maximum_allowable_price : 80% above Registration Statement Highest Price
        - near_execution_price : The current reference price when the DLCR volatility test has successfully passed
        - near_execution_time : The time at which the near execution price was set
        - lower_price_range_collar : Indicates the price of the Lower Auction Collar Threshold (10% below the Near Execution Price)
        - upper_price_range_collar : Indicates the price of the Upper Auction Collar Threshold (10% above the Near Execution Price)
    """

    message_type = b"O"
    description = "Direct Listing with Capital Raise Message"
    message_format = "!HHHI8scIIIQII"
    message_pack_format = "!" + "c" + message_format[1:]
    message_size = struct.calcsize(message_format) + 1

    stock: bytes
    open_eligibility_status: bytes
    minimum_allowable_price: float
    maximum_allowable_price: float
    near_execution_price: float
    near_execution_time: int
    lower_price_range_collar: float
    upper_price_range_collar: float

    def __init__(self, message: bytes):
        (
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.open_eligibility_status,
            self.minimum_allowable_price,
            self.maximum_allowable_price,
            self.near_execution_price,
            self.near_execution_time,
            self.lower_price_range_collar,
            self.upper_price_range_collar,
        ) = struct.unpack(self.message_format, message[1:])
        self.set_timestamp(timestamp1, timestamp2)

    def pack(self):
        (timestamp1, timestamp2) = self.split_timestamp()
        message = struct.pack(
            self.message_pack_format,
            self.message_type,
            self.stock_locate,
            self.tracking_number,
            timestamp1,
            timestamp2,
            self.stock,
            self.open_eligibility_status,
            self.minimum_allowable_price,
            self.maximum_allowable_price,
            self.near_execution_price,
            self.near_execution_time,
            self.lower_price_range_collar,
            self.upper_price_range_collar,
        )
        return message


messages: Dict[bytes, Type[MarketMessage]] = {
    b"S": SystemEventMessage,
    b"R": StockDirectoryMessage,
    b"H": StockTradingActionMessage,
    b"Y": RegSHOMessage,
    b"L": MarketParticipantPositionMessage,
    b"V": MWCBDeclineLeveMessage,
    b"W": MWCBStatusMessage,
    b"K": IPOQuotingPeriodUpdateMessage,
    b"J": LULDAuctionCollarMessage,
    b"h": OperationalHaltMessage,
    b"A": AddOrderNoMPIAttributionMessage,
    b"F": AddOrderMPIDAttribution,
    b"E": OrderExecutedMessage,
    b"C": OrderExecutedWithPriceMessage,
    b"X": OrderCancelMessage,
    b"D": OrderDeleteMessage,
    b"U": OrderReplaceMessage,
    b"P": NonCrossTradeMessage,
    b"Q": CrossTradeMessage,
    b"B": BrokenTradeMessage,
    b"I": NOIIMessage,
    b"N": RetailPriceImprovementIndicator,
    b"O": DLCRMessage,
}


def create_message(message_type: bytes, **kwargs) -> Type[MarketMessage]:
    """
    Creates a new message of a given type with specified attributes.

    This function simplifies the process of message creation by handling
    the instantiation and attribute setting for any valid message type.
    It's particularly useful for simulating trading environments or
    generating test data without manually packing and unpacking bytes.

    Args:
        message_type (bytes):
            A single-byte identifier for the message type (e.g., b'A'
            for AddOrderNoMPIAttributionMessage).
        **kwargs:
            Keyword arguments representing the attributes of the message.
            These must match the attributes expected by the message class
            (e.g., `stock_locate`, `timestamp`, `price`).

    Returns:
        MarketMessage:
            An instance of the corresponding message class, populated with
            the provided attributes.

    Raises:
        ValueError:
            If the `message_type` is not found in the registered messages.
    """
    message_class = messages.get(message_type)
    if not message_class:
        raise ValueError(f"Unknown message type: {message_type.decode()}")

    # Create a new instance without calling __init__
    # __init__ is for unpacking, not creating
    instance = message_class.__new__(message_class)

    # Set attributes from kwargs
    for key, value in kwargs.items():
        if key == 'timestamp':
            # Timestamps are 48-bit, so we need to mask the original value
            value &= ((1 << 48) - 1)
        setattr(instance, key, value)

    # Set the message_type attribute on the instance, as it's used by pack()
    instance.message_type = message_type

    return instance
