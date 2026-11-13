"""Durable notification outbox. Delivery never grants order authorization."""
import json
import re
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, build_opener

from .exchange import NoRedirect
from .plans import canonical, digest, transaction


class DeliveryError(Exception):
    def __init__(self, *, retryable=True, retry_after=0):
        super().__init__('Bildirim teslimi doğrulanamadı.')
        self.retryable=retryable
        self.retry_after=retry_after


def chat_id(value):
    value=str(value)
    if not re.fullmatch(r'-?[1-9][0-9]{0,19}',value):
        raise ValueError('Telegram sohbet kimliği sayısal olmalı.')
    return value


class NotificationQueue:
    def __init__(self,store,clock=time.time):
        self.store,self.clock=store,clock
        with store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS notification_outbox (
                event_id TEXT NOT NULL,destination TEXT NOT NULL,body TEXT NOT NULL,digest TEXT NOT NULL,
                state TEXT NOT NULL,attempts INTEGER NOT NULL,next_at REAL NOT NULL,
                lease_until REAL NOT NULL,lease_token TEXT,receipt TEXT,
                PRIMARY KEY(event_id,destination))''')

    def enqueue(self,event_id,destination,text):
        destination=chat_id(destination)
        if not isinstance(event_id,str) or not 1<=len(event_id)<=128:
            raise ValueError('Bildirim olay kimliği gerekli.')
        if not isinstance(text,str) or not 1<=len(text)<=3500:
            raise ValueError('Bildirim 1–3500 karakter olmalı.')
        body=canonical({'event_id':event_id,'destination':destination,'text':text})
        with transaction(self.store) as db:
            old=db.execute('SELECT digest FROM notification_outbox WHERE event_id=? AND destination=?',
                           (event_id,destination)).fetchone()
            if old:
                if old['digest']!=digest(body):raise ValueError('Bildirim kimliği farklı içerikle tekrar kullanılamaz.')
                return {'state':'ALREADY_QUEUED','event_id':event_id}
            db.execute('INSERT INTO notification_outbox VALUES (?,?,?,?,?,0,?,0,NULL,NULL)',
                       (event_id,destination,body,digest(body),'PENDING',self.clock()))
        return {'state':'QUEUED','event_id':event_id}

    def _claim(self):
        now=self.clock()
        with transaction(self.store) as db:
            row=db.execute('''SELECT * FROM notification_outbox
                WHERE (state IN ('PENDING','RETRY') AND next_at<=?)
                   OR (state='SENDING' AND lease_until<=?)
                ORDER BY next_at,event_id LIMIT 1''',(now,now)).fetchone()
            if row is None:return None
            if digest(row['body'])!=row['digest']:raise ValueError('Bildirim kuyruğu bütünlüğü uyuşmuyor.')
            if row['attempts']>=8:
                db.execute("UPDATE notification_outbox SET state='FAILED' WHERE event_id=? AND destination=?",
                           (row['event_id'],row['destination']))
                return None
            token=uuid.uuid4().hex
            db.execute('''UPDATE notification_outbox SET state='SENDING',attempts=attempts+1,
                lease_until=?,lease_token=? WHERE event_id=? AND destination=?''',
                       (now+60,token,row['event_id'],row['destination']))
            return dict(row)|{'lease_token':token,'attempts':row['attempts']+1}

    def deliver_one(self,sender):
        row=self._claim()
        if row is None:return {'state':'IDLE'}
        body=json.loads(row['body'])
        try:
            receipt=sender.send(body['destination'],body['text']+'\nOlay: '+body['event_id'])
        except DeliveryError as exc:
            state='RETRY' if exc.retryable and row['attempts']<8 else 'FAILED'
            delay=max(min(300,2**row['attempts']),exc.retry_after)
            receipt=None
        else:
            state,delay='DELIVERED',0
        with self.store.db:
            changed=self.store.db.execute('''UPDATE notification_outbox
                SET state=?,next_at=?,lease_until=0,receipt=?,lease_token=NULL
                WHERE event_id=? AND destination=? AND state='SENDING' AND lease_token=?''',
                (state,self.clock()+delay,json.dumps(receipt),row['event_id'],row['destination'],row['lease_token'])).rowcount
            if changed!=1:raise ValueError('Bildirim teslim kirası değişti; sonuç ayrıca doğrulanmalı.')
        return {'state':state,'event_id':row['event_id'],'attempts':row['attempts']}

    def status(self):
        return {r['state']:r['n'] for r in self.store.db.execute(
            'SELECT state,COUNT(*) AS n FROM notification_outbox GROUP BY state')}


class TelegramSender:
    def __init__(self,token,allowed_chat,*,opener=None):
        if not isinstance(token,str) or not re.fullmatch(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,128}',token):
            raise ValueError('Telegram bot anahtarı geçersiz veya eksik.')
        self._token=token
        self.allowed_chat=chat_id(allowed_chat)
        self.opener=opener or build_opener(NoRedirect())

    def send(self,destination,text):
        if chat_id(destination)!=self.allowed_chat:
            raise DeliveryError(retryable=False)
        request=Request('https://api.telegram.org/bot'+self._token+'/sendMessage',
                        data=json.dumps({'chat_id':destination,'text':text}).encode(),
                        headers={'Content-Type':'application/json'},method='POST')
        try:
            with self.opener.open(request,timeout=10) as response:
                payload=json.load(response)
            result=payload.get('result',{})
            if (payload.get('ok')is not True or type(result.get('message_id'))is not int
                    or str(result.get('chat',{}).get('id'))!=self.allowed_chat):
                raise DeliveryError()
            return {'message_id':result['message_id']}
        except HTTPError as exc:
            retry=0
            if exc.code==429:
                try:
                    value=json.loads(exc.read()).get('parameters',{}).get('retry_after',0)
                    if type(value)is int and 0<=value<=86400:retry=value
                except (ValueError,AttributeError,OSError):pass
            raise DeliveryError(retryable=exc.code==429 or exc.code>=500,retry_after=retry) from None
        except DeliveryError:
            raise
        except Exception:
            # urllib errors may contain the private bot-token URL.
            raise DeliveryError() from None


def queue_session_report(queue,destination,report):
    safe={k:report[k] for k in ('state','session_id','kind','cell','stage','quantity','position','positions',
                               'trigger_price','attempt','stream_generation') if k in report}
    stamp=report.get('observed_at_ms',time.time_ns())
    event_id=digest([safe,stamp])
    return queue.enqueue(event_id,destination,json.dumps(safe,ensure_ascii=False))
