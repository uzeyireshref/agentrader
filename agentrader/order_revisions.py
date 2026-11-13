"""Verified amendments overlay immutable creation intents; unknown PUTs never do."""
import json

from .plans import digest
from .risk import number


def effective_params(store,client_id):
    intent=store.intent(client_id)
    if intent is None or intent['path']!='/fapi/v1/order':raise ValueError('Sahip olunan normal emir niyeti gerekli.')
    params=json.loads(intent['params'])
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='order_modifications'").fetchone():
        for row in store.db.execute("SELECT * FROM order_modifications WHERE client_id=? AND state='APPLIED' ORDER BY seq",(client_id,)):
            body=json.loads(row['body'])
            if digest(body)!=row['digest']or body['before_params']!=params:raise ValueError('Emir değişiklik zinciri uyuşmuyor.')
            params=params|{'quantity':body['quantity'],'price':body['price']}
    return params


def commit_projection(db,client_id,quantity,order):
    row=db.execute('SELECT * FROM order_projection WHERE client_id=?',(client_id,)).fetchone()
    if row is None:raise ValueError('Emir değişikliği için kalıcı gerçekleşme kaydı gerekli.')
    filled=max(number(row['filled']),number(order['executedQty']))
    if filled>number(quantity):raise ValueError('Değişen miktar gerçekleşen toplamın altında.')
    status=order['status']
    if status=='EXPIRED_IN_MATCH':status='EXPIRED'
    if filled==number(quantity):status='FILLED'
    db.execute('UPDATE order_projection SET quantity=?,filled=?,status=?,observed_ms=MAX(observed_ms,?) WHERE client_id=?',
               (quantity,str(filled),status,int(order['updateTime']),client_id))
