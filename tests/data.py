# --- Test Data Generation ---
# Common values
DEFAULT_STOCK_LOCATE = 1
DEFAULT_TRACKING_NUMBER = 2
DEFAULT_TIMESTAMP = 1651500000 * 1_000_000_000
DEFAULT_ORDER_REF = 1234567890
DEFAULT_MATCH_NUM = 9876543210
DEFAULT_STOCK = b"AAPL    "
DEFAULT_MPID = b"NSDQ"

TEST_DATA = {
    b"S": {  # SystemEventMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "event_code": b"O",
    },
    b"R": {  # StockDirectoryMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "market_category": b"Q",
        "financial_status_indicator": b"N",
        "round_lot_size": 100,
        "round_lots_only": b"N",
        "issue_classification": b"C",
        "issue_sub_type": b"I ",
        "authenticity": b"P",
        "short_sale_threshold_indicator": b"N",
        "ipo_flag": b"N",
        "luld_ref": b"1",
        "etp_flag": b"N",
        "etp_leverage_factor": 0,
        "inverse_indicator": b"N",
    },
    b"H": {  # StockTradingActionMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "trading_state": b"T",
        "reserved": b"\x00",
        "reason": b"T1  ",
    },
    b"Y": {  # RegSHOMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "reg_sho_action": b"0",
    },
    b"L": {  # MarketParticipantPositionMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "mpid": DEFAULT_MPID,
        "stock": DEFAULT_STOCK,
        "primary_market_maker": b"Y",
        "market_maker_mode": b"N",
        "market_participant_state": b"A",
    },
    b"V": {  # MWCBDeclineLeveMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "level1_price": 10000000000,
        "level2_price": 20000000000,
        "level3_price": 30000000000,
    },
    b"W": {  # MWCBStatusMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "breached_level": b"1",
    },
    b"K": {  # IPOQuotingPeriodUpdateMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "ipo_release_time": 34200,
        "ipo_release_qualifier": b"A",
        "ipo_price": 255000,
    },
    b"J": {  # LULDAuctionCollarMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "auction_collar_reference_price": 1500000,
        "upper_auction_collar_price": 1600000,
        "lower_auction_collar_price": 1400000,
        "auction_collar_extention": 1,
    },
    b"h": {  # OperationalHaltMessage - Lowercase 'h'
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "market_code": b"Q",
        "operational_halt_action": b"H",
    },
    b"A": {  # AddOrderNoMPIAttributionMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "buy_sell_indicator": b"B",
        "shares": 100,
        "stock": DEFAULT_STOCK,
        "price": 1501234,
    },
    b"F": {  # AddOrderMPIDAttribution
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "buy_sell_indicator": b"S",
        "shares": 200,
        "stock": DEFAULT_STOCK,
        "price": 1505000,
        "attribution": DEFAULT_MPID,
    },
    b"E": {  # OrderExecutedMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "executed_shares": 50,
        "match_number": DEFAULT_MATCH_NUM,
    },
    b"C": {  # OrderExecutedWithPriceMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "executed_shares": 50,
        "match_number": DEFAULT_MATCH_NUM,
        "printable": b"Y",
        "execution_price": 1502000,
    },
    b"X": {  # OrderCancelMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "cancelled_shares": 100,
    },
    b"D": {  # OrderDeleteMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
    },
    b"U": {  # OrderReplaceMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "new_order_reference_number": DEFAULT_ORDER_REF + 1,
        "shares": 150,
        "price": 1510000,
    },
    b"P": {  # NonCrossTradeMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "order_reference_number": DEFAULT_ORDER_REF,
        "buy_sell_indicator": b"B",
        "shares": 100,
        "stock": DEFAULT_STOCK,
        "price": 1503000,
        "match_number": DEFAULT_MATCH_NUM,
    },
    b"Q": {  # CrossTradeMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "shares": 100000,
        "stock": DEFAULT_STOCK,
        "cross_price": 1500000,
        "match_number": DEFAULT_MATCH_NUM,
        "cross_type": b"O",
    },
    b"B": {  # BrokenTradeMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "match_number": DEFAULT_MATCH_NUM,
    },
    b"I": {  # NOIIMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "paired_shares": 50000,
        "imbalance_shares": 10000,
        "imbalance_direction": b"B",
        "stock": DEFAULT_STOCK,
        "far_price": 1520000,
        "near_price": 1510000,
        "current_reference_price": 1500000,
        "cross_type": b"O",
        "variation_indicator": b" ",
    },
    b"N": {  # RetailPriceImprovementIndicator
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "interest_flag": b"A",
    },
    b"O": {  # DLCRMessage
        "stock_locate": DEFAULT_STOCK_LOCATE,
        "tracking_number": DEFAULT_TRACKING_NUMBER,
        "timestamp": DEFAULT_TIMESTAMP,
        "stock": DEFAULT_STOCK,
        "open_eligibility_status": b"Y",
        "minimum_allowable_price": 1800000,
        "maximum_allowable_price": 2200000,
        "near_execution_price": 2000000,
        "near_execution_time": DEFAULT_TIMESTAMP,
        "lower_price_range_collar": 1900000,
        "upper_price_range_collar": 2100000,
    },
}
