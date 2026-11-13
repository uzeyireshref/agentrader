import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.analysis import ema, rsi, atr, timeframe_report, daily_volume
from agentrader.market_data import PublicMarket, CandleStore, INTERVALS, bucket, normalize, fetch_candles
from agentrader.market_cli import build_report, markdown_report
from agentrader.exchange import ExchangeError

ASOF = 1793838000123


def candles(interval, count=61, include_open=True, asof=ASOF):
    step = INTERVALS[interval]
    current = bucket(asof, interval)
    result = []
    for index in range(count + int(include_open)):
        stamp = current - (count - index) * step
        price = 100 + index
        result.append([stamp, str(price), str(price + 2), str(price - 1), str(price + 1),
                       '10', stamp + step - 1, str(1000 + index), 5, '5', str((1000 + index) / 2), '0'])
    return result


class FakeMarket:
    def __init__(self, count=301):
        self.data = {interval: candles(interval, count) for interval in INTERVALS}
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path.endswith('/time'):
            return {'serverTime': ASOF}
        if path.endswith('exchangeInfo'):
            return {'symbols': [{'symbol': s, 'status': 'TRADING', 'contractType': 'PERPETUAL', 'quoteAsset': 'USDT'} for s in ('BTCUSDT', 'ETHUSDT')]}
        return [r for r in self.data[params['interval']] if r[0] <= params['endTime']][-params['limit']:]


class IndicatorTests(unittest.TestCase):
    def test_ema_sma_seed_and_update(self):
        self.assertEqual(ema([1, 2, 3, 4, 5], 3), 4)
        self.assertIsNone(ema([1, 2], 3))
        self.assertEqual(ema([10] * 100, 20), 10)

    def test_rsi_rising_falling_and_flat(self):
        self.assertEqual(rsi(list(range(30))), 100)
        self.assertEqual(rsi(list(range(30, 0, -1))), 0)
        self.assertEqual(rsi([10] * 30), 50)
        self.assertIsNone(rsi([1, 2]))
        self.assertAlmostEqual(rsi([1, 2, 1, 3], 2), 100 - 100 / 6)

    def test_atr_previous_close_gap_and_wilder(self):
        rows = [[0, 0, '12', '8', '10'], [1, 0, '22', '20', '21'], [2, 0, '23', '21', '22']]
        self.assertEqual(atr(rows[:2], 2), 8)
        self.assertEqual(atr(rows, 2), 5)

    def test_weekly_boundary_is_monday_utc(self):
        from datetime import datetime, timezone
        stamp = int(datetime(2026, 11, 5, tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(datetime.fromtimestamp(bucket(stamp, '1w') / 1000, timezone.utc).weekday(), 0)

    def test_open_candle_never_affects_indicators(self):
        rows = candles('15m')
        original = timeframe_report(rows, '15m', ASOF)
        altered = copy.deepcopy(rows)
        altered[-1][1:6] = ['999999', '999999', '999999', '999999', '100000']
        altered[-1][7] = '99999999'
        self.assertEqual(original['features'], timeframe_report(altered, '15m', ASOF)['features'])
        self.assertEqual(original['open_count'], 1)

    def test_gap_staleness_and_warmup_block_features(self):
        rows = candles('1h')
        gap = rows[:10] + rows[11:]
        stale = rows[:-2]
        for data in (gap, stale, rows[-10:]):
            report = timeframe_report(data, '1h', ASOF)
            self.assertEqual(report['status'], 'INVALID_DATA')
            self.assertIsNone(report['features'])

    def test_close_boundary_has_no_lookahead(self):
        rows = candles('1h')
        close_time = rows[-2][6]
        report = timeframe_report(rows, '1h', close_time)
        self.assertEqual(report['closed_count'], 60)
        report_after = timeframe_report(rows, '1h', close_time + 1)
        self.assertEqual(report_after['closed_count'], 61)

    def test_seven_daily_rows_exclude_today_and_compare_prior_week(self):
        result = daily_volume(candles('1d', 20), ASOF)
        self.assertEqual(len(result['days']), 7)
        self.assertTrue(result['comparison_complete'])
        self.assertIsNotNone(result['change_pct'])
        self.assertEqual(result['capital_flows'], 'NOT_AVAILABLE')
        for day in result['days']:
            self.assertEqual(float(day['taker_buy_quote_usdt']) + float(day['taker_sell_quote_usdt']), float(day['quote_volume_usdt']))

    def test_missing_daily_bar_not_filled_with_invented_volume(self):
        rows = candles('1d', 20)
        del rows[-3]
        result = daily_volume(rows, ASOF)
        self.assertFalse(result['comparison_complete'])
        self.assertIsNone(result['change_pct'])
        self.assertTrue(any(day['quote_volume_usdt'] is None for day in result['days']))


class MarketDataTests(unittest.TestCase):
    def test_public_client_blocks_account_trade_and_secret_parameters(self):
        client = PublicMarket()
        for path, params in [('/fapi/v3/account', {}), ('/fapi/v1/order', {}),
                             ('/fapi/v1/time', {'signature': 'never-send'})]:
            with self.assertRaises(ValueError):
                client.get(path, params)

    def test_public_client_only_sends_unsigned_get_to_live_data_host(self):
        client = PublicMarket()
        with patch.object(client.opener, 'open', return_value=io.BytesIO(b'{"serverTime": 1}')) as opened:
            self.assertEqual(client.get('/fapi/v1/time')['serverTime'], 1)
        request = opened.call_args.args[0]
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.full_url, 'https://fapi.binance.com/fapi/v1/time')
        self.assertNotIn('X-mbx-apikey', request.headers)

    def test_identical_duplicates_are_counted_conflicts_rejected(self):
        rows = candles('1h')
        result, quality = normalize(rows + [rows[0]], '1h')
        self.assertEqual(len(result), len(rows))
        self.assertEqual(quality['duplicates_removed'], 1)
        conflict = copy.deepcopy(rows[0])
        conflict[7] = '2000'
        with self.assertRaisesRegex(ValueError, 'çelişen'):
            normalize(rows + [conflict], '1h')

    def test_bad_ohlc_nan_alignment_and_taker_volume_rejected(self):
        for field, value in ((2, '1'), (1, 'NaN'), (0, 123), (10, '9999999'), (8, -1)):
            rows = candles('1h')
            rows[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                normalize(rows, '1h')

    def test_backward_pagination_keeps_full_history_without_duplicates(self):
        client = FakeMarket(900)
        rows, _ = fetch_candles(client, 'BTCUSDT', '1h', ASOF, 700)
        self.assertEqual(len(rows), 701)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0][1]['limit'], 499)
        self.assertLess(client.calls[1][1]['endTime'], client.calls[0][1]['endTime'])

    def test_sqlite_idempotent_updates_and_revisions(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            store = CandleStore(Path(folder) / 'market.db')
            try:
                rows = candles('1h')
                self.assertEqual(store.save('BTCUSDT', '1h', rows, ASOF), 0)
                self.assertEqual(store.save('BTCUSDT', '1h', rows, ASOF), 0)
                changed = copy.deepcopy(rows)
                changed[-2][7] = '2000'
                self.assertEqual(store.save('BTCUSDT', '1h', changed, ASOF + 1), 1)
                self.assertEqual(len(store.load('BTCUSDT', '1h', ASOF)), len(rows))
            finally:
                store.close()

    def test_live_then_offline_has_same_features_and_input_hash(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            store = CandleStore(Path(folder) / 'market.db')
            try:
                live = build_report(FakeMarket(), store, ['BTCUSDT', 'ETHUSDT'])
                offline = build_report(None, store, ['BTCUSDT', 'ETHUSDT'], offline=True)
                self.assertEqual(live['status'], 'OK')
                self.assertEqual(live['input_hash'], offline['input_hash'])
                for symbol in live['symbols']:
                    for interval in INTERVALS:
                        self.assertEqual(live['symbols'][symbol]['timeframes'][interval]['features'], offline['symbols'][symbol]['timeframes'][interval]['features'])
                self.assertFalse(live['trade_execution_enabled'])
                text = markdown_report(live)
                self.assertIn('BTCUSDT', text)
                self.assertIn('ETHUSDT', text)
                self.assertIn('Son 7', text)
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM analysis_runs').fetchone()[0], 2)
            finally:
                store.close()

    def test_unknown_symbol_is_reported_as_incomplete_not_replaced(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            store = CandleStore(Path(folder) / 'market.db')
            try:
                result = build_report(FakeMarket(), store, ['UNKNOWNUSDT'])
                self.assertEqual(result['status'], 'INCOMPLETE')
                self.assertEqual(len(result['symbols']['UNKNOWNUSDT']['missing']), len(INTERVALS))
            finally:
                store.close()

    def test_rate_limit_stops_all_further_requests(self):
        client = FakeMarket()
        original = client.get
        def limited(path, params=None):
            if path.endswith('klines'):
                client.calls.append((path, params))
                raise ExchangeError('rate limit', http_status=429)
            return original(path, params)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            store = CandleStore(Path(folder) / 'market.db')
            try:
                with patch.object(client, 'get', side_effect=limited), self.assertRaises(ExchangeError):
                    build_report(client, store, ['BTCUSDT', 'ETHUSDT'])
                self.assertEqual(len(client.calls), 3)
            finally:
                store.close()

    def test_cli_creates_reports_without_loading_account_credentials(self):
        from agentrader.market_cli import main
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            database, output = Path(folder) / 'market.db', Path(folder) / 'reports'
            with patch('agentrader.market_cli.PublicMarket', return_value=FakeMarket()), \
                 patch('agentrader.config.Config.load', side_effect=AssertionError('Account secrets must not be loaded')), \
                 patch('sys.stdout', new_callable=io.StringIO):
                result = main(['report', '--bars', '60', '--database', str(database), '--output-dir', str(output)])
            self.assertEqual(result, 0)
            report = json.loads((output / 'market-latest.json').read_text(encoding='utf-8'))
            self.assertFalse(report['trade_execution_enabled'])
            self.assertEqual(report['status'], 'OK')
