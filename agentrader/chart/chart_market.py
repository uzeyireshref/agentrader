"""Bounded public USD-M chart history; no credentials or execution access."""
from agentrader.shared.market_environment import ENVIRONMENT
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import copy
import math
from pathlib import Path
import re
import threading
import time

from agentrader.chart.chart_clock import measure_time, StreamTiming
from agentrader.chart.chart_precision import exact_candle, exact_tick, precision_summary, PrecisionError
from agentrader.shared.market_data import PublicMarket, CandleStore, INTERVALS, SOURCE, bucket, fetch_candles, normalize


class MarketUnavailable(RuntimeError):
    pass


class InvalidMarket(ValueError):
    pass


def validate_selection(symbol, interval):
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', symbol) or interval not in INTERVALS:
        raise InvalidMarket('Desteklenmeyen sembol veya zaman dilimi.')


def candle(row, as_of):
    result = {'time': row[0] // 1000, 'close_time': row[6], 'closed': row[6] < as_of,
              'open': float(row[1]), 'high': float(row[2]), 'low': float(row[3]), 'close': float(row[4]),
              'volume': float(row[5]), 'quote_volume': float(row[7])}
    if not all(math.isfinite(result[k]) for k in ('open','high','low','close','volume','quote_volume')):
        raise InvalidMarket('Geçersiz mum değeri.')
    try:
        result['exact'] = exact_candle(row)
    except PrecisionError:
        raise InvalidMarket('Geçersiz kesin mum değeri.') from None
    return result


class ChartMarket:
    def __init__(self, database, *, client_factory=PublicMarket, clock=time.time, monotonic=time.monotonic):
        self.database, self.client_factory, self.clock = Path(database), client_factory, clock
        self.monotonic = monotonic
        self._catalog = None
        self._catalog_at = 0
        self._lock = threading.RLock()
        self._catalog_lock = threading.RLock()
        self._history_locks = {interval: threading.RLock() for interval in INTERVALS}
        self._clock_lock = threading.RLock()
        self._recent_clock = None
        self._history_cache = OrderedDict()

    def clock_sample(self):
        """Independent public clock read; no history lock or candle mutation."""
        return measure_time(self.client_factory(),self.clock,self.monotonic)[1]

    def _history_time(self, client):
        # A burst of timeframe switches can share a recently measured clock.
        # Re-project via the original monotonic evidence, never reset its age,
        # uncertainty or TTL. Wall jumps invalidate reuse before any read.
        with self._clock_lock:
            if self._recent_clock is not None:
                at, evidence = self._recent_clock
                timing = StreamTiming(self.clock, self.monotonic)
                timing.seed(evidence)
                error, server, _ = timing.clock_state()
                if not error and 0 <= self.monotonic()-at <= 10:
                    return int(server), copy.deepcopy(evidence)
            stamp, evidence = measure_time(client, self.clock, self.monotonic)
            self._recent_clock = ((self.monotonic(), evidence)
                                  if evidence.get('state') == 'MEASURED' else None)
            return stamp, evidence

    def catalog(self):
        with self._catalog_lock:
            now = self.clock()
            if self._catalog is not None and 0 <= now - self._catalog_at < 300:
                return copy.deepcopy(self._catalog)
            try:
                data = self.client_factory().get('/fapi/v1/exchangeInfo')
                markets = []
                for item in data['symbols']:
                    if (item.get('status') != 'TRADING' or item.get('contractType') != 'PERPETUAL'
                            or item.get('quoteAsset') != 'USDT'
                            or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', item.get('symbol', ''))):
                        continue
                    filters = {v['filterType']: v for v in item.get('filters', [])}
                    tick = filters.get('PRICE_FILTER', {}).get('tickSize')
                    if tick is None or not 0 < float(tick) < float('inf'):
                        continue
                    markets.append({'symbol': item['symbol'], 'base_asset': item['baseAsset'],
                                    'quote_asset': 'USDT', 'contract_type': 'PERPETUAL', 'tick_size': tick, 'exact': exact_tick(tick)})
                if not markets:
                    raise ValueError()
                markets.sort(key=lambda m: (m['symbol'] != 'BTCUSDT', m['symbol'] != 'ETHUSDT', m['symbol']))
                self._catalog = {'source': SOURCE, 'environment': ENVIRONMENT, 'product': 'USD-M',
                                 'price_type': 'LAST_PRICE', 'observed_at': int(now * 1000),
                                 'intervals': list(INTERVALS), 'markets': markets}
                self._catalog_at = now
                return copy.deepcopy(self._catalog)
            except Exception:
                # No stale catalog is advertised as currently supported.
                raise MarketUnavailable('Piyasa listesi alınamadı.') from None

    def selection(self, symbol, interval):
        validate_selection(symbol, interval)
        market = next((m for m in self.catalog()['markets'] if m['symbol'] == symbol), None)
        if market is None:
            raise InvalidMarket('Bu USD-M sözleşmesi desteklenmiyor.')
        return market

    def history(self, symbol, interval, *, limit=300, end_time=None, force=False):
        validate_selection(symbol, interval)
        if type(limit) is not int or not 2 <= limit <= 499:
            raise InvalidMarket('Mum sayısı 2–499 olmalı.')
        if end_time is not None and (type(end_time) is not int or not 0 <= end_time <= 32503680000000):
            raise InvalidMarket('Geçersiz tarih aralığı.')
        # Same-interval reads deduplicate; another timeframe must not wait for
        # this interval's clock/REST network round trips. Cache mutation is brief.
        with self._history_locks[interval]:
            market = self.selection(symbol, interval)
            key = (symbol, interval, limit, end_time)
            with self._lock:
                cached = self._history_cache.get(key)
            now = self.clock()
            if not force and cached and 0 <= now - cached[0] <= 2:
                return copy.deepcopy(cached[1])
            try:
                client = self.client_factory()
                if force and end_time is None:
                    # Latest klines do not depend on a clock request. Keep clients
                    # separate and join both before validating/publishing anything.
                    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='chart-clock') as startup:
                        clock_job = startup.submit(self._history_time, self.client_factory())
                        raw = client.get('/fapi/v1/klines', {'symbol': symbol, 'interval': interval, 'limit': limit})
                        rows, normalized = normalize(raw, interval)
                        server_time, clock_sample = clock_job.result()
                    timing = StreamTiming(self.clock, self.monotonic)
                    timing.seed(clock_sample)
                    error, projected, _ = timing.clock_state()
                    if error:
                        raise MarketUnavailable('Borsa saati doğrulanamadı.')
                    server_time = int(projected)
                    if any(r[0] > server_time for r in rows):
                        raise MarketUnavailable('Mum zamanı doğrulanmış saatin ilerisinde.')
                else:
                    server_time, clock_sample = self._history_time(client)
                if type(server_time) is not int or server_time <= 0:
                    raise ValueError()
                cutoff = min(end_time, server_time) if end_time is not None else server_time
                if not (force and end_time is None):
                    rows, normalized = fetch_candles(client, symbol, interval, cutoff, bars=limit - 1)
                rows = [r for r in rows if r[0] <= cutoff][-limit:]
                # A valid empty older page means listing/history boundary, not an outage.
                # Initial feed snapshots still require real candles.
                if not rows and end_time is None:
                    raise ValueError()
                gaps = sum(max(0, (right[0] - left[0]) // INTERVALS[interval] - 1) for left, right in zip(rows, rows[1:]))
                missing_tail = bool(rows) and rows[-1][0] != bucket(cutoff, interval)
                store = CandleStore(self.database)
                try:
                    store.save(symbol, interval, rows, server_time)
                finally:
                    store.close()
                result = {'source': SOURCE, 'environment': ENVIRONMENT, 'product': 'USD-M',
                          'price_type': 'LAST_PRICE', 'symbol': symbol, 'interval': interval, 'market': market,
                          'clock_sample': clock_sample, 'server_time': server_time, 'observed_at': int(self.clock() * 1000),
                          'candles': [candle(r, cutoff) for r in rows], 'next_end_time': max(0, rows[0][0] - 1) if rows else None,
                          'has_more': len(rows) >= limit,
                          'quality': {'state': 'EMPTY' if not rows else ('GAP' if gaps else ('STALE' if missing_tail else 'OK')), 'missing_bars': gaps,
                                      'short_history': len(rows) < limit, **normalized}}
                result['precision'] = precision_summary(result['candles'], market)
                with self._lock:
                    self._history_cache[key] = (self.clock(), result)
                    self._history_cache.move_to_end(key)
                    while len(self._history_cache) > 24:
                        self._history_cache.popitem(last=False)
                return copy.deepcopy(result)
            except (InvalidMarket, MarketUnavailable):
                raise
            except Exception:
                raise MarketUnavailable('Mum verisi alınamadı veya doğrulanamadı.') from None


def normalize_kline(raw, symbol, interval):
    validate_selection(symbol, interval)
    if (not isinstance(raw, dict) or raw.get('e') != 'kline' or raw.get('s') != symbol
            or type(raw.get('E')) is not int):
        raise InvalidMarket('Geçersiz piyasa olayı.')
    k = raw.get('k')
    if (not isinstance(k, dict) or k.get('s') != symbol or k.get('i') != interval
            or type(k.get('t')) is not int or type(k.get('T')) is not int
            or type(k.get('x')) is not bool or raw['E'] < k['t']):
        raise InvalidMarket('Piyasa olayı bağlamı uyuşmuyor.')
    try:
        row = [k['t'], k['o'], k['h'], k['l'], k['c'], k['v'], k['T'], k['q'], k['n'], k['V'], k['Q'], '0']
        normalize([row], interval)
    except (KeyError, TypeError, ValueError):
        raise InvalidMarket('Piyasa mum olayı doğrulanamadı.') from None
    result = candle(row, k['T'] + 1 if k['x'] else k['t'])
    return {'event_time': raw['E'], 'raw': row, 'candle': result}
