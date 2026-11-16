"""Pinned USD-M demo market context. No live switch or arbitrary host input."""
SOURCE = 'binance_usdm_demo_trade_price'
ENVIRONMENT = 'demo_public'
PRODUCT = 'USD-M'
REST_URL = 'https://demo-fapi.binance.com'
KLINE_WS_BASE = 'wss://demo-fstream.binance.com/market/ws/'


def identity(symbol, interval):
    return dict(source=SOURCE, environment=ENVIRONMENT, product=PRODUCT,
                price_type='LAST_PRICE', symbol=symbol, interval=interval)
