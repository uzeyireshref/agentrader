"""Cancel selected owned normal orders once, then prove each result with GET.

Caller holds execution_lock and has authorized stopping/draining these orders.
No account-wide cancel, no unowned order IDs, no retry after uncertain DELETE.
"""
import hashlib
import json
import re

from .exchange import ExchangeError
from .plans import canonical,digest,transaction
from .risk import number
from .order_revisions import effective_params

TERMINAL={'FILLED','CANCELED','EXPIRED','EXPIRED_IN_MATCH','REJECTED'}


class OwnedBatchCancel:
    def __init__(self,exchange,store):
        self.x,self.store=exchange,store
        self.account_ref=hashlib.sha256(exchange.config.api_key.encode()).hexdigest()
        with store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS batch_cancellations (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,state TEXT NOT NULL)''')
            store.db.execute('''CREATE TABLE IF NOT EXISTS v2_cancellations (
                command_id TEXT PRIMARY KEY,body TEXT NOT NULL,state TEXT NOT NULL)''')

    def _single(self,symbol,cid):
        body=json.dumps(['/fapi/v1/order',{'symbol':symbol,'origClientOrderId':cid}],sort_keys=True)
        return digest(body),body

    def _read(self,symbol,cid):
        row=self.store.db.execute('SELECT * FROM intents WHERE client_id=?',(cid,)).fetchone()
        if row is None or row['path']!='/fapi/v1/order':raise ValueError('Toplu iptal için sahip olunan normal emir niyeti gerekli.')
        p=effective_params(self.store,cid)
        if p.get('symbol')!=symbol or p.get('newClientOrderId')!=cid:raise ValueError('Toplu iptal sembol/emir kimliği uyuşmuyor.')
        a=self.x.get('/fapi/v1/order',{'symbol':symbol,'origClientOrderId':cid})
        if (a.get('clientOrderId')!=cid or any(a.get(k)!=p.get(k)for k in('symbol','side','positionSide'))
                or number(a['origQty'])!=number(p['quantity'])
                or not 0<=number(a['executedQty'])<=number(a['origQty'])):
            raise ValueError('Toplu iptal emir sahipliği/miktarı doğrulanamadı.')
        previous=json.loads(row['response'])if row['response']else{}
        if previous.get('orderId')is not None and str(previous['orderId'])!=str(a.get('orderId')):
            raise ValueError('Toplu iptal kimliği başka borsa emri için yeniden kullanılmış.')
        if a.get('status')not in TERMINAL|{'NEW','PARTIALLY_FILLED'}:raise ValueError('Toplu iptal emir durumu bilinmiyor.')
        self.store.update(cid,a['status'],a)
        return a

    def cancel(self,symbol,client_ids,*,owned_client_ids):
        if not isinstance(symbol,str)or not re.fullmatch(r'[A-Z0-9]{2,20}USDT',symbol):raise ValueError('Toplu iptal sembolü geçersiz.')
        if not isinstance(client_ids,(list,tuple))or not 1<=len(client_ids)<=10:
            raise ValueError('Toplu iptal 1–10 seçili emir gerektirir.')
        if any(not isinstance(c,str)or not re.fullmatch(r'[.A-Za-z:/0-9_-]{1,36}',c)for c in client_ids):
            raise ValueError('Toplu iptal istemci kimliği geçersiz.')
        if len(set(client_ids))!=len(client_ids)or not set(client_ids)<=set(owned_client_ids):
            raise ValueError('Tekrarlı veya sahip olunmayan emir toplu iptale alınamaz.')
        before={cid:self._read(symbol,cid)for cid in client_ids}
        pending=[cid for cid in client_ids if before[cid]['status']not in TERMINAL]
        selected=[]
        for cid in pending:
            key,_=self._single(symbol,cid)
            if not self.store.db.execute('SELECT 1 FROM v2_cancellations WHERE command_id=?',(key,)).fetchone():selected.append(cid)
        command_id=None
        if selected:
            body={'account_ref':self.account_ref,'symbol':symbol,'client_ids':sorted(selected)}
            command_id=digest(body)
            with transaction(self.store)as db:
                if db.execute('SELECT 1 FROM batch_cancellations WHERE command_id=?',(command_id,)).fetchone():
                    raise ValueError('Toplu iptal kaydı uzlaştırılmalı; tekrar gönderilmedi.')
                db.execute('INSERT INTO batch_cancellations VALUES (?,?,?)',(command_id,canonical(body),'SUBMITTING'))
                for cid in selected:
                    key,single=self._single(symbol,cid)
                    db.execute('INSERT INTO v2_cancellations VALUES (?,?,?)',(key,single,'SUBMITTING'))
            try:
                self.x.request('DELETE','/fapi/v1/batchOrders',
                               {'symbol':symbol,'origClientOrderIdList':json.dumps(sorted(selected),separators=(',',':'))})
            except ExchangeError:
                with self.store.db:
                    self.store.db.execute("UPDATE batch_cancellations SET state='UNKNOWN' WHERE command_id=?",(command_id,))
                    for cid in selected:self.store.db.execute("UPDATE v2_cancellations SET state='UNKNOWN' WHERE command_id=?",(self._single(symbol,cid)[0],))
                raise
            with self.store.db:self.store.db.execute("UPDATE batch_cancellations SET state='RESPONSE_RECEIVED' WHERE command_id=?",(command_id,))
        after={cid:self._read(symbol,cid)for cid in client_ids}
        unresolved=[cid for cid,a in after.items()if a['status']not in TERMINAL]
        with self.store.db:
            for cid,a in after.items():
                if a['status']in TERMINAL:self.store.db.execute("UPDATE v2_cancellations SET state='ACKNOWLEDGED' WHERE command_id=?",(self._single(symbol,cid)[0],))
            if command_id:self.store.db.execute('UPDATE batch_cancellations SET state=? WHERE command_id=?',('PARTIAL'if unresolved else'RECONCILED',command_id))
            for old in self.store.db.execute("SELECT command_id,body FROM batch_cancellations WHERE state!='RECONCILED'").fetchall():
                b=json.loads(old['body'])
                if b['account_ref']!=self.account_ref or b['symbol']!=symbol:continue
                states=[self.store.db.execute('SELECT state FROM intents WHERE client_id=?',(cid,)).fetchone()for cid in b['client_ids']]
                if all(row and row['state']in TERMINAL for row in states):
                    self.store.db.execute("UPDATE batch_cancellations SET state='RECONCILED' WHERE command_id=?",(old['command_id'],))
        report={'state':'PARTIAL'if unresolved else'RECONCILED','orders':[{'client_id':c,'status':a['status'],'executed_quantity':a['executedQty']}for c,a in after.items()],
                'unresolved':unresolved,'submitted_count':len(selected),'automatic_resend':False}
        self.store.event('owned_batch_cancel',report)
        return report
