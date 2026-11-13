"""Shared on-demand public kline feeds with reconnect and REST resynchronization."""
from collections import deque
import copy
import json
import threading
import time
import uuid
from decimal import Decimal

from .chart_evidence import snapshot
from .chart_clock import StreamTiming
from .chart_precision import precision_summary
from .chart_market import InvalidMarket, MarketUnavailable, normalize_kline
from .market_data import CandleStore, INTERVALS, SOURCE

WS_BASE = 'wss://fstream.binance.com/market/ws/'
MAX_STREAM_AGE_SECONDS = 20


class FeedUnavailable(RuntimeError):
    pass


class PublicSocket:
    def __init__(self, symbol, interval):
        import websocket
        self.timeout_error = websocket.WebSocketTimeoutException
        self.connection = websocket.create_connection(WS_BASE + symbol.lower() + '@kline_' + interval,
                                                       timeout=10, redirect_limit=0, enable_multithread=True)
        self.connection.settimeout(1)

    def receive(self):
        try:
            frame = self.connection.recv()
        except self.timeout_error:
            return None
        if not frame:
            raise FeedUnavailable()
        if len(frame) > 32768:
            raise InvalidMarket('Piyasa çerçevesi çok büyük.')
        return json.loads(frame)

    def close(self):
        try:
            self.connection.close(timeout=1)
        except Exception:
            pass


class FeedState:
    """Deterministic reducer; closed bars and event times never move backwards."""
    def __init__(self, symbol, interval, clock=time.time, monotonic=time.monotonic):
        self.symbol, self.interval, self.clock = symbol, interval, clock
        self.monotonic = monotonic
        self.timing = StreamTiming(clock, monotonic)
        self.last_receipt_mono = None
        self.seed_mono = None
        self.lock = threading.RLock()
        self.rows = []
        self.stream_epoch = uuid.uuid4().hex
        self.data_revision = 0
        self.evidence = None
        self.sequence = 0
        self.generation = 0
        self.state = 'CONNECTING'
        self.received_at = None
        self.last_event = 0
        self.server_time_at_seed = 0
        self.clock_at_seed = 0
        self.closed_keys = deque(maxlen=1000)
        self.last_close = None
        self.quality = {'state': 'UNKNOWN', 'missing_bars': 0}
        self.market = None

    def status(self, value):
        with self.lock:
            if self.state != value:
                self.state = value
                self.sequence += 1

    def seed(self, history):
        with self.lock:
            self.timing.seed(history.get('clock_sample'))
            self.seed_mono = self.last_receipt_mono = self.monotonic()
            self.rows = copy.deepcopy(history['candles'])
            self.market, self.quality = copy.deepcopy(history['market']), copy.deepcopy(history['quality'])
            self.stream_epoch = uuid.uuid4().hex
            self.last_event = history['server_time']
            self.received_at = self.clock()
            self.server_time_at_seed = history['server_time']
            self.clock_at_seed = self.received_at
            self.generation += 1
            self.sequence += 1
            self.state = 'SYNCING'
            self._capture_evidence()
            # Historical closes are not emitted as new live signals.
            for item in self.rows:
                if item['closed'] and item['time'] not in self.closed_keys:
                    self.closed_keys.append(item['time'])

    def apply(self, raw):
        event = normalize_kline(raw, self.symbol, self.interval)
        item, stamp = event['candle'], event['event_time']
        with self.lock:
            if not self.rows:
                raise FeedUnavailable()
            last = self.rows[-1]
            if stamp <= self.last_event or item['time'] < last['time']:
                return None
            expected_server_time = self.server_time_at_seed + max(0, self.monotonic() - self.seed_mono) * 1000
            if expected_server_time - stamp > MAX_STREAM_AGE_SECONDS * 1000:
                raise FeedUnavailable('Delayed public event; REST resync required')
            if item['time'] == last['time']:
                exact_volume = all(v.get('exact',{}).get('state')=='VERIFIED' for v in (item,last))
                decreased = (Decimal(item['exact']['volume']) < Decimal(last['exact']['volume']) if exact_volume else item['volume'] < last['volume'])
                if last['closed'] or decreased:
                    return None
            else:
                if item['time'] != last['time'] + INTERVALS[self.interval] // 1000 or not last['closed']:
                    raise FeedUnavailable('Missing candle/close; REST resync required')
            timing_error = self.timing.observe(stamp)
            if timing_error and self.timing.enforced:
                raise FeedUnavailable(timing_error)
            if item['time'] == last['time']:
                self.rows[-1] = item
            else:
                self.rows.append(item)
                self.rows = self.rows[-499:]
            self.last_event, self.received_at = stamp, self.clock()
            self.last_receipt_mono = self.monotonic()
            self.state = 'LIVE' if self.quality['state'] == 'OK' else 'GAP'
            self.sequence += 1
            if item['closed'] and item['time'] not in self.closed_keys:
                self.closed_keys.append(item['time'])
                self.last_close = {'event_id': f'{SOURCE}:{self.symbol}:{self.interval}:{item["time"]}:close',
                                   'time': item['time'], 'event_time': stamp}
            self._capture_evidence()
            return event

    def _capture_evidence(self):
        self.data_revision += 1
        self.evidence = snapshot(self.rows, self.market, self.quality, symbol=self.symbol,
                                 interval=self.interval, epoch=self.stream_epoch,
                                 generation=self.generation, revision=self.data_revision)

    def require_fresh(self):
        with self.lock:
            if self.last_receipt_mono is None or self.monotonic() - self.last_receipt_mono > MAX_STREAM_AGE_SECONDS:
                raise FeedUnavailable('Stale public stream')
            if self.timing.enforced and self.timing.proof()['reason'] in ('CLOCK_UNTRUSTED', 'SNAPSHOT_REQUIRED'):
                raise FeedUnavailable('Clock/resynchronization required')

    def packet(self, generation=0, stream_epoch=None):
        with self.lock:
            state = self.state
            if state == 'LIVE' and (self.received_at is None or self.monotonic() - self.last_receipt_mono > 10):
                state = 'STALE'
            result = {'type': 'snapshot' if generation != self.generation or stream_epoch is not None and stream_epoch != self.stream_epoch else 'update',
                      'stream_epoch': self.stream_epoch,
                      'data_proof': self.evidence.view() if self.evidence is not None else None,
                      'source': SOURCE, 'environment': 'live_public', 'product': 'USD-M', 'price_type': 'LAST_PRICE',
                      'symbol': self.symbol, 'interval': self.interval, 'status': state,
                      'sequence': self.sequence, 'generation': self.generation,
                      'observed_at': int(self.clock() * 1000),
                      'received_at': int(self.received_at * 1000) if self.received_at is not None else None,
                      'quality': copy.deepcopy(self.quality), 'market': copy.deepcopy(self.market), 'close_event': copy.deepcopy(self.last_close),
                      'precision': precision_summary(self.rows, self.market), 'timing': self.timing.proof()}
            if result['type'] == 'snapshot':
                result['candles'] = copy.deepcopy(self.rows)
            else:
                result['candle'] = copy.deepcopy(self.rows[-1]) if self.rows else None
                result['tail'] = copy.deepcopy(self.rows[-2:])
            return result


class SharedFeed:
    def __init__(self, market, symbol, interval, *, socket_factory=PublicSocket, clock=time.time, monotonic=time.monotonic):
        self.market, self.symbol, self.interval = market, symbol, interval
        self.clock, self.socket_factory, self.monotonic = clock, socket_factory, monotonic
        self.state = FeedState(symbol, interval, clock, monotonic)
        self.references = 0
        self.last_used = monotonic()
        self.stop_event = threading.Event()
        self.socket = None
        self.thread = threading.Thread(target=self.run, daemon=True, name='public-kline-' + symbol + '-' + interval)

    def run(self):
        failures = 0
        while not self.stop_event.is_set():
            if self.references == 0 and self.monotonic() - self.last_used > 60:
                break
            try:
                self.state.status('CONNECTING' if failures == 0 else 'RECONNECTING')
                self.socket = self.socket_factory(self.symbol, self.interval)
                self.state.status('SYNCING')
                self.state.seed(self.market.history(self.symbol, self.interval, force=True))
                if not self.state.timing.enforced:
                    raise FeedUnavailable('CLOCK_UNTRUSTED')
                last_flush = 0
                while not self.stop_event.is_set():
                    if self.references == 0 and self.monotonic() - self.last_used > 60:
                        return
                    raw = self.socket.receive()
                    # Any frame can be stale: duplicate traffic must not defeat the watchdog.
                    self.state.require_fresh()
                    if raw is None:
                        continue
                    event = self.state.apply(raw)
                    if event is None:
                        continue
                    failures = 0
                    # Closed bars are saved immediately; open bars at most every 2s.
                    if event['candle']['closed'] or self.monotonic() - last_flush >= 2:
                        store = CandleStore(self.market.database)
                        try:
                            store.save(self.symbol, self.interval, [event['raw']], event['event_time'])
                        finally:
                            store.close()
                        last_flush = self.monotonic()
            except Exception:
                failures += 1
                self.state.status('RECONNECTING')
            finally:
                if self.socket is not None:
                    self.socket.close()
                    self.socket = None
            self.stop_event.wait(min(30, 2 ** min(failures, 5)))
        self.state.status('STOPPED')

    def stop(self):
        self.stop_event.set()
        if self.socket is not None:
            self.socket.close()


class MarketFeedHub:
    def binding_context(self, symbol, interval):
        """Detached server evidence from an already subscribed feed; no network action."""
        with self.lock:
            feed = self.feeds.get((symbol, interval))
            if self.closed or feed is None or feed.references <= 0:
                return None
            state = feed.state
            with state.lock:
                if state.evidence is None:
                    return None
                return copy.deepcopy(dict(
                    identity=dict(source=SOURCE, environment='live_public', product='USD-M',
                                  price_type='LAST_PRICE', symbol=symbol, interval=interval),
                    transport_state=state.state, rows=state.rows, market=state.market, quality=state.quality,
                    stream_epoch=state.stream_epoch, generation=state.generation,
                    data_revision=state.data_revision, event_time=state.last_event, data_proof=state.evidence.view(),
                    timing=state.timing.proof()))

    def __init__(self, market, *, socket_factory=PublicSocket, clock=time.time, monotonic=time.monotonic, max_feeds=8):
        self.market, self.socket_factory, self.clock = market, socket_factory, clock
        self.monotonic = monotonic
        self.max_feeds, self.feeds, self.lock = max_feeds, {}, threading.RLock()
        self.closed = False

    def acquire(self, symbol, interval):
        self.market.selection(symbol, interval)
        with self.lock:
            if self.closed:
                raise FeedUnavailable()
            for key, feed in list(self.feeds.items()):
                if not feed.thread.is_alive():
                    self.feeds.pop(key)
            key = (symbol, interval)
            feed = self.feeds.get(key)
            if feed is None:
                if len(self.feeds) >= self.max_feeds:
                    idle = next((k for k, f in self.feeds.items() if f.references == 0), None)
                    if idle is not None:
                        retired = self.feeds[idle]
                        retired.stop()
                        retired.thread.join(timeout=1)
                        if retired.thread.is_alive():
                            raise FeedUnavailable('Önceki veri bağlantısı kapanıyor.')
                        self.feeds.pop(idle)
                    else:
                        raise FeedUnavailable('Piyasa abonelik sınırı.')
                feed = SharedFeed(self.market, symbol, interval, socket_factory=self.socket_factory, clock=self.clock, monotonic=self.monotonic)
                self.feeds[key] = feed
                feed.references = 1
                feed.thread.start()
            else:
                if feed.references >= 16:
                    raise FeedUnavailable('İstemci sınırı.')
                feed.references += 1
            return feed

    def release(self, feed):
        with self.lock:
            feed.references = max(0, feed.references - 1)
            feed.last_used = self.monotonic()

    def close(self):
        with self.lock:
            self.closed = True
            feeds = list(self.feeds.values())
            for feed in feeds:
                feed.stop()
        for feed in feeds:
            feed.thread.join(timeout=2)
