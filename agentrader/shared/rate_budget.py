"""Atomic local reservations for the documented shared UM/CM pools.

UID is deliberately over-scoped to every local key: a key hash is not a UID.
External clients/NAT traffic remain outside local reservations; observations
are added conservatively, never used to refund an in-flight request.
"""
import json
import math
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit, parse_qs

from agentrader.shared.errors import ExchangeError

HOSTS = {
    'demo-fapi.binance.com': ('demo', 'REST'),
    'demo-dapi.binance.com': ('demo', 'REST'),
    'fapi.binance.com': ('production', 'REST'),
    'dapi.binance.com': ('production', 'REST'),
    'testnet.binancefuture.com': ('demo', 'WS'),
    'ws-fapi.binance.com': ('production', 'WS'),
}
INTERVALS = {'SECOND': 1, 'MINUTE': 60, 'HOUR': 3600, 'DAY': 86400}


def context(host):
    return HOSTS.get(host)


def charges(environment, channel, weight, orders=0, *, trade_overlap=0):
    rows = [(f'futures:{environment}:ip:{channel}', 'REQUEST_WEIGHT', 60, 2400, weight)]
    if trade_overlap and channel == 'REST':
        rows.append((f'futures:{environment}:ip:WS', 'REQUEST_WEIGHT', 60, 2400, trade_overlap))
    if orders:
        rows += [(f'futures:{environment}:uid:LOCAL_ALL_KEYS', 'ORDERS', seconds, limit, orders)
                 for seconds, limit in ((10, 300), (60, 1200))]
    return [r for r in rows if r[-1]]


def rest_charges(request):
    url = urlsplit(request.full_url); scope = context(url.netloc)
    if scope is None or scope[1] != 'REST':
        return []
    env, channel = scope; path = url.path; method = request.get_method()
    if path.startswith('/futures/data/'):
        return charges(env,channel,1)+[(f'futures:{env}:data:LOCAL_IP','REQUESTS',300,1000,1)]
    if not path.startswith(('/fapi/', '/dapi/')): return []
    params = parse_qs(url.query); name = path.rsplit('/', 1)[-1]
    if name in ('fundingRate','fundingInfo'):
        return charges(env,channel,1)+[(f'futures:{env}:funding:LOCAL_IP','REQUESTS',300,500,1)]
    # Documented maxima for variable reads, with deliberately conservative
    # fallback for existing allowed routes whose exact cost is not pinned here.
    weight = {'ping': 1, 'time': 1, 'exchangeInfo': 1, 'account': 5,
              'positionRisk': 5, 'openOrders': 40, 'openAlgoOrders': 40,
              'userTrades': 5, 'income': 30, 'orderAmendment': 1,
              'depth': 20, 'rpiDepth': 20, 'klines': 10,
              'continuousKlines': 10, 'indexPriceKlines': 10,
              'markPriceKlines': 10, 'premiumIndexKlines': 10,
              'ticker': 40}.get(name, 100)
    if name in ('openOrders', 'openAlgoOrders') and params.get('symbol'): weight = 1
    orders = 0; overlap = 0
    if name in ('order', 'algoOrder', 'batchOrders'):
        weight = 1
        if method in ('POST', 'PUT'):
            orders = 1
            if name == 'batchOrders':
                try: orders = max(1, len(json.loads(params.get('batchOrders', ['[]'])[0])))
                except (ValueError, TypeError): orders = 5
                weight = 5 if method == 'POST' else 10
            elif name == 'order': weight = 0
        if method != 'GET': overlap = max(1, weight)  # stricter than zero-cost placements
    # Export requests carry a large documented weight, not the generic fallback.
    if path.endswith('/asyn'): weight = 1000
    elif path.endswith('/asyn/id'): weight = 10
    return charges(env, channel, weight, orders, trade_overlap=overlap)


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS rate_buckets (
        pool TEXT, kind TEXT, seconds INTEGER, window INTEGER,
        local_count INTEGER NOT NULL, observed INTEGER NOT NULL, ceiling INTEGER NOT NULL,
        PRIMARY KEY(pool,kind,seconds,window))''')
    db.execute('CREATE TABLE IF NOT EXISTS pool_cooldowns (pool TEXT PRIMARY KEY, until_ts REAL NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS rate_clock (id INTEGER PRIMARY KEY CHECK(id=1), last_ts REAL NOT NULL)')
    db.execute('''CREATE TABLE IF NOT EXISTS rate_dimensions (
        pool TEXT, kind TEXT, seconds INTEGER, ceiling INTEGER NOT NULL,
        PRIMARY KEY(pool,kind,seconds))''')


def check_clock(db, now):
    row = db.execute('SELECT last_ts FROM rate_clock WHERE id=1').fetchone()
    if row and now < row[0]:
        raise ExchangeError('Kota saati geriye gitti; saat doğrulanmadan istek gönderilmedi.', delivery_status='NOT_SENT')
    db.execute('INSERT INTO rate_clock VALUES (1,?) ON CONFLICT(id) DO UPDATE SET last_ts=excluded.last_ts', (now,))


def reserve(governor, rows):
    if not rows: return
    now = governor.clock()
    if not math.isfinite(now) or now < 0: raise ValueError('RATE_CLOCK_INVALID')
    governor.path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(governor.path, timeout=10)) as db:
        with db:
            db.execute('BEGIN IMMEDIATE'); schema(db)
            now = governor.clock()  # Sample after acquiring the cross-process lock.
            check_clock(db, now)
            rows = list(rows)
            dimensions = {(pool, kind, seconds) for pool, kind, seconds, _, _ in rows}
            for pool, kind, _, _, cost in list(rows):
                for seconds, ceiling in db.execute('SELECT seconds,ceiling FROM rate_dimensions WHERE pool=? AND kind=?', (pool,kind)).fetchall():
                    if (pool,kind,seconds) not in dimensions:
                        dimensions.add((pool,kind,seconds)); rows.append((pool,kind,seconds,ceiling,cost))
            # All dimensions are checked and charged in one transaction.
            for pool, kind, seconds, limit, cost in rows:
                if any(type(v) is not int or v <= 0 for v in (seconds, limit, cost)):
                    raise ValueError('RATE_CHARGE_INVALID')
                db.execute('''INSERT INTO rate_dimensions VALUES (?,?,?,?) ON CONFLICT(pool,kind,seconds)
                    DO UPDATE SET ceiling=MIN(ceiling,excluded.ceiling)''',(pool,kind,seconds,limit))
                limit = db.execute('SELECT ceiling FROM rate_dimensions WHERE pool=? AND kind=? AND seconds=?',(pool,kind,seconds)).fetchone()[0]
                cooldown = db.execute('SELECT until_ts FROM pool_cooldowns WHERE pool=?', (pool,)).fetchone()
                if cooldown and cooldown[0] > now: _blocked(cooldown[0]-now)
                window = int(now)//seconds
                row = db.execute('SELECT local_count,observed,ceiling FROM rate_buckets WHERE pool=? AND kind=? AND seconds=? AND window=?', (pool, kind, seconds, window)).fetchone()
                used = row[0]+row[1] if row else 0
                ceiling = min(limit, row[2]) if row else limit
                if used+cost > ceiling: _blocked((window+1)*seconds-now+1)
                db.execute('''INSERT INTO rate_buckets VALUES (?,?,?,?,?,0,?)
                    ON CONFLICT(pool,kind,seconds,window) DO UPDATE SET
                    local_count=local_count+excluded.local_count, ceiling=MIN(ceiling,excluded.ceiling)''',
                    (pool, kind, seconds, window, cost, ceiling))
            db.execute('DELETE FROM rate_buckets WHERE (window+2)*seconds<?', (now,))


def _blocked(delay):
    raise ExchangeError('Ortak istek bütçesi dolu; istek gönderilmedi.', http_status=429,
                        delivery_status='NOT_SENT', retry_after=delay)


def observe(governor, host, limits=(), retry=None):
    scope = context(host)
    if scope is None: return
    env, channel = scope; now = governor.clock()
    governor.path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(governor.path, timeout=10)) as db:
        with db:
            db.execute('BEGIN IMMEDIATE'); schema(db)
            now = governor.clock()
            check_clock(db, now)
            if retry is not None:
                # Ban scope may be broader than one host: conservatively stop
                # both futures transports and all local account keys.
                for pool in (f'futures:{env}:ip:REST', f'futures:{env}:ip:WS', f'futures:{env}:uid:LOCAL_ALL_KEYS'):
                    db.execute('INSERT INTO pool_cooldowns VALUES (?,?) ON CONFLICT(pool) DO UPDATE SET until_ts=MAX(until_ts,excluded.until_ts)', (pool, now+retry))
            for item in limits:
                if not isinstance(item, dict): continue
                kind = item.get('rateLimitType'); unit = INTERVALS.get(item.get('interval'))
                count, mult, ceiling = item.get('count'), item.get('intervalNum'), item.get('limit')
                if kind not in ('REQUEST_WEIGHT', 'ORDERS') or not unit: continue
                if any(type(v) is not int or not 0 <= v <= 10**9 for v in (count, mult, ceiling)) or not mult or not ceiling: continue
                seconds = unit*mult
                pool = f'futures:{env}:ip:{channel}' if kind == 'REQUEST_WEIGHT' else f'futures:{env}:uid:LOCAL_ALL_KEYS'
                db.execute('''INSERT INTO rate_dimensions VALUES (?,?,?,?) ON CONFLICT(pool,kind,seconds)
                    DO UPDATE SET ceiling=MIN(ceiling,excluded.ceiling)''',(pool,kind,seconds,ceiling))
                db.execute('''INSERT INTO rate_buckets VALUES (?,?,?,?,0,?,?)
                    ON CONFLICT(pool,kind,seconds,window) DO UPDATE SET
                    observed=MAX(observed,excluded.observed),ceiling=MIN(ceiling,excluded.ceiling)''',
                    (pool, kind, seconds, int(now)//seconds, count, ceiling))


def header_observations(headers):
    result = []
    import re
    for name, value in headers.items():
        match = re.fullmatch(r'x-mbx-(used-weight|order-count)-(\d+)([smhd])', name)
        if match:
            kind = 'REQUEST_WEIGHT' if match[1] == 'used-weight' else 'ORDERS'
            unit = {'s':'SECOND','m':'MINUTE','h':'HOUR','d':'DAY'}[match[3]]
            seconds = int(match[2])*INTERVALS[unit]
            ceiling = 2400 if kind == 'REQUEST_WEIGHT' else {10:300,60:1200}.get(seconds)
            if ceiling: result.append(dict(rateLimitType=kind, interval=unit, intervalNum=int(match[2]), limit=ceiling, count=value))
    return result
