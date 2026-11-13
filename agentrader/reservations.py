"""Account-bound durable risk envelopes. Fills never release a grid's refill budget."""
import json
import time
from dataclasses import asdict

from .plans import canonical, digest, transaction
from .portfolio import Exposure, evaluate_portfolio


class ReservationBook:
    def __init__(self, store, account_ref, clock=time.time):
        if not isinstance(account_ref, str) or not account_ref:
            raise ValueError('Teminat rezervi için hesap kimliği gerekli.')
        self.store, self.account_ref = store, account_ref
        self.clock = clock
        with store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS risk_reservations (
                reservation_id TEXT PRIMARY KEY, account_ref TEXT NOT NULL,
                body TEXT NOT NULL, digest TEXT NOT NULL, state TEXT NOT NULL)''')

    def reserve(self, reservation_id, owner, plan_digest, exposures, snapshot, limits):
        if not all(isinstance(v, str) and v for v in (reservation_id, owner, plan_digest)):
            raise ValueError('Rezervasyon kimliği, sahibi ve plan özeti gerekli.')
        body = {'owner': owner, 'plan_digest': plan_digest,
                'exposures': [asdict(e) for e in exposures]}
        empty=(snapshot.get('flat_verified') is True or
               (snapshot.get('target_flat_verified') is True and snapshot.get('ownership_verified') is True))
        if not body['exposures'] or not empty:
            raise ValueError('İlk risk rezervi için doğrulanmış boş hesap görünümü gerekli.')
        with transaction(self.store) as db:
            old = db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?', (reservation_id,)).fetchone()
            if old:
                if old['account_ref'] != self.account_ref or old['digest'] != digest(body):
                    raise ValueError('Rezervasyon kimliği başka kapsamla kullanılamaz.')
                if old['state'] == 'RELEASED':
                    raise ValueError('Serbest bırakılmış rezervasyon yeniden etkinleştirilemez.')
                return {'reservation_id': reservation_id, 'state': old['state'], 'duplicate': True}
            combined = list(exposures)
            keys={(e.symbol,e.direction)for e in exposures}
            for row in db.execute("SELECT * FROM risk_reservations WHERE account_ref=? AND state!='RELEASED'", (self.account_ref,)):
                saved = json.loads(row['body'])
                if digest(saved) != row['digest']:
                    raise ValueError('Kayıtlı risk rezervi özeti uyuşmuyor.')
                other=[Exposure(**leg)for leg in saved['exposures']]
                if keys&{(e.symbol,e.direction)for e in other}:
                    raise ValueError('Aynı pozisyonun tamamı tek risk zarfında ayrılmalı; basamaklar ayrı rezervlerle geçilemez.')
                combined.extend(other)
            risk = evaluate_portfolio(combined, snapshot['collateral'], snapshot['daily_loss'],
                                      snapshot['observed_at'], self.clock(), limits,
                                      collateral_valuation_verified=True)
            db.execute('INSERT INTO risk_reservations VALUES (?,?,?,?,?)',
                       (reservation_id, self.account_ref, canonical(body), digest(body), 'RESERVED'))
        return {'reservation_id': reservation_id, 'state': 'RESERVED', 'duplicate': False, 'risk': risk}

    def evaluate(self,snapshot,limits,*,exchange=None,extra_exposures=()):
        """Keep full envelopes until close; available collateral is not added back."""
        from dataclasses import replace
        from .brackets import select_bracket
        from .risk import number
        combined=list(extra_exposures)
        for row in self.store.db.execute("SELECT * FROM risk_reservations WHERE account_ref=? AND state!='RELEASED'",(self.account_ref,)):
            body=json.loads(row['body'])
            if digest(body)!=row['digest']:raise ValueError('Portföy risk rezervi özeti uyuşmuyor.')
            combined.extend(Exposure(**e) for e in body['exposures'])
        if not combined:raise ValueError('Hesap risk rezervi gerekli.')
        if exchange is not None:
            tiers={}
            for symbol in {e.symbol for e in combined}:
                rows=exchange.get('/fapi/v1/leverageBracket',{'symbol':symbol})
                rows=[rows] if isinstance(rows,dict) else rows
                rows=[r for r in rows if r.get('symbol')==symbol]
                if len(rows)!=1 or number(rows[0].get('notionalCoef',1))!=1:
                    raise ValueError('Ortak risk için güncel basamak kanıtı eksik.')
                legs=[e for e in combined if e.symbol==symbol]
                total=sum((number(e.quantity)*number(e.notional_price or e.entry) for e in legs),number(0))
                tiers[symbol]=select_bracket(rows[0]['brackets'],total,max(e.leverage for e in legs))
            combined=[replace(e,maintenance_ratio=str(tiers[e.symbol]['maintMarginRatio']),maintenance_deduction='0') for e in combined]
        return evaluate_portfolio(combined,snapshot['collateral'],snapshot['daily_loss'],
            snapshot['observed_at'],self.clock(),limits,collateral_valuation_verified=True)

    def state(self, reservation_id):
        row = self.store.db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?', (reservation_id,)).fetchone()
        if row is None or row['account_ref'] != self.account_ref:
            raise ValueError('Hesaba ait rezervasyon bulunamadı.')
        if digest(json.loads(row['body'])) != row['digest']:
            raise ValueError('Rezervasyon bütünlüğü doğrulanamadı.')
        return row['state']

    def assert_binding(self,reservation_id,owner,plan_digest,exposures):
        if self.state(reservation_id)=='RELEASED':raise ValueError('Etkin oturumun risk rezervi serbest bırakılamaz.')
        body={'owner':owner,'plan_digest':plan_digest,'exposures':exposures}
        row=self.store.db.execute('SELECT digest FROM risk_reservations WHERE reservation_id=?',(reservation_id,)).fetchone()
        if row['digest']!=digest(body):raise ValueError('Oturumun ortak risk rezervi plan içeriğiyle uyuşmuyor.')

    def list_reservations(self,owner):
        result=[]
        for row in self.store.db.execute('SELECT * FROM risk_reservations WHERE account_ref=? ORDER BY rowid',(self.account_ref,)):
            body=json.loads(row['body'])
            if digest(body)!=row['digest']:raise ValueError('Risk rezervi listesi bütünlüğü uyuşmuyor.')
            if body['owner']!=owner:continue
            result.append({'reservation_id':row['reservation_id'],'state':row['state'],
                           'plan_digest':body['plan_digest'],'exposures':body['exposures'],
                           'has_session':self.store.db.execute('SELECT 1 FROM managed_sessions WHERE session_id=?',(row['reservation_id'],)).fetchone() is not None})
        return result

    def mark_submitted(self, reservation_id):
        if self.state(reservation_id) == 'RELEASED':
            raise ValueError('Serbest rezervasyonla emir gönderilemez.')
        with self.store.db:
            self.store.db.execute("UPDATE risk_reservations SET state='COMMITTED' WHERE reservation_id=?", (reservation_id,))

    def release(self, reservation_id, *, flat_verified, orders_terminal):
        self.state(reservation_id)
        if flat_verified is not True or orders_terminal is not True:
            raise ValueError('Rezerv ancak sıfır pozisyon ve terminal emir kanıtıyla bırakılır.')
        with self.store.db:
            self.store.db.execute("UPDATE risk_reservations SET state='RELEASED' WHERE reservation_id=?", (reservation_id,))

    def close_session(self,session,*,flat_verified,orders_terminal):
        if (flat_verified is not True or orders_terminal is not True or
                session.get('active') is not False or session.get('status')!='CLOSED'):
            raise ValueError('Oturum ve risk rezervi yalnız doğrulanmış terminal durumda birlikte kapanır.')
        self.state(session['id'])
        with transaction(self.store) as db:
            db.execute("UPDATE risk_reservations SET state='RELEASED' WHERE reservation_id=? AND account_ref=?",
                       (session['id'],self.account_ref))
            db.execute('INSERT OR REPLACE INTO managed_sessions VALUES (?,?,0)',(session['id'],canonical(session)))

    def release_unused(self,reservation_id,owner,ownership):
        """Retire a pre-claim crash, never an uncertain or submitted order.

        Caller holds the execution lock. The account is reconciled first;
        plan cancellation and budget release commit together under SQLite lock.
        """
        self.state(reservation_id)
        ownership.verify()
        with transaction(self.store) as db:
            row=db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(reservation_id,)).fetchone()
            body=json.loads(row['body'])
            if row['state']!='RESERVED' or body['owner']!=owner:
                raise ValueError('Yalnız gönderilmemiş ve aynı sahibe ait rezerv geri alınabilir.')
            if db.execute('SELECT 1 FROM managed_sessions WHERE session_id=?',(reservation_id,)).fetchone():
                raise ValueError('Oturumu bulunan rezerv bu yolla serbest bırakılamaz.')
            plans=db.execute('SELECT * FROM plan_versions WHERE digest=? AND owner=?',(body['plan_digest'],owner)).fetchall()
            if len(plans)!=1:raise ValueError('Kullanılmamış rezervin plan sahipliği belirsiz.')
            plan=plans[0]
            if (plan['action_id'] is not None or plan['session_id'] is not None or
                    plan['state'] in ('EXECUTING','MANAGING','NEEDS_REVIEW') or
                    db.execute('SELECT 1 FROM plan_actions WHERE plan_id=? AND version=?',(plan['plan_id'],plan['version'])).fetchone()):
                raise ValueError('Giriş hakkı kullanılmış/belirsiz; rezerv geri alınamaz.')
            # Cancel the unused authorization too, so a later claim cannot
            # race a now-released reservation into an unreserved entry.
            if plan['state'] not in ('CLOSED','REJECTED','CANCELED','EXPIRED','SUPERSEDED'):
                db.execute("UPDATE plan_versions SET state='CANCELED' WHERE plan_id=? AND version=?",(plan['plan_id'],plan['version']))
            db.execute('DELETE FROM plan_slots WHERE plan_id=? AND version=?',(plan['plan_id'],plan['version']))
            db.execute("UPDATE risk_reservations SET state='RELEASED' WHERE reservation_id=?",(reservation_id,))
        return {'state':'UNUSED_RESERVATION_RELEASED','reservation_id':reservation_id,'executed':False}
