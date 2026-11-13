import copy
import json
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import Mock

from agentrader.chart_precision import decimal_text, exact_candle, exact_tick, validate_tick_price, precision_summary, PrecisionError
from agentrader.chart_market import ChartMarket, candle, InvalidMarket, normalize_kline
from agentrader.market_data import CandleStore
from agentrader.market_feed import FeedState
from test_chart_feed import row, event, START, STEP

class ChartPrecisionTests(unittest.TestCase):
    def test_high_precision_round_trip_even_with_small_decimal_context(self):
        text='100.123456789012345678901234567890123456789'
        with localcontext() as context:
            context.prec=5
            self.assertEqual(decimal_text(text),text)
            self.assertEqual(decimal_text('1.2300E-12'),'0.00000000000123')
        self.assertEqual(decimal_text('-0.000'),'0')

    def test_non_text_and_malformed_decimal_cannot_establish_precision(self):
        for value in [1.2,1,True,Decimal('1.2'),None,'NaN','Infinity','-1',' 1','1_000','1e999999','1e-31','9'*129]:
            with self.subTest(value=str(value)),self.assertRaises(PrecisionError):decimal_text(value)
        with self.assertRaises(PrecisionError):decimal_text('0',positive=True)

    def test_exact_candle_does_not_reconstruct_from_float(self):
        raw=row();raw[4]=105.0
        self.assertEqual(exact_candle(raw)['state'],'UNPROVEN')
        dto=candle(raw,START+2000)
        self.assertIsInstance(dto['close'],float)
        self.assertEqual(dto['exact']['reason'],'PRICE_PRECISION_UNPROVEN')

    def test_bad_ohlc_and_negative_volume_rejected(self):
        for index,value in [(2,'99'),(3,'106'),(4,'0'),(5,'-1'),(7,'NaN')]:
            raw=row();raw[index]=value
            with self.subTest(index=index),self.assertRaises(InvalidMarket):candle(raw,START+2000)

    def test_tick_validation_never_rounds_and_ignores_ambient_precision(self):
        text='100.12345678901234567890123456789'
        with localcontext() as context:
            context.prec=4
            self.assertEqual(validate_tick_price(text,'0.00000000000000000000000000001'),text)
        with self.assertRaises(PrecisionError):validate_tick_price('100.15','0.1')
        self.assertEqual(exact_tick(.1)['state'],'UNPROVEN')

    def market(self,folder,rows):
        client=Mock()
        symbol={'symbol':'BTCUSDT','status':'TRADING','contractType':'PERPETUAL','baseAsset':'BTC','quoteAsset':'USDT','filters':[{'filterType':'PRICE_FILTER','tickSize':'0.1000'}]}
        def get(path,params=None):
            if path.endswith('exchangeInfo'):return {'symbols':[symbol]}
            if path.endswith('/time'):return {'serverTime':START+2000}
            return rows
        client.get.side_effect=get
        return ChartMarket(Path(folder)/'market.db',client_factory=lambda:client,clock=lambda:START/1000+2)

    def test_rest_cache_raw_store_and_wire_round_trip_preserve_exact_text(self):
        with tempfile.TemporaryDirectory() as folder:
            raw=row();raw[4]='105.000000000000000000001'
            market=self.market(folder,[row(START-STEP),raw]);h=market.history('BTCUSDT','15m',limit=2)
            wire=json.loads(json.dumps(h));self.assertEqual(wire['candles'][-1]['exact']['close'],raw[4])
            self.assertEqual(wire['market']['exact']['tick_size'],'0.1');self.assertEqual(wire['precision']['state'],'VERIFIED')
            h['candles'][-1]['exact']['close']='bad'
            self.assertEqual(market.history('BTCUSDT','15m',limit=2)['candles'][-1]['exact']['close'],raw[4])
            store=CandleStore(Path(folder)/'market.db')
            try:self.assertEqual(store.load('BTCUSDT','15m',START+2000)[-1][4],raw[4])
            finally:store.close()

    def test_legacy_float_store_is_unproven_not_silently_upgraded(self):
        with tempfile.TemporaryDirectory() as folder:
            raw=row();raw[4]=105.0;store=CandleStore(Path(folder)/'legacy.db')
            try:
                store.save('BTCUSDT','15m',[raw],START+2000)
                loaded=store.load('BTCUSDT','15m',START+2000)[0]
                self.assertEqual(exact_candle(loaded)['state'],'UNPROVEN')
            finally:store.close()

    def test_feed_snapshot_update_tail_and_heartbeat_preserve_exactness(self):
        with tempfile.TemporaryDirectory() as folder:
            market=self.market(folder,[row(START-STEP),row()]);state=FeedState('BTCUSDT','15m',clock=lambda:START/1000+3)
            state.seed(market.history('BTCUSDT','15m',limit=2));snapshot=state.packet()
            self.assertEqual(snapshot['precision']['state'],'VERIFIED')
            raw=event();raw['k']['c']='105.000000000000000000001';state.apply(raw)
            packet=json.loads(json.dumps(state.packet(state.generation)))
            self.assertEqual(packet['candle']['exact']['close'],raw['k']['c']);self.assertEqual(packet['tail'][-1]['exact'],packet['candle']['exact'])
            packet['market']['exact']['tick_size']='bad'
            self.assertEqual(state.packet()['market']['exact']['tick_size'],'0.1')
            self.assertEqual(state.packet(state.generation)['precision']['state'],'VERIFIED')

    def test_sub_float_volume_decrease_cannot_mutate_feed(self):
        with tempfile.TemporaryDirectory() as folder:
            raw=row();raw[5]='10.000000000000000000002'
            market=self.market(folder,[row(START-STEP),raw]);state=FeedState('BTCUSDT','15m',clock=lambda:START/1000+3);state.seed(market.history('BTCUSDT','15m',limit=2))
            before=state.packet();self.assertIsNone(state.apply(event(volume='10.000000000000000000001')))
            self.assertEqual(state.sequence,before['sequence']);self.assertEqual(state.rows[-1]['exact']['volume'],raw[5])

    def test_real_http_and_websocket_keep_sidecar_and_numeric_chart_fields(self):
        from fastapi.testclient import TestClient
        from types import SimpleNamespace
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with tempfile.TemporaryDirectory() as folder:
            raw=row();raw[4]='105.000000000000000000001'
            market=self.market(folder,[row(START-STEP),raw]);state=FeedState('BTCUSDT','15m',clock=lambda:START/1000+3)
            state.seed(market.history('BTCUSDT','15m',limit=2));hub=Mock();hub.acquire.return_value=SimpleNamespace(state=state)
            settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
            with TestClient(create_app(settings,market=market,hub=hub),base_url='http://127.0.0.1') as client:
                response=client.get('/api/candles?symbol=BTCUSDT&interval=15m&limit=2');self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()['candles'][-1]['exact']['close'],raw[4]);self.assertIsInstance(response.json()['candles'][-1]['close'],float)
                with client.websocket_connect('ws://127.0.0.1/api/market-stream?symbol=BTCUSDT&interval=15m',headers={'origin':'http://127.0.0.1'}) as ws:
                    snapshot=ws.receive_json();self.assertEqual(snapshot['precision']['state'],'VERIFIED')
                    update=event();update['k']['c']='105.000000000000000000002';state.apply(update)
                    packet=ws.receive_json();self.assertEqual(packet['candle']['exact']['close'],update['k']['c']);self.assertIsInstance(packet['candle']['close'],float)
            self.assertFalse(settings.execution_database.exists())

    def test_legacy_seed_and_missing_tick_do_not_claim_full_precision(self):
        self.assertEqual(precision_summary([candle(row(),START+2000)],{})['state'],'UNPROVEN')
        self.assertEqual(precision_summary([{'close':105.}],{'exact':exact_tick('0.1')})['state'],'UNPROVEN')
        self.assertFalse(precision_summary([candle(row(),START+2000)],{'exact':exact_tick('0.1')})['bot_eligible'])

if __name__=='__main__':unittest.main()
