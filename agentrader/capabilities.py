"""Versioned capability inventory and bounded read-only demo discovery.

Successful GETs prove only that read operation, never permission to trade.
The documentation catalog cannot add routes to the exchange allowlist.
"""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from collections import Counter
from importlib.resources import files

from .exchange import BASE_URL, ExchangeError, allowed_requests
from .risk import number


CATALOG_SCHEMA = 1
PROBE_VERSION = 'demo-read-only-v1'
PROBES = (
    ('ping', '/fapi/v1/ping', False, False),
    ('time', '/fapi/v1/time', False, False),
    ('symbol', '/fapi/v1/exchangeInfo', False, False),
    ('mark', '/fapi/v1/premiumIndex', False, True),
    ('account', '/fapi/v3/account', True, False),
    ('position_mode', '/fapi/v1/positionSide/dual', True, False),
    ('symbol_config', '/fapi/v1/symbolConfig', True, True),
    ('leverage_brackets', '/fapi/v1/leverageBracket', True, True),
    ('positions', '/fapi/v3/positionRisk', True, True),
    ('open_orders', '/fapi/v1/openOrders', True, True),
    ('open_algos', '/fapi/v1/openAlgoOrders', True, True),
    ('account_config', '/fapi/v1/accountConfig', True, False),
)


def load_catalog():
    data = json.loads(files('agentrader').joinpath('data/usdm_capabilities.json').read_text(encoding='utf-8'))
    if data.get('schema_version') != CATALOG_SCHEMA or not isinstance(data.get('operations'), list):
        raise ValueError('Desteklenmeyen yetenek kataloğu.')
    seen = set()
    for row in data['operations']:
        if not re.fullmatch(r'UM-\d{3}', row['id']) or row['id'] in seen:
            raise ValueError('Katalog kimlikleri geçersiz veya tekrarlı.')
        seen.add(row['id'])
        if row['method'] not in ('GET', 'POST', 'PUT', 'DELETE'):
            raise ValueError('Katalog yöntemi geçersiz.')
        path = row['reference_path']
        if path is not None and not re.fullmatch(r'/(?:fapi|futures)/[A-Za-z0-9/_]+', path):
            raise ValueError('Katalog adresi geçersiz.')
    data['catalog_sha256'] = hashlib.sha256(json.dumps(data['operations'], sort_keys=True).encode()).hexdigest()
    return data


def list_capabilities(category=None):
    catalog = load_catalog()
    if category and category not in catalog['counts']:
        raise ValueError('Bilinmeyen yetenek kategorisi.')
    allowed = allowed_requests()
    rows = []
    for item in catalog['operations']:
        if category and item['category'] != category:
            continue
        rows.append({'id': item['id'], 'name': item['name_tr'], 'category': item['category'],
                     'method': item['method'], 'path': item['reference_path'],
                     'documented': True, 'adapter_allowed': (item['method'], item['reference_path']) in allowed,
                     'current_read_access': 'NOT_PROBED', 'write_permission': 'NOT_VERIFIED',
                     'workflow_status': 'NOT_ASSESSED', 'source': item['source_url']})
    return {'schema_version': 1, 'environment': 'demo', 'product': 'USD-M',
            'catalog_review_date': catalog['review_date'], 'catalog_sha256': catalog['catalog_sha256'],
            'count': len(rows), 'adapter_allowed_count': sum(r['adapter_allowed'] for r in rows),
            'read_only': True, 'operations': rows}


def failure_status(error):
    if error.http_status in (418, 429): return 'RATE_LIMITED'
    if error.http_status == 451: return 'REGION_OR_ACCESS_RESTRICTED'
    if error.http_status == 403: return 'ACCESS_BLOCKED'
    if error.code in (-2014, -2015): return 'AUTH_OR_PERMISSION_DENIED'
    if error.code == -1022: return 'SIGNATURE_ERROR'
    if error.code == -1021: return 'CLOCK_OR_TIMESTAMP_ERROR'
    if error.code == -1121: return 'SYMBOL_NOT_AVAILABLE'
    if error.http_status == 404: return 'ENDPOINT_OR_ROUTE_NOT_AVAILABLE'
    return 'NETWORK_OR_SERVER_ERROR'


def _summary(name, payload, symbol):
    """Only validated, minimal fields are allowed into reports; never raw responses."""
    if name == 'ping':
        if not isinstance(payload, dict): raise ValueError('Bağlantı yanıtı geçersiz.')
        return {'responded': True}
    if name == 'time':
        value = payload['serverTime']
        if type(value) is not int or value <= 0: raise ValueError('Saat yanıtı geçersiz.')
        return {'server_time_ms': value}
    if name == 'symbol':
        selected = next(s for s in payload['symbols'] if s['symbol'] == symbol)
        filters = {f['filterType']: f for f in selected['filters']}
        result = {'symbol': symbol, 'trading': selected['status'] == 'TRADING',
                  'usdt_perpetual': selected.get('quoteAsset') == 'USDT' and selected.get('contractType') == 'PERPETUAL'}
        for field, filter_name, key in [('price_tick','PRICE_FILTER','tickSize'), ('quantity_step','LOT_SIZE','stepSize'),
                                        ('minimum_notional','MIN_NOTIONAL','notional')]:
            value = number(filters[filter_name][key])
            if value <= 0: raise ValueError('Sembol filtresi geçersiz.')
            result[field] = str(value)
        return result
    if name == 'mark':
        price, stamp = number(payload['markPrice']), payload['time']
        if payload['symbol'] != symbol or price <= 0 or type(stamp) is not int:
            raise ValueError('Fiyat yanıtı geçersiz.')
        return {'symbol': symbol, 'mark_price': str(price), 'exchange_time_ms': stamp}
    if name == 'account':
        flag = payload.get('canTrade')
        if (not isinstance(payload.get('assets'),list) or not isinstance(payload.get('positions'),list)
                or ('canTrade' in payload and type(flag) is not bool)):
            raise ValueError('Hesap yanıtı geçersiz.')
        number(payload['availableBalance'])
        return {'account_can_trade_flag': flag,
                'trade_flag_status': 'EXPOSED' if flag is not None else 'NOT_EXPOSED_BY_ACCOUNT_V3',
                'balance_schema_verified': True, 'write_permission': 'NOT_VERIFIED'}
    if name == 'position_mode':
        value = payload['dualSidePosition']
        if type(value) is not bool: raise ValueError('Pozisyon modu geçersiz.')
        return {'position_mode': 'hedge' if value else 'one-way'}
    if name == 'account_config':
        flag, multi = payload['canTrade'], payload['multiAssetsMargin']
        if type(flag) is not bool or type(multi) is not bool:
            raise ValueError('Hesap yapılandırması geçersiz.')
        return {'account_can_trade_flag': flag, 'multi_assets_margin': multi,
                'write_permission': 'NOT_VERIFIED'}
    if name == 'symbol_config':
        selected = next(r for r in payload if r['symbol'] == symbol)
        leverage = int(selected['leverage'])
        margin = selected['marginType']
        if not 1 <= leverage <= 125 or margin not in ('CROSSED', 'ISOLATED'):
            raise ValueError('Sembol yapılandırması geçersiz.')
        return {'leverage': leverage, 'margin_type': margin}
    if name == 'leverage_brackets':
        selected = next(r for r in payload if r['symbol'] == symbol)
        brackets = selected['brackets']
        if not brackets: raise ValueError('Kaldıraç basamakları eksik.')
        for b in brackets:
            if int(b['initialLeverage']) < 1 or number(b['notionalCap']) <= 0:
                raise ValueError('Kaldıraç basamağı geçersiz.')
        return {'bracket_count': len(brackets), 'maximum_listed_leverage': max(int(b['initialLeverage']) for b in brackets),
                'note': 'Üst kaldıraç tüm pozisyon büyüklüklerine uygulanmaz.'}
    if name in ('positions', 'open_orders', 'open_algos'):
        if not isinstance(payload, list): raise ValueError('Liste yanıtı geçersiz.')
        if name == 'positions':
            return {'nonzero_position_count': sum(number(p['positionAmt']) != 0 for p in payload)}
        return {'open_count': len(payload)}
    raise ValueError('Bilinmeyen keşif işlemi.')


def probe_capabilities(exchange, symbol='BTCUSDT', *, include_account=False):
    if not re.fullmatch(r'[A-Z0-9]{2,20}USDT', symbol):
        raise ValueError('Geçerli USDT sembolü gerekli.')
    report = list_capabilities()
    key = exchange.config.api_key
    report.update(run_id=uuid.uuid4().hex, probe_version=PROBE_VERSION, symbol=symbol,
                  base_url=BASE_URL, started_at_ms=int(time.time()*1000),
                  credential_ref=hashlib.sha256(key.encode()).hexdigest()[:16] if key and include_account else None,
                  account_requested=include_account, exchange_mutations=0, checks=[])
    blocked = None
    auth_blocked = None
    by_path = {}
    for name, path, private, scoped in PROBES:
        check = {'name': name, 'method': 'GET', 'path': path, 'private': private,
                 'observed_at_ms': int(time.time()*1000)}
        if blocked:
            check['status'] = 'SKIPPED_AFTER_ERROR'
        elif private and not include_account:
            check['status'] = 'ACCOUNT_NOT_REQUESTED'
        elif private and not key:
            check['status'] = 'CREDENTIALS_MISSING'
        elif private and auth_blocked:
            check['status'] = 'SKIPPED_AFTER_PRIVATE_ERROR'
        else:
            if ('GET', path) not in allowed_requests():
                raise ValueError('Keşif adresi adaptör izin listesinde değil.')
            before = time.time()*1000
            try:
                payload = exchange.get(path, {'symbol': symbol} if scoped else None)
                check.update(status='READ_VERIFIED', summary=_summary(name, payload, symbol))
                if name == 'time':
                    exchange.offset_ms = round(check['summary']['server_time_ms'] - (before+time.time()*1000)/2)
                if name == 'mark':
                    age = (time.time()*1000 + exchange.offset_ms - check['summary']['exchange_time_ms'])/1000
                    check['summary'].update(age_seconds=round(age,3), fresh_for_execution=-1 <= age <= 15)
            except ExchangeError as exc:
                check.update(status=failure_status(exc), error_code=exc.code, http_status=exc.http_status)
                if check['status'] in ('RATE_LIMITED','REGION_OR_ACCESS_RESTRICTED','ACCESS_BLOCKED','NETWORK_OR_SERVER_ERROR'):
                    blocked = check['status']
                elif private:
                    auth_blocked = check['status']
            except (ValueError, KeyError, TypeError, StopIteration, OverflowError):
                check['status'] = 'INVALID_RESPONSE'
        report['checks'].append(check)
        by_path[path] = check
    for row in report['operations']:
        check = by_path.get(row['path']) if row['method'] == 'GET' else None
        if check:
            row['current_read_access'] = check['status']
        # A successful read never promotes POST/PUT/DELETE or workflow readiness.
    report['finished_at_ms'] = int(time.time()*1000)
    report['check_counts'] = dict(Counter(c['status'] for c in report['checks']))
    report['status'] = 'READ_CHECKS_PASSED' if all(
        c['status'] in ('READ_VERIFIED','ACCOUNT_NOT_REQUESTED') for c in report['checks']) else 'INCOMPLETE'
    report['write_permission'] = 'NOT_VERIFIED'
    return report


def save_probe(store, report):
    if report.get('probe_version') != PROBE_VERSION or report.get('exchange_mutations') != 0:
        raise ValueError('Geçersiz keşif raporu.')
    with store.db:
        store.db.execute('''CREATE TABLE IF NOT EXISTS capability_runs (
            run_id TEXT PRIMARY KEY, environment TEXT NOT NULL, product TEXT NOT NULL,
            symbol TEXT NOT NULL, credential_ref TEXT, observed_at_ms INTEGER NOT NULL, body TEXT NOT NULL)''')
        encoded = json.dumps(report,ensure_ascii=True)
        previous = store.db.execute('SELECT body FROM capability_runs WHERE run_id=?',(report['run_id'],)).fetchone()
        if previous:
            if previous['body'] != encoded:
                raise ValueError('Aynı keşif kimliği farklı raporla değiştirilemez.')
            return False
        store.db.execute('INSERT INTO capability_runs VALUES (?,?,?,?,?,?,?)',
                         (report['run_id'], 'demo', 'USD-M', report['symbol'], report['credential_ref'],
                          report['finished_at_ms'], encoded))
    return True


def latest_probe(store, symbol, credential_ref=None, max_age_seconds=300, now_ms=None):
    """Read only matching account evidence; old/other-key observations grant nothing."""
    if not re.fullmatch(r'[A-Z0-9]{2,20}USDT',symbol):
        raise ValueError('Geçersiz sembol.')
    if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 3600:
        raise ValueError('Kanıt geçerliliği 1–3600 saniye olmalı.')
    try:
        row = store.db.execute('''SELECT body FROM capability_runs
            WHERE environment='demo' AND product='USD-M' AND symbol=? AND credential_ref IS ?
            ORDER BY observed_at_ms DESC, rowid DESC LIMIT 1''',(symbol,credential_ref)).fetchone()
    except sqlite3.OperationalError as exc:
        if 'no such table' not in str(exc): raise
        row = None
    if row is None:
        return {'evidence_status':'NOT_FOUND','symbol':symbol,'write_permission':'NOT_VERIFIED'}
    report = json.loads(row['body'])
    age = ((int(time.time()*1000) if now_ms is None else now_ms)-report['finished_at_ms'])/1000
    return {'evidence_status':'FRESH' if 0 <= age <= max_age_seconds else 'STALE',
            'age_seconds':round(age,3),'write_permission':'NOT_VERIFIED','report':report}
