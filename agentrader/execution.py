"""Demo isteklerini kalıcılaştırır; belirsiz gönderimi asla tekrar etmez."""
from .history import income_history
import json
import time
from datetime import datetime, timezone
from decimal import Decimal

from .exchange import ExchangeError
from .risk import evaluate, RiskLimits

TERMINAL = {'FILLED', 'CANCELED', 'EXPIRED', 'EXPIRED_IN_MATCH', 'REJECTED', 'FINISHED', 'RESOLVED_FLAT'}


def resolve_absent_flat(exchange, store, row, error):
    """Resolve a missing algo only with verified flat account and no open orders.

    This does not assert that the historical POST was rejected and never permits
    resubmission. A missing order while a position is open remains UNKNOWN.
    """
    if (error.code != -2013 or row['path'] != '/fapi/v1/algoOrder'
            or row['state'] != 'UNKNOWN'):
        raise error
    if (any(Decimal(p['positionAmt']) != 0 for p in exchange.get('/fapi/v3/positionRisk'))
            or exchange.get('/fapi/v1/openOrders') or exchange.get('/fapi/v1/openAlgoOrders')):
        raise error
    result = {'algoStatus': 'EXPIRED', 'resolution': 'RESOLVED_FLAT',
              'clientAlgoId': row['client_id'], 'lookup_code': error.code,
              'reason': 'Missing algo; account flat and no open orders. Never resubmit.'}
    store.update(row['client_id'], 'RESOLVED_FLAT', result)
    store.event('unknown_algo_resolved_flat', result)
    return result


class DurableExchange:
    def __init__(self, exchange, store, limits=RiskLimits(), test_only=False):
        self.x, self.store = exchange, store
        self.entry_risk = None
        self.limits = limits
        self.entry_guard = None
        self.test_only = test_only

    def sync_time(self):
        return self.x.sync_time()

    def get(self, path, params=None):
        return self.x.get(path, params)

    def configure_entry(self, entry, stop):
        self.entry_risk = (entry, stop)

    def lookup(self, path, params):
        if path.endswith('algoOrder'):
            return {'clientAlgoId': params['clientAlgoId']}
        return {'symbol': params['symbol'], 'origClientOrderId': params['newClientOrderId']}

    def check_entry(self, params):
        if self.store.db.execute('SELECT 1 FROM control WHERE name=?',
                                 ('entry_revoked:'+params.get('newClientOrderId', ''),)).fetchone():
            raise ValueError('Bu girişin plan yetkisi iptal edildi.')
        if self.store.unresolved_account_command():
            raise ValueError('Belirsiz hesap ayarı uzlaştırılmadan yeni giriş açılamaz.')
        if (self.store.db.execute("SELECT 1 FROM control WHERE name='plan_owner'").fetchone()
                and self.entry_guard is None and not self.test_only):
            raise ValueError('Yeni giriş için plan yetki denetimi gerekli; deneyler yalnızca açık test-only modunda çalışır.')
        reason = self.store.halt_reason()
        if reason:
            raise ValueError('Yeni girişler durduruldu: ' + reason)
        if self.entry_risk is None:
            raise ValueError('Giriş için bağımsız risk verisi eksik.')
        account = self.get('/fapi/v3/account')
        positions = sum(Decimal(p['positionAmt']) != 0 for p in account['positions'])
        # Bilinmeyen pozisyon/emir riskini sıfır varsaymak yerine reddet.
        if positions or self.get('/fapi/v1/openOrders') or self.get('/fapi/v1/openAlgoOrders'):
            raise ValueError('Mevcut pozisyon/emir varken demo deneyi yeni giriş açamaz.')
        observed = time.time()
        mark = self.get('/fapi/v1/premiumIndex', {'symbol': params['symbol']})
        if self.get('/fapi/v1/positionSide/dual')['dualSidePosition']:
            raise ValueError('Hesap modu değişti; one-way gerekli.')
        entry, stop = self.entry_risk
        if params['side'] != 'BUY' or Decimal(stop) >= Decimal(entry):
            raise ValueError('Bu demo profili yalnızca stopu giriş altında LONG destekler.')
        # Piyasa emrinde güncel fiyatı kullan; fiyat kayması sonradan ayrıca izlenir.
        risk_entry = mark['markPrice'] if params['type'] == 'MARKET' else params['price']
        if Decimal(stop) >= Decimal(risk_entry):
            raise ValueError('Güncel giriş fiyatı stop seviyesinin altında veya eşit.')
        if 'time' in mark:
            age = (time.time() * 1000 + getattr(self.x, 'offset_ms', 0) - int(mark['time'])) / 1000
            if not -1 <= age <= self.limits.max_age_seconds:
                raise ValueError('Borsa fiyat zaman damgası eski veya geçersiz.')
        midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        incomes = income_history(self.x, int(midnight.timestamp() * 1000))
        pnl = sum((Decimal(row['income']) for row in incomes
                   if row['incomeType'] in ('REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE') and row['asset'] == 'USDT'), Decimal(0))
        if any(row['asset'] != 'USDT' and row['incomeType'] in ('REALIZED_PNL', 'COMMISSION', 'FUNDING_FEE') for row in incomes):
            raise ValueError('USDT dışı günlük sonuçlar dönüştürülmeden giriş açılamaz.')
        pnl += min(Decimal(account.get('totalUnrealizedProfit', '0')), Decimal(0))
        result = evaluate(risk_entry, stop, params['quantity'], account['availableBalance'], 0,
                          max(-pnl, Decimal(0)), positions, observed, self.limits)
        if self.entry_guard:
            self.entry_guard(params, mark)
        self._entry_mark = mark
        self.store.event('risk_accepted', result)

    def request(self, method, path, params=None):
        params = dict(params or {})
        if method != 'POST':
            result = self.x.request(method, path, params)
            self.store.event('request_completed', {'method': method, 'path': path, 'response': result})
            return result
        if path not in ('/fapi/v1/order', '/fapi/v1/algoOrder'):
            raise ValueError('Desteklenmeyen kalıcı emir türü.')
        cid = params.get('clientAlgoId') if path.endswith('algoOrder') else params.get('newClientOrderId')
        if not cid:
            raise ValueError('Kalıcı işlem için istemci kimliği zorunlu.')
        existing = next((r for r in self.store.intents() if r['client_id'] == cid), None)
        if existing:
            if existing['path'] != path or json.loads(existing['params']) != params:
                raise ValueError('Aynı kimlikle farklı emir parametresi reddedildi.')
            result = self.get(path, self.lookup(path, params))
            self.store.update(cid, result.get('status', result.get('algoStatus')), result)
            return result
        is_entry = path.endswith('/order') and params.get('reduceOnly') != 'true'
        if is_entry:
            self.check_entry(params)
        if not self.store.reserve(cid, path, params):
            raise ExchangeError('İşlem kimliği başka süreç tarafından ayrılmış; tekrar gönderilmedi.')
        if is_entry and self.entry_guard:
            try:
                # İzin ile kalıcı gönderim niyeti arasındaki iptal/sona erme yarışını kapat.
                self.entry_guard(params, self._entry_mark)
                if self.store.db.execute('SELECT 1 FROM control WHERE name=?',
                                         ('entry_revoked:'+cid,)).fetchone():
                    raise ValueError('Gönderim öncesi giriş yetkisi iptal edildi.')
            except ValueError:
                self.store.update(cid, 'REJECTED')
                raise
        try:
            result = self.x.request(method, path, params)
        except ExchangeError as exc:
            rejected = exc.delivery_status in ('NOT_SENT','REJECTED') or exc.code in {-1100, -1102, -1111, -2019, -2021, -2022, -4130, -4164, -4003, -4509}
            error = {'code': exc.code, 'http_status': exc.http_status, 'message': str(exc),
                     'delivery_status':exc.delivery_status,'retry_after':exc.retry_after}
            self.store.update(cid, 'REJECTED' if rejected else 'UNKNOWN', {'error': error})
            self.store.event('order_submission_failed', {'client_id': cid, 'path': path,
                                                       'state': 'REJECTED' if rejected else 'UNKNOWN', **error})
            self.store.halt('Emir kesin reddedildi veya gönderilmedi; kontrol gerekli.' if rejected
                            else 'Gönderim yanıtı belirsiz; recover gerekli.')
            raise
        self.store.update(cid, result.get('status', result.get('algoStatus', 'ACCEPTED')), result)
        return result


def reconcile(exchange, store, clear_halt=False):
    """Okuma ile uzlaştırır. Bilinmeyen pozisyonu kapatmaz veya emri tekrar göndermez."""
    exchange.sync_time()
    report = {'environment': 'demo', 'orders': [], 'issues': []}
    for row in store.intents():
        params = json.loads(row['params'])
        try:
            result = exchange.get(row['path'], DurableExchange(exchange, store).lookup(row['path'], params))
            status = result.get('status', result.get('algoStatus', 'UNKNOWN'))
            store.update(row['client_id'], status, result)
            report['orders'].append({'client_id': row['client_id'], 'status': status})
            if status not in TERMINAL:
                report['issues'].append('Sonlanmamış emir: ' + row['client_id'])
        except ExchangeError as exc:
            if row['state'] == 'UNKNOWN' and exc.code == -2013 and row['path'].endswith('algoOrder'):
                try:
                    resolve_absent_flat(exchange, store, row, exc)
                    report['orders'].append({'client_id': row['client_id'], 'status': 'RESOLVED_FLAT'})
                    continue
                except ExchangeError:
                    pass
            if row['state'] not in TERMINAL:
                store.update(row['client_id'], 'UNKNOWN')
                report['issues'].append('Sorgulanamayan emir: ' + row['client_id'])
    account = exchange.get('/fapi/v3/account')
    positions = [p for p in account['positions'] if Decimal(p['positionAmt']) != 0]
    normal = exchange.get('/fapi/v1/openOrders')
    algo = exchange.get('/fapi/v1/openAlgoOrders')
    report.update(position_count=len(positions), open_order_count=len(normal), open_algo_order_count=len(algo))
    if store.sessions():
        report['issues'].append('Aktif yönetilen oturum var; watchdog ile devralınmalı veya kapatılmalı.')
    if positions:
        report['issues'].append('Açık pozisyon var; korumayı kaldırmadan uzlaştırma gerekli.')
    if normal or algo:
        report['issues'].append('Borsada açık emir var; manuel/diğer bot emirleri dahil giriş durduruldu.')
    if report['issues']:
        store.halt('; '.join(report['issues']))
    elif clear_halt:
        store.clear_halt()
    report['halt_reason'] = store.halt_reason()
    report['ready'] = not report['issues'] and not report['halt_reason']
    store.event('reconciliation', report)
    return report
