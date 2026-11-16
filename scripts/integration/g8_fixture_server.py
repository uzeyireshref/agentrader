"""Explicit synthetic HTTP server for G8 acceptance; never a production startup default."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import os
from dataclasses import replace
from types import SimpleNamespace
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.chart.chart_clock import measure_time
from agentrader.chart.chart_precision import exact_tick
from agentrader.shared.market_feed import FeedState,MarketFeedHub
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
from scripts.integration.chart_tool_matrix_cases import candles


def create():
    if os.environ.get('AGENTRADER_G8_FIXTURE')!='EXPLICIT_SYNTHETIC':raise RuntimeError('Explicit synthetic fixture flag required')
    settings=replace(WebSettings.load(),owner='g8-fixture')
    rows=candles(300);now=rows[-1]['time']+2.;mono=1000.
    state=FeedState('BTCUSDT','15m',clock=lambda:now,monotonic=lambda:mono)
    market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',tick_size='0.25',contract_type='PERPETUAL',exact=exact_tick('0.25'))
    sample=measure_time(SimpleNamespace(get=lambda *_:dict(serverTime=int(now*1000))),lambda:now,lambda:mono)[1]
    state.seed(dict(clock_sample=sample,server_time=int(now*1000),market=market,quality=dict(state='OK',missing_bars=0),candles=rows))
    state.timing.observe(int(now*1000));state.state='LIVE'
    hub=MarketFeedHub(None);hub.feeds[('BTCUSDT','15m')]=SimpleNamespace(state=state,references=1)
    def no_network(*args,**kwargs):raise RuntimeError('Fixture disallows market network/subscriptions')
    source=SimpleNamespace(catalog=lambda:dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',markets=[market]),history=no_network)
    proxy=SimpleNamespace(binding_context=hub.binding_context,close=lambda:None,acquire=no_network)
    return create_app(settings,market=source,hub=proxy)
