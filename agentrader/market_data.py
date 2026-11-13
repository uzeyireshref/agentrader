"""Anahtarsız, salt okunur canlı USD-M piyasa verisi ve ayrı SQLite deposu."""
import hashlib
import json
import re
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .exchange import ExchangeError, NoRedirect
from .transport import JsonTransport

LIVE_URL = 'https://fapi.binance.com'
SOURCE = 'binance_usdm_live_trade_price'
INTERVALS = {'1w': 604800000, '1d': 86400000, '4h': 14400000, '1h': 3600000, '15m': 900000, '30m': 1800000, '5m': 300000, '1m': 60000}
WEEK_ANCHOR = 345600000  # 1970-01-05 Monday, UTC


def bucket(timestamp, interval):
    step = INTERVALS[interval]
    anchor = WEEK_ANCHOR if interval == '1w' else 0
    return (timestamp - anchor) // step * step + anchor


class PublicMarket:
    """İşlem/hesap endpointi, API key, secret veya POST yöntemi kabul etmez."""
    def __init__(self, *, transport=None):
        self.opener = build_opener(NoRedirect())
        self.transport = transport or JsonTransport()

    def get(self, path, params=None):
        allowed = {'/fapi/v1/time': set(), '/fapi/v1/exchangeInfo': set(), '/fapi/v1/premiumIndex': {'symbol'},
                   '/fapi/v1/klines': {'symbol', 'interval', 'endTime', 'limit'}}
        params = dict(params or {})
        if path not in allowed or set(params) - allowed[path]:
            raise ValueError('Salt okunur piyasa endpointi/parametresi desteklenmiyor.')
        if path.endswith('premiumIndex') and not re.fullmatch(r'[A-Z0-9]{2,20}USDT', params.get('symbol', '')):
            raise ValueError('Mark fiyatı için geçerli USDT sembolü gerekli.')
        if path.endswith('klines'):
            if params.get('interval') not in INTERVALS or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', params.get('symbol', '')):
                raise ValueError('Piyasa sembolü veya zaman dilimi geçersiz.')
            if type(params.get('limit')) is not int or not 1 <= params['limit'] <= 499:
                raise ValueError('Piyasa sayfa boyutu 1–499 olmalı.')
            if type(params.get('endTime')) is not int or params['endTime'] < 0:
                raise ValueError('Mum bitiş sorgusu geçersiz.')
        factory = lambda:Request(LIVE_URL + path + ('?' + urlencode(params) if params else ''), method='GET')
        try:
            result = self.transport.perform(self.opener,factory,'GET',LIVE_URL)
            if path.endswith('/time') and (not isinstance(result, dict) or type(result.get('serverTime')) is not int or result['serverTime'] <= 0):
                raise ValueError('Geçersiz sunucu saati.')
            if path.endswith('exchangeInfo') and (not isinstance(result, dict) or not isinstance(result.get('symbols'), list)
                                                  or any(not isinstance(s, dict) or not isinstance(s.get('symbol'), str) for s in result['symbols'])):
                raise ValueError('Geçersiz sembol bilgisi.')
            return result
        except ValueError:
            raise ExchangeError('Canlı piyasa yanıtı geçerli JSON veya beklenen veri şeması değil.') from None


def normalize(rows, interval):
    if not isinstance(rows, list):
        raise ValueError('Mum yanıtı liste olmalı.')
    unique, duplicate_count = {}, 0
    previous = None
    reordered = False
    step = INTERVALS[interval]
    for row in rows:
        if not isinstance(row, list) or len(row) != 12:
            raise ValueError('Mum satırı 12 Binance kline alanı içermeli.')
        if type(row[0]) is not int or type(row[6]) is not int or type(row[8]) is not int or row[8] < 0:
            raise ValueError('Mum zaman/işlem sayısı alanı geçersiz.')
        if row[0] < 0 or bucket(row[0], interval) != row[0] or row[6] != row[0] + step - 1:
            raise ValueError('Mum zaman aralığı veya UTC hizası hatalı.')
        try:
            op, hi, lo, cl, base, quote, taker_base, taker_quote = [Decimal(str(row[i])) for i in (1, 2, 3, 4, 5, 7, 9, 10)]
        except (InvalidOperation, ValueError):
            raise ValueError('Mum sayısal alanı geçersiz.') from None
        if (not all(v.is_finite() and -30 <= v.adjusted() <= 30 for v in (op, hi, lo, cl, base, quote, taker_base, taker_quote))
                or min(op, hi, lo, cl) <= 0 or min(base, quote, taker_base, taker_quote) < 0
                or lo > min(op, cl) or hi < max(op, cl) or lo > hi
                or taker_base > base or taker_quote > quote):
            raise ValueError('Mum OHLC/hacim bütünlüğü hatalı.')
        if row[0] in unique:
            if unique[row[0]] != row:
                raise ValueError('Aynı açılış zamanında çelişen mumlar var.')
            duplicate_count += 1
        unique[row[0]] = row
        if previous is not None and row[0] < previous:
            reordered = True
        previous = row[0]
    return [unique[t] for t in sorted(unique)], {'duplicates_removed': duplicate_count, 'reordered': reordered}


def fetch_candles(client, symbol, interval, as_of_ms, bars=300):
    collected = {}
    end = as_of_ms
    duplicates, reordered = 0, False
    for _ in range((bars + 1 + 498) // 499 + 2):
        count = min(499, bars + 1 - len(collected))
        if count <= 0:
            break
        raw = client.get('/fapi/v1/klines', {'symbol': symbol, 'interval': interval, 'endTime': end, 'limit': count})
        rows, quality = normalize(raw, interval)
        duplicates += quality['duplicates_removed']
        reordered |= quality['reordered']
        if not rows:
            break
        if rows[-1][0] > end:
            raise ValueError('Sağlayıcı sorgunun bitiş zamanından sonraki mum döndürdü.')
        for row in rows:
            if row[0] in collected and collected[row[0]] != row:
                raise ValueError('Sayfalar arasında çelişen mum var.')
            collected[row[0]] = row
        next_end = rows[0][0] - 1
        if next_end >= end:
            raise ValueError('Mum sayfalaması ilerlemiyor.')
        end = next_end
        if end < 0 or len(rows) < count:
            break
    return [collected[t] for t in sorted(collected)], {'duplicates_removed': duplicates, 'reordered': reordered}


class CandleStore:
    def __init__(self, path=Path('data/market.sqlite3')):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS candles (
              source TEXT NOT NULL,symbol TEXT NOT NULL,interval TEXT NOT NULL,
              open_time INTEGER NOT NULL,close_time INTEGER NOT NULL,raw TEXT NOT NULL,
              observed_at INTEGER NOT NULL,PRIMARY KEY(source,symbol,interval,open_time));
            CREATE TABLE IF NOT EXISTS analysis_runs (
              run_id INTEGER PRIMARY KEY,as_of_ms INTEGER NOT NULL,input_hash TEXT NOT NULL,
              inputs TEXT NOT NULL,report TEXT NOT NULL);
        ''')

    def save(self, symbol, interval, rows, observed_at):
        normalized, _ = normalize(rows, interval)
        revisions = 0
        with self.db:
            for row in normalized:
                raw = json.dumps(row, separators=(',', ':'))
                old = self.db.execute('SELECT raw FROM candles WHERE source=? AND symbol=? AND interval=? AND open_time=?',
                                      (SOURCE, symbol, interval, row[0])).fetchone()
                if old and old[0] != raw and row[6] < observed_at:
                    # Açık mumun doğal güncellemesi, kapanmış veri revizyonu değildir.
                    previous = self.db.execute('SELECT observed_at FROM candles WHERE source=? AND symbol=? AND interval=? AND open_time=?',
                                               (SOURCE, symbol, interval, row[0])).fetchone()[0]
                    revisions += previous > row[6]
                self.db.execute('INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?)',
                                (SOURCE, symbol, interval, row[0], row[6], raw, observed_at))
        return revisions

    def load(self, symbol, interval, as_of_ms, bars=300):
        rows = self.db.execute('SELECT raw FROM candles WHERE source=? AND symbol=? AND interval=? AND open_time<=? ORDER BY open_time DESC LIMIT ?',
                               (SOURCE, symbol, interval, as_of_ms, bars + 1)).fetchall()
        return [json.loads(r[0]) for r in reversed(rows)]

    def record_run(self, as_of_ms, inputs, report):
        encoded = json.dumps(inputs, sort_keys=True, separators=(',', ':'))
        checksum = hashlib.sha256(encoded.encode()).hexdigest()
        report['input_hash'] = checksum
        with self.db:
            cursor = self.db.execute('INSERT INTO analysis_runs(as_of_ms,input_hash,inputs,report) VALUES (?,?,?,?)',
                                     (as_of_ms, checksum, encoded, json.dumps(report, ensure_ascii=False)))
        return cursor.lastrowid

    def close(self):
        self.db.close()
