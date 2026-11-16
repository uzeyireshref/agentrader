"""Account-bound durable risk envelopes. Fills never release a grid's refill budget."""
import json
import time
from dataclasses import asdict
from contextlib import nullcontext

from agentrader.bot.plans import canonical, digest, transaction
from agentrader.bot.portfolio import Exposure, evaluate_portfolio


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
            store.db.execute('''CREATE TABLE IF NOT EXISTS single_reservation_caps (
                reservation_id TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL)''')

    def _effective_exposures(self,db,row,saved):
        from dataclasses import replace
        from agentrader.bot.risk import number
        exposures=[Exposure(**e) for e in saved['exposures']]
        from agentrader.bot.position_commands import extra_exposures
        extras=extra_exposures(self.store,row['reservation_id'],self.account_ref,saved['owner'])
        cap=db.execute('SELECT * FROM single_reservation_caps WHERE reservation_id=?',(row['reservation_id'],)).fetchone()
        if cap is None:return exposures+extras
        proof=json.loads(cap['body'])
        projection=db.execute('SELECT * FROM order_projection WHERE client_id=?',(proof['client_id'],)).fetchone()
        if (digest(proof)!=cap['digest'] or proof['plan_digest']!=saved['plan_digest'] or len(exposures)!=1 or
                projection is None or projection['owner']!=row['reservation_id'] or projection['symbol']!=exposures[0].symbol or
                projection['side']!=('BUY' if exposures[0].direction=='LONG' else 'SELL') or
                projection['status'] not in ('FILLED','CANCELED','EXPIRED','REJECTED') or
                number(projection['quantity'])!=number(exposures[0].quantity) or
                not 0<=number(projection['filled'])<=number(projection['quantity'])):
            raise ValueError('SINGLE terminal miktar rezervi kanıtı uyuşmuyor.')
        # A later cumulative fill can only enlarge this cap, never free risk.
        quantity=max(number(proof['confirmed_filled']),number(projection['filled']))
        if not 0<quantity<=number(exposures[0].quantity):raise ValueError('SINGLE gerçekleşme rezervi geçersiz.')
        return [replace(exposures[0],quantity=str(quantity))]+extras

    def cap_single_terminal(self,session,entry):
        """Release only the terminal, unfilled SINGLE remainder after protection."""
        from agentrader.bot.risk import number
        if (session.get('engine')!='v2' or session['plan']['execution']['strategy']!='SINGLE' or
                session.get('status')!='PROTECTED' or entry['status'] not in ('FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH') or
                not 0<number(entry['executedQty'])<=number(session['prepared']['quantity'])):
            raise ValueError('SINGLE kalan rezervi için terminal giriş ve doğrulanmış koruma gerekli.')
        self.assert_binding(session['id'],self.store.db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()[0],
                            session['plan_ref']['digest'],session['prepared']['exposures'])
        proof={'client_id':session['entry_id'],'plan_digest':session['plan_ref']['digest'],'confirmed_filled':entry['executedQty']}
        with transaction(self.store) as db:
            row=db.execute('SELECT * FROM risk_reservations WHERE reservation_id=?',(session['id'],)).fetchone()
            old=db.execute('SELECT * FROM single_reservation_caps WHERE reservation_id=?',(session['id'],)).fetchone()
            if old:
                saved=json.loads(old['body'])
                if digest(saved)!=old['digest'] or saved['client_id']!=proof['client_id']:raise ValueError('SINGLE rezerv sınırı kimliği bozuk.')
                proof['confirmed_filled']=str(max(number(saved['confirmed_filled']),number(proof['confirmed_filled'])))
            db.execute('INSERT OR REPLACE INTO single_reservation_caps VALUES(?,?,?)',(session['id'],canonical(proof),digest(proof)))
            self._effective_exposures(db,row,json.loads(row['body']))

    def reserve(self, reservation_id, owner, plan_digest, exposures, snapshot, limits,*,_db=None):
        if not all(isinstance(v, str) and v for v in (reservation_id, owner, plan_digest)):
            raise ValueError('Rezervasyon kimliği, sahibi ve plan özeti gerekli.')
        body = {'owner': owner, 'plan_digest': plan_digest,
                'exposures': [asdict(e) for e in exposures]}
        empty=(snapshot.get('flat_verified') is True or
               (snapshot.get('target_flat_verified') is True and snapshot.get('ownership_verified') is True))
        if not body['exposures'] or not empty:
            raise ValueError('İlk risk rezervi için doğrulanmış boş hesap görünümü gerekli.')
        if _db is not None and (_db is not self.store.db or not _db.in_transaction):raise ValueError('Rezerv etkin depo transaction gerektirir.')
        with (transaction(self.store) if _db is None else nullcontext(_db)) as db:
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
                other=self._effective_exposures(db,row,saved)
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
        from agentrader.bot.brackets import select_bracket
        from agentrader.bot.risk import number
        combined=list(extra_exposures)
        for row in self.store.db.execute("SELECT * FROM risk_reservations WHERE account_ref=? AND state!='RELEASED'",(self.account_ref,)):
            body=json.loads(row['body'])
            if digest(body)!=row['digest']:raise ValueError('Portföy risk rezervi özeti uyuşmuyor.')
            combined.extend(self._effective_exposures(self.store.db,row,body))
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
