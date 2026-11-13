"""Sürümlü demo planları ve tek kullanımlık, kapsamı belirli yerel yetkilendirme."""
import hashlib
import hmac
import json
import re
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

FINAL = {'REJECTED', 'CANCELED', 'EXPIRED', 'SUPERSEDED', 'CLOSED'}
PENDING = {'PENDING_APPROVAL', 'PENDING_ACTIVATION'}
BUSY = {'EXECUTING', 'MANAGING', 'NEEDS_REVIEW'}


def exact_fields(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError(label + ': eksik veya desteklenmeyen alan.')


def positive(value, label):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError(label + ' ondalık metin olmalı.')
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError(label + ' geçerli sayı olmalı.') from None
    if not number.is_finite() or number <= 0:
        raise ValueError(label + ' pozitif ve sonlu olmalı.')
    if not -18 <= number.adjusted() <= 18:
        raise ValueError(label + ' desteklenen sayısal aralık dışında.')
    return number


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Zaman ISO-8601 metni olmalı.')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError()
        return date.timestamp()
    except (ValueError, OverflowError):
        raise ValueError('Zaman saat dilimi içeren ISO-8601 olmalı.') from None


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError('Plan nesne olmalı.')
    if plan.get('schema_version') == 2:
        from .plan_v2 import validate_v2
        return validate_v2(plan)
    exact_fields({k: v for k, v in plan.items() if k != 'market_guard'}, 'schema_version plan_id version environment exchange product symbol position_mode direction mode created_at expires_at entry sizing stop targets management max_runs analysis_ref rationale', 'Plan')
    if 'market_guard' in plan:
        guard = plan['market_guard']
        exact_fields(guard, 'source max_divergence_bps max_age_seconds', 'Piyasa farkı kontrolü')
        if guard['source'] != 'binance_usdm_live_mark' or positive(guard['max_divergence_bps'], 'Demo/canlı farkı') > 100:
            raise ValueError('Piyasa karşılaştırması canlı Binance mark ve en fazla %1 fark destekler.')
        if type(guard['max_age_seconds']) is not int or not 1 <= guard['max_age_seconds'] <= 30:
            raise ValueError('Piyasa karşılaştırması veri yaşı 1–30 saniye olmalı.')
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise ValueError('Desteklenmeyen plan şema sürümü.')
    if not isinstance(plan['plan_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', plan['plan_id']):
        raise ValueError('Geçersiz plan kimliği.')
    if type(plan['version']) is not int or plan['version'] < 1:
        raise ValueError('Plan sürümü pozitif tam sayı olmalı.')
    if (plan['environment'], plan['exchange'], plan['product'], plan['position_mode'], plan['direction']) != ('demo', 'binance', 'USD-M', 'one-way', 'LONG'):
        raise ValueError('İlk plan adaptörü yalnızca Binance demo USD-M one-way LONG destekler.')
    if not isinstance(plan['symbol'], str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', plan['symbol']):
        raise ValueError('Geçerli USDT sözleşme sembolü gerekli.')
    if plan['mode'] not in ('A', 'B'):
        raise ValueError('Yetki modu A veya B olmalı.')
    created, expires = timestamp(plan['created_at']), timestamp(plan['expires_at'])
    if expires <= created or expires - created > 5 * 86400:
        raise ValueError('Plan geçerliliği pozitif ve en fazla 5 gün olmalı.')
    exact_fields(plan['entry'], 'condition reference_price trigger_price max_drift_bps', 'Giriş')
    entry = plan['entry']
    if entry['condition'] not in ('IMMEDIATE', 'MARK_AT_OR_BELOW', 'MARK_AT_OR_ABOVE'):
        raise ValueError('Desteklenmeyen giriş koşulu.')
    ref = positive(entry['reference_price'], 'Referans fiyat')
    if entry['condition'] == 'IMMEDIATE':
        if entry['trigger_price'] is not None:
            raise ValueError('Anlık girişte tetik fiyatı boş olmalı.')
    else:
        positive(entry['trigger_price'], 'Tetik fiyatı')
    drift = positive(entry['max_drift_bps'], 'Fiyat toleransı')
    if drift > 100:
        raise ValueError('İlk demo planında tolerans en fazla 100 baz puan (%1).')
    exact_fields(plan['sizing'], 'kind amount currency', 'Tutar')
    if plan['sizing']['kind'] not in ('NOTIONAL', 'MAX_LOSS') or plan['sizing']['currency'] != 'USDT':
        raise ValueError('Tutar NOTIONAL veya MAX_LOSS / USDT olmalı; teminat tipi henüz desteklenmiyor.')
    positive(plan['sizing']['amount'], 'Tutar')
    stop = positive(plan['stop'], 'Stop')
    if not isinstance(plan['targets'], list) or not 1 <= len(plan['targets']) <= 8:
        raise ValueError('1–8 hedef gerekli.')
    total = Decimal(0)
    previous = ref
    for target in plan['targets']:
        exact_fields(target, 'price fraction', 'Hedef')
        price = positive(target['price'], 'Hedef fiyatı')
        total += positive(target['fraction'], 'Çıkış payı')
        if price <= previous:
            raise ValueError('LONG hedefleri girişin üzerinde ve sıralı olmalı.')
        previous = price
    if total != 1 or stop >= ref:
        raise ValueError('Hedef payları toplamı 1 ve stop giriş altında olmalı.')
    if entry['trigger_price'] is not None and not stop < Decimal(entry['trigger_price']) < Decimal(plan['targets'][0]['price']):
        raise ValueError('Tetik fiyatı stop ile ilk hedef arasında olmalı.')
    exact_fields(plan['management'], 'break_even_after_target allow_scale_in allow_reverse allow_reentry', 'Yönetim')
    if any(type(plan['management'][k]) is not bool for k in ('allow_scale_in', 'allow_reverse', 'allow_reentry')):
        raise ValueError('Yönetim izinleri boolean olmalı.')
    break_even = plan['management']['break_even_after_target']
    if break_even is not None and (type(break_even) is not int or not 1 <= break_even < len(plan['targets'])):
        raise ValueError('Girişe stop taşıma hedefi, son hedeften önceki geçerli bir hedef numarası olmalı.')
    if (any(plan['management'][k] for k in ('allow_scale_in', 'allow_reverse', 'allow_reentry'))
            or type(plan['max_runs']) is not int or plan['max_runs'] != 1):
        raise ValueError('Adaptör tek giriş destekler; artırma, ters yön ve yeniden giriş henüz desteklenmiyor.')
    for field in ('analysis_ref', 'rationale'):
        if not isinstance(plan[field], str) or not 1 <= len(plan[field]) <= 2000:
            raise ValueError(field + ' boş olmayan metin olmalı.')
    return plan


@contextmanager
def transaction(store):
    store.db.execute('BEGIN IMMEDIATE')
    try:
        yield store.db
        store.db.commit()
    except BaseException:
        store.db.rollback()
        raise


class PlanService:
    def __init__(self, store, owner):
        if not owner or not isinstance(owner, str):
            raise ValueError('Yetkili kullanıcı kimliği gerekli.')
        self.store, self.owner = store, owner
        with transaction(store) as db:
            row = db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
            if row and row['value'] != owner:
                raise ValueError('Plan deposu başka bir yetkili kullanıcıya bağlı.')
            db.execute("INSERT OR IGNORE INTO control VALUES ('plan_owner',?)", (owner,))

    def actor(self, actor):
        if actor != self.owner:
            raise ValueError('Yetkisiz kullanıcı.')

    def event(self, db, event, payload):
        db.execute('INSERT INTO events(event,payload) VALUES (?,?)', (event, canonical(payload)))

    def row(self, db, plan_id, version):
        row = db.execute('SELECT * FROM plan_versions WHERE plan_id=? AND version=?', (plan_id, version)).fetchone()
        if not row:
            raise ValueError('Plan/sürüm bulunamadı.')
        result = dict(row)
        body = validate_plan(json.loads(result['body']))
        if digest(body) != result['digest']:
            raise ValueError('Plan içeriği ile kayıt özeti uyuşmuyor.')
        result['plan'] = body
        return result

    def expire(self, db, now):
        for record in db.execute('SELECT plan_id,version FROM plan_versions WHERE state IN (?,?,?)',
                                 ('PENDING_APPROVAL', 'PENDING_ACTIVATION', 'AUTHORIZED')).fetchall():
            row = self.row(db, record['plan_id'], record['version'])
            if timestamp(row['plan']['expires_at']) <= now or (row['state'] == 'AUTHORIZED' and row['approval_until'] <= now):
                db.execute("UPDATE plan_versions SET state='EXPIRED' WHERE plan_id=? AND version=?", (row['plan_id'], row['version']))
                db.execute('DELETE FROM plan_slots WHERE plan_id=? AND version=?', (row['plan_id'], row['version']))

    def sync(self, db):
        # Watchdog CLOSED kaydı yalnızca borsada sıfır pozisyon doğrulandıktan sonra oluşur.
        for record in db.execute('SELECT plan_id,version,session_id FROM plan_versions WHERE state IN (?,?,?)', tuple(BUSY)).fetchall():
            if not record['session_id']:
                continue
            session = db.execute('SELECT body,active FROM managed_sessions WHERE session_id=?', (record['session_id'],)).fetchone()
            if session:
                body = json.loads(session['body'])
                state = ('CLOSED' if not session['active'] and body['status'] == 'CLOSED'
                         else 'MANAGING' if body['status'] == 'PROTECTED'
                         else self.row(db, record['plan_id'], record['version'])['state'])
                db.execute('UPDATE plan_versions SET state=? WHERE plan_id=? AND version=?', (state, record['plan_id'], record['version']))
                if state == 'CLOSED':
                    db.execute('DELETE FROM plan_slots WHERE plan_id=? AND version=?', (record['plan_id'], record['version']))
                    db.execute("UPDATE plan_actions SET state='CLOSED' WHERE plan_id=? AND version=?", (record['plan_id'], record['version']))

    def create(self, plan, actor, now=None):
        self.actor(actor)
        now = time.time() if now is None else now
        validate_plan(plan)
        if not timestamp(plan['created_at']) <= now < timestamp(plan['expires_at']):
            raise ValueError('Plan zamanı geçersiz veya süresi dolmuş.')
        token = secrets.token_urlsafe(24)
        state = 'PENDING_APPROVAL' if plan['mode'] == 'A' else 'PENDING_ACTIVATION'
        with transaction(self.store) as db:
            self.sync(db)
            self.expire(db, now)
            old = db.execute('SELECT version,state FROM plan_versions WHERE plan_id=? ORDER BY version DESC LIMIT 1', (plan['plan_id'],)).fetchone()
            expected = old['version'] + 1 if old else 1
            if plan['version'] != expected:
                raise ValueError('Yeni plan sürümü sıralı olmalı: ' + str(expected))
            if old and old['state'] in BUSY:
                raise ValueError('Yürütülen/açık pozisyon planı yerinde değiştirilemez.')
            if old:
                db.execute("UPDATE plan_versions SET state='SUPERSEDED' WHERE plan_id=? AND state NOT IN ('CLOSED','CANCELED','REJECTED','EXPIRED')", (plan['plan_id'],))
                db.execute('DELETE FROM plan_slots WHERE plan_id=?', (plan['plan_id'],))
            db.execute('INSERT INTO plan_versions(plan_id,version,body,digest,state,owner,token_hash) VALUES (?,?,?,?,?,?,?)',
                       (plan['plan_id'], plan['version'], canonical(plan), digest(plan), state, self.owner, hashlib.sha256(token.encode()).hexdigest()))
            self.event(db, 'plan_created', {'plan_id': plan['plan_id'], 'version': plan['version'], 'digest': digest(plan)})
        return {'state': state, 'plan': plan, 'digest': digest(plan), 'authorization_token': token,
                'warning': 'Bu kayıt emir göndermez; belirli sürüm için ayrıca approve/activate gerekir.'}

    def show(self, plan_id, version, now=None):
        now = time.time() if now is None else now
        with transaction(self.store) as db:
            self.sync(db)
            self.expire(db, now)
            row = self.row(db, plan_id, version)
        return {k: v for k, v in row.items() if k not in ('body', 'token_hash')}

    def authorize(self, plan_id, version, token, action, actor, ttl=120, now=None):
        self.actor(actor)
        now = time.time() if now is None else now
        if type(ttl) is not int or not 1 <= ttl <= 86400:
            raise ValueError('Onay süresi 1–86400 saniye olmalı.')
        # Süre sonu kayıtlarını hatalı onay girişiminde de kalıcılaştır.
        self.show(plan_id, version, now)
        with transaction(self.store) as db:
            row = self.row(db, plan_id, version)
            if not isinstance(token, str) or not hmac.compare_digest(row['token_hash'], hashlib.sha256(token.encode()).hexdigest()):
                raise ValueError('Onay kimliği geçersiz.')
            expected = 'approve' if row['plan']['mode'] == 'A' else 'activate'
            if action != expected:
                raise ValueError('Onay eylemi planın yetki moduyla uyuşmuyor.')
            if row['state'] == 'AUTHORIZED':
                return {'state': 'AUTHORIZED', 'duplicate': True, 'approval_until': row['approval_until']}
            if row['state'] not in PENDING:
                raise ValueError('Plan bu durumda yetkilendirilemez: ' + row['state'])
            conflict = db.execute('SELECT * FROM plan_slots WHERE symbol=?', (row['plan']['symbol'],)).fetchone()
            if conflict:
                raise ValueError('Aynı sembolde başka etkin/onaylı plan var.')
            sessions=self.store.sessions()
            if sessions and (row['plan']['schema_version']!=2 or any(
                    s.get('engine') not in ('v2','grid-v2','neutral-v2') or s['symbol']==row['plan']['symbol'] or
                    s['plan']['position_mode']!=row['plan']['position_mode'] for s in sessions)):
                raise ValueError('Etkin oturumlarla uyumlu, farklı sembollü v2 planı gerekli.')
            until = min(timestamp(row['plan']['expires_at']), now + ttl) if action == 'approve' else timestamp(row['plan']['expires_at'])
            db.execute("UPDATE plan_versions SET state='AUTHORIZED',authorized_by=?,authorized_at=?,approval_until=? WHERE plan_id=? AND version=?",
                       (actor, now, until, plan_id, version))
            db.execute('INSERT INTO plan_slots VALUES (?,?,?)', (row['plan']['symbol'], plan_id, version))
            self.event(db, 'plan_authorized', {'plan_id': plan_id, 'version': version, 'mode': row['plan']['mode'], 'until': until, 'actor': actor})
        return {'state': 'AUTHORIZED', 'duplicate': False, 'approval_until': until}

    def cancel(self, plan_id, version, actor, reject=False):
        self.actor(actor)
        with transaction(self.store) as db:
            self.sync(db)
            row = self.row(db, plan_id, version)
            if row['state'] in BUSY:
                intent = db.execute('SELECT 1 FROM intents WHERE client_id=?', (row['action_id'],)).fetchone()
                session = db.execute('SELECT 1 FROM managed_sessions WHERE session_id=?', (row['session_id'],)).fetchone()
                if not intent and not session:
                    db.execute("UPDATE plan_versions SET state='CANCELED' WHERE plan_id=? AND version=?", (plan_id, version))
                    db.execute('DELETE FROM plan_slots WHERE plan_id=? AND version=?', (plan_id, version))
                    db.execute("UPDATE plan_actions SET state='CANCELED' WHERE plan_id=? AND version=?", (plan_id, version))
                    self.event(db, 'unsubmitted_plan_canceled', {'plan_id': plan_id, 'version': version})
                    return {'state': 'CANCELED', 'submitted': False}
                # Yetki zaten tek giriş içindi. Açık pozisyonu ve korumasını değiştirme.
                db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',
                           ('entry_revoked:'+row['action_id'], 'true'))
                self.event(db, 'plan_entry_revoked', {'plan_id': plan_id, 'version': version})
                return {'state': row['state'], 'entry_revoked': True, 'message': 'Yeni giriş yok; mevcut koruma sürer. Kapatma ayrı komuttur.'}
            if row['state'] in FINAL:
                return {'state': row['state'], 'duplicate': True}
            state = 'REJECTED' if reject else 'CANCELED'
            db.execute('UPDATE plan_versions SET state=? WHERE plan_id=? AND version=?', (state, plan_id, version))
            db.execute('DELETE FROM plan_slots WHERE plan_id=? AND version=?', (plan_id, version))
            self.event(db, 'plan_' + state.lower(), {'plan_id': plan_id, 'version': version})
        return {'state': state}

    def claim(self, plan_id, version, session_id, now=None):
        now = time.time() if now is None else now
        self.show(plan_id, version, now)
        with transaction(self.store) as db:
            row = self.row(db, plan_id, version)
            if row['state'] != 'AUTHORIZED' or row['approval_until'] <= now:
                raise ValueError('Yeni giriş için geçerli yetki yok: ' + row['state'])
            slot = db.execute('SELECT * FROM plan_slots WHERE symbol=?', (row['plan']['symbol'],)).fetchone()
            if not slot or (slot['plan_id'], slot['version']) != (plan_id, version):
                raise ValueError('Planın sembol rezervasyonu yok.')
            action_id = 'agt-' + hashlib.sha256(f'{plan_id}:{version}:entry'.encode()).hexdigest()[:28]
            db.execute('INSERT INTO plan_actions VALUES (?,?,?,?,?)', (action_id, plan_id, version, 'ENTRY', 'CLAIMED'))
            db.execute("UPDATE plan_versions SET state='EXECUTING',action_id=?,session_id=? WHERE plan_id=? AND version=?", (action_id, session_id, plan_id, version))
            self.event(db, 'plan_entry_claimed', {'plan_id': plan_id, 'version': version, 'action_id': action_id, 'session_id': session_id})
        return action_id

    def outcome(self, plan_id, version, state):
        if state not in ('MANAGING', 'NEEDS_REVIEW'):
            raise ValueError('Geçersiz yürütme sonucu.')
        with transaction(self.store) as db:
            row = self.row(db, plan_id, version)
            if row['state'] in FINAL:
                return
            db.execute('UPDATE plan_versions SET state=? WHERE plan_id=? AND version=?', (state, plan_id, version))
            db.execute('UPDATE plan_actions SET state=? WHERE action_id=?', (state, row['action_id']))


def example_plan(staged=False):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    plan = {'schema_version': 1, 'plan_id': 'demo-example', 'version': 1,
            'environment': 'demo', 'exchange': 'binance', 'product': 'USD-M', 'symbol': 'BTCUSDT',
            'position_mode': 'one-way', 'direction': 'LONG', 'mode': 'A',
            'created_at': (now - timedelta(seconds=1)).isoformat(), 'expires_at': (now + timedelta(hours=1)).isoformat(),
            'entry': {'condition': 'MARK_AT_OR_BELOW', 'reference_price': '80000', 'trigger_price': '80000', 'max_drift_bps': '50'},
            'sizing': {'kind': 'NOTIONAL', 'amount': '60', 'currency': 'USDT'},
            'stop': '78400', 'targets': [{'price': '81600', 'fraction': '1'}],
            'management': {'break_even_after_target': None, 'allow_scale_in': False, 'allow_reverse': False, 'allow_reentry': False},
            'max_runs': 1, 'analysis_ref': 'manual-demo-test',
            'rationale': 'Örnek seviyelerdir; güncel analiz veya işlem tavsiyesi değildir.'}
    if staged:
        plan['plan_id'] = 'demo-staged-example'
        plan['sizing']['amount'] = '64'
        plan['targets'] = [{'price': '81000', 'fraction': '.5'}, {'price': '82000', 'fraction': '.5'}]
        plan['management']['break_even_after_target'] = 1
    return plan
