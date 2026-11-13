"""Demo arithmetic LONG grid planner and durable fill-driven cycle ledger.

Budget means total nominal across every inventory slot, never margin times leverage.
No order is submitted by the planner or ledger.
"""
import json
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING

from .plans import positive, digest


def arithmetic_levels(lower, upper, intervals):
    lower, upper = positive(str(lower), 'Alt fiyat'), positive(str(upper), 'Üst fiyat')
    if type(intervals) is not int or not 2 <= intervals <= 100 or lower >= upper:
        raise ValueError('Grid sayısı 2–100 ve alt fiyat üst fiyattan küçük olmalı.')
    spacing = (upper - lower) / intervals
    return [lower + spacing * i for i in range(intervals + 1)]


def preview_grid(spec, symbol, limits):
    required = {'environment', 'symbol', 'direction', 'entry', 'lower', 'upper',
                'intervals', 'spacing', 'leverage', 'budget_kind', 'budget', 'stop'}
    if set(spec) != required:
        raise ValueError('Grid planı alanları eksik veya desteklenmiyor.')
    if (spec['environment'], spec['direction'], spec['spacing'], spec['budget_kind']) != (
            'demo', 'LONG', 'ARITHMETIC', 'NOTIONAL'):
        raise ValueError('Yalnız demo LONG aritmetik grid ve toplam nominal bütçe desteklenir.')
    if type(spec['leverage']) is not int or not 1 <= spec['leverage'] <= 125:
        raise ValueError('Kaldıraç 1–125 arasında tam sayı olmalı.')
    if symbol['symbol'] != spec['symbol'] or symbol['status'] != 'TRADING' or symbol['quoteAsset'] != 'USDT':
        raise ValueError('İşleme açık USDT sözleşmesi gerekli.')
    filters = {f['filterType']: f for f in symbol['filters']}
    pf, lot = filters['PRICE_FILTER'], filters['LOT_SIZE']
    tick, step = Decimal(pf['tickSize']), Decimal(lot['stepSize'])
    entry, stop, budget = (positive(str(spec[k]), k) for k in ('entry', 'stop', 'budget'))
    levels = arithmetic_levels(spec['lower'], spec['upper'], spec['intervals'])
    if not (levels[0] <= entry < levels[-1] and stop < entry):
        raise ValueError('LONG için alt sınır <= giriş < üst sınır ve stop < giriş gerekli.')
    for price in [entry, stop, *levels]:
        if price % tick or not Decimal(pf['minPrice']) <= price <= Decimal(pf['maxPrice']):
            raise ValueError('Grid/giriş/stop fiyatı borsanın fiyat adımına uymuyor.')
    minimum = Decimal(filters['MIN_NOTIONAL']['notional'])
    # Reserve a full cycle purchase at every lower boundary, including refills.
    cost_per_unit = sum(levels[:-1])
    # Conservatively cap marked exposure even if every slot were held at the upper band.
    exposure_per_unit = levels[-1] * spec['intervals']
    quantity = (budget / exposure_per_unit / step).to_integral_value(rounding=ROUND_FLOOR) * step
    min_quantity = max(Decimal(lot['minQty']), minimum / levels[0])
    min_quantity = (min_quantity / step).to_integral_value(rounding=ROUND_CEILING) * step
    minimum_budget = min_quantity * exposure_per_unit
    cells = [{'index': i, 'buy_price': str(lo), 'sell_price': str(hi),
              'quantity': str(quantity), 'initial_inventory': lo >= entry}
             for i, (lo, hi) in enumerate(zip(levels, levels[1:]))]
    reasons = []
    if stop >= levels[0]:
        reasons.append({'code': 'STOP_INSIDE_GRID_REQUIRES_CANCEL',
                        'message': 'Stop bandın içinde. Stop sonrası alt grid alışlarının terminal iptali doğrulanmadan yürütme etkinleşemez.',
                        'buy_levels_at_or_below_stop': [str(p) for p in levels[:-1] if p <= stop]})
    if quantity < min_quantity:
        reasons.append({'code': 'MINIMUM_GRID_ORDER', 'message': 'Grid alışları minimum nominali karşılamıyor.',
                        'minimum_order_notional': str(minimum),
                        'minimum_budget_equal_btc_slots': str(minimum_budget)})
    if quantity <= 0 or quantity > Decimal(lot['maxQty']):
        reasons.append({'code': 'LOT_SIZE', 'message': 'Grid miktarı lot sınırları dışında.'})
    reserved = quantity * cost_per_unit
    worst_loss = quantity * sum(max(entry, p) - stop for p in levels[:-1])
    if budget > limits.max_notional:
        reasons.append({'code': 'NOMINAL_RISK_LIMIT', 'message': 'Bağımsız nominal üst sınırı aşılıyor.',
                        'limit': str(limits.max_notional)})
    if worst_loss > min(limits.max_trade_loss, limits.max_total_loss, limits.max_daily_loss):
        reasons.append({'code': 'STOP_RISK_LIMIT', 'message': 'Grid toplam stop riski bağımsız sınırları aşıyor.',
                        'estimated_loss_excluding_costs': str(worst_loss)})
    return {'state': 'BLOCKED' if reasons else 'VALIDATED_OFFLINE', 'spec': spec,
            'digest': digest(spec), 'levels': [str(p) for p in levels],
            'price_spacing': str(levels[1] - levels[0]), 'cells': cells,
            'grid_quantity': str(quantity), 'reserved_notional': str(reserved),
            'maximum_marked_notional_in_band': str(quantity * exposure_per_unit),
            'seed_quantity': str(quantity * sum(c['initial_inventory'] for c in cells)),
            'initial_margin_estimate': str(reserved / spec['leverage']),
            'worst_stop_loss_excluding_costs': str(worst_loss),
            'minimum_budget_equal_btc_slots': str(minimum_budget), 'reasons': reasons, 'executed': False}


def verify_leverage(exchange, symbol, leverage, *, apply=False):
    """Explicit flat-account leverage setting, followed by GET verification.

    Caller must hold execution_lock and have authorized this setting if apply=True.
    No retry after a timeout, no change of margin mode, no order submission.
    """
    if type(leverage) is not int or not 1 <= leverage <= 125:
        raise ValueError('Geçersiz kaldıraç.')
    brackets = exchange.get('/fapi/v1/leverageBracket', {'symbol': symbol})
    selected = next((r for r in brackets if r['symbol'] == symbol), None)
    if not selected or max(b['initialLeverage'] for b in selected['brackets']) < leverage:
        raise ValueError('Kaldıraç bu sözleşmede desteklenmiyor.')
    if apply:
        if (any(Decimal(p['positionAmt']) for p in exchange.get('/fapi/v3/positionRisk'))
                or exchange.get('/fapi/v1/openOrders') or exchange.get('/fapi/v1/openAlgoOrders')):
            raise ValueError('Kaldıraç ayarlamak için hesap boş ve emirsiz olmalı.')
        exchange.request('POST', '/fapi/v1/leverage', {'symbol': symbol, 'leverage': leverage})
    actual = next((r for r in exchange.get('/fapi/v1/symbolConfig', {'symbol': symbol}) if r['symbol'] == symbol), None)
    if actual is None or (apply and int(actual['leverage']) != leverage):
        raise ValueError('Borsa kaldıraç yapılandırmasını doğrulamadı.')
    return {'requested': leverage, 'actual': int(actual['leverage']), 'margin_type': actual['marginType'],
            'changed': apply, 'brackets': selected['brackets']}


class GridLedger:
    """Persistent cycle proposals; only exact confirmed FILLED orders advance state."""
    def __init__(self, store, session_id, preview=None):
        self.store, self.session_id = store, session_id
        store.db.execute('CREATE TABLE IF NOT EXISTS grid_ledgers (session_id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        row = store.db.execute('SELECT body FROM grid_ledgers WHERE session_id=?', (session_id,)).fetchone()
        if row:
            self.body = json.loads(row[0])
            if digest(self.body['spec']) != self.body['digest']:
                raise ValueError('Grid içeriği ile kayıt özeti uyuşmuyor.')
            if preview and self.body['digest'] != preview['digest']:
                raise ValueError('Kayıtlı grid planı değiştirilemez.')
        elif preview and preview['state'] == 'VALIDATED_OFFLINE':
            self.body = {'digest': preview['digest'], 'state': 'WAITING_SEED', 'spec': preview['spec'],
                         'seed_quantity': preview['seed_quantity'],
                         'cells': [dict(c, phase='WAITING_SEED' if c['initial_inventory'] else 'BUY', cycle=0)
                                   for c in preview['cells']], 'fills': {}}
            self.save()
        else:
            raise ValueError('Geçerli grid önizlemesi veya kayıtlı oturum gerekli.')

    def save(self):
        with self.store.db:
            self.store.db.execute('INSERT OR REPLACE INTO grid_ledgers VALUES (?,?)',
                                  (self.session_id, json.dumps(self.body)))

    def action(self, index=None):
        if self.body['state'] in ('STOPPING', 'CLOSED'):
            raise ValueError('Durdurulan grid yeni döngü üretemez.')
        if index is None:
            if self.body['state'] != 'WAITING_SEED':
                raise ValueError('Başlangıç girişi zaten tamamlandı.')
            phase, cycle = 'SEED', 0
            price, quantity = self.body['spec']['entry'], self.body['seed_quantity']
        else:
            if type(index) is not int or not 0 <= index < len(self.body['cells']):
                raise ValueError('Geçersiz grid hücresi.')
            cell = self.body['cells'][index]
            phase, cycle = cell['phase'], cell['cycle']
            if phase not in ('BUY', 'SELL'):
                raise ValueError('Hücre başlangıç gerçekleşmesini bekliyor.')
            price = cell['buy_price' if phase == 'BUY' else 'sell_price']
            quantity = cell['quantity']
        cid = 'agt-g-' + digest([self.session_id, index, phase, cycle])[:26]
        return {'symbol': self.body['spec']['symbol'], 'side': 'SELL' if phase == 'SELL' else 'BUY',
                'positionSide': 'BOTH', 'type': 'LIMIT', 'timeInForce': 'GTC',
                'price': price, 'quantity': quantity, 'reduceOnly': 'true' if phase == 'SELL' else 'false',
                'newClientOrderId': cid}

    def filled(self, index, response):
        cid = response.get('clientOrderId')
        if cid in self.body['fills']:
            if self.body['fills'][cid] != response:
                raise ValueError('Aynı gerçekleşme kimliği farklı içerikle geldi.')
            return False
        expected = self.action(index)
        if (cid != expected['newClientOrderId'] or response.get('symbol') != expected['symbol']
                or response.get('side') != expected['side'] or response.get('status') != 'FILLED'
                or Decimal(response.get('executedQty', '0')) != Decimal(expected['quantity'])):
            raise ValueError('Grid eylemi eşleşen tam gerçekleşme bekliyor.')
        self.body['fills'][cid] = response
        if index is None:
            self.body['state'] = 'ACTIVE'
            for cell in self.body['cells']:
                if cell['phase'] == 'WAITING_SEED': cell['phase'] = 'SELL'
        else:
            cell = self.body['cells'][index]
            if cell['phase'] == 'SELL': cell.update(phase='BUY', cycle=cell['cycle'] + 1)
            else: cell['phase'] = 'SELL'
        self.save()
        return True

    def stop(self):
        self.body['state'] = 'STOPPING'
        self.save()

    def observe_mark(self, mark_price):
        price = positive(str(mark_price), 'Mark fiyatı')
        if price <= Decimal(self.body['spec']['stop']):
            self.stop()
            return 'STOPPING'
        return self.body['state']
