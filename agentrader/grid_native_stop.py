"""Opt-in close-all stop ladder. Preserve the original exchange fallback.

No automatic POST/DELETE retry. Caller holds the account execution lock.
The bot still owns the watermark; this is not TRAILING_STOP_MARKET.
"""
import json
import time

from .exchange import ExchangeError
from .order_rules import validate_order
from .plans import digest
from .risk import number
from .v2_preflight import fresh


def enabled(s):
    return (s['plan']['management'].get('trailing') or {}).get('native_stop') is True


def validate_transitions(r,s):
    previous=None;level=number(s['plan']['stop']);sign=1 if s['plan']['direction']=='LONG' else -1
    transitions=s.get('stop_transitions',[])
    if transitions and not enabled(s):raise ValueError('Native grid stopu için onaylı politika gerekli.')
    for i,t in enumerate(transitions):
        p=t['proposal']['params'];trigger=number(p['triggerPrice'])
        expected={'symbol':s['symbol'],'side':'SELL' if sign==1 else 'BUY',
                  'positionSide':'BOTH' if s['plan']['position_mode']=='one-way' else s['plan']['direction'],
                  'type':'STOP_MARKET','closePosition':'true','workingType':'MARK_PRICE',
                  'triggerPrice':str(trigger),'algoType':'CONDITIONAL','clientAlgoId':r._id(s,['grid-native-stop',i])}
        if (t['proposal']['path']!='/fapi/v1/algoOrder' or p!=expected or t.get('previous')!=previous or
                t.get('state') not in ('PREPARED','VERIFIED','APPLIED') or
                i<len(transitions)-1 and t['state']!='APPLIED' or sign*(trigger-level)<=0 or
                sign*(r._grid_stop(s)-trigger)<0):
            raise ValueError('Native grid stop geçişi onaylı yön/seviye/kimlikle uyuşmuyor.')
        previous=p['clientAlgoId'];level=trigger


def retired(r,s,cid,actual):
    if actual.get('algoStatus')!='CANCELED' or actual.get('actualOrderId') not in (None,'',0,'0'):return False
    if not any(t['previous']==cid and t['state'] in ('VERIFIED','APPLIED') for t in s.get('stop_transitions',[])):return False
    command=digest(json.dumps(['/fapi/v1/algoOrder',{'clientAlgoId':cid}],sort_keys=True))
    return r.store.db.execute('SELECT 1 FROM v2_cancellations WHERE command_id=?',(command,)).fetchone() is not None


def verify(params,actual):
    if (not isinstance(actual,dict) or actual.get('algoStatus')!='NEW' or
            any(actual.get(k)!=params[k] for k in ('clientAlgoId','symbol','side','positionSide','workingType')) or
            actual.get('orderType',actual.get('type'))!='STOP_MARKET' or
            number(actual.get('triggerPrice',0))!=number(params['triggerPrice']) or
            str(actual.get('closePosition',False)).lower()!='true' or
            number(actual.get('quantity',0))!=0 or str(actual.get('reduceOnly',False)).lower()!='false'):
        raise ValueError('Yeni native grid stopu etkin/eşleşen close-all koruma değil; eski korumalar tutuluyor.')


def move_stop(r,s,amount,mark,info,execute,results,algos):
    if not enabled(s) or not amount:return None
    transitions=s.get('stop_transitions',[]);desired=r._grid_stop(s)
    pending=transitions and transitions[-1]['state']!='APPLIED'
    current=number(transitions[-1]['proposal']['params']['triggerPrice']) if transitions else number(s['plan']['stop'])
    if not pending and desired==current:return None
    if not execute:return {'state':'GRID_STOP_MOVE_REQUIRED','session_id':s['id'],'executed':False}
    if not pending:
        previous=transitions[-1]['proposal']['params']['clientAlgoId'] if transitions else None
        params={'symbol':s['symbol'],'side':'SELL' if s['plan']['direction']=='LONG' else 'BUY',
                'positionSide':'BOTH' if s['plan']['position_mode']=='one-way' else s['plan']['direction'],
                'type':'STOP_MARKET','closePosition':'true','triggerPrice':str(desired),
                'workingType':'MARK_PRICE','clientAlgoId':r._id(s,['grid-native-stop',len(transitions)])}
        proposal=validate_order(params,info,s['plan']['position_mode'],'CLOSE',mark['markPrice'],int(time.time()*1000))
        transitions=s.setdefault('stop_transitions',[])
        transitions.append({'proposal':proposal,'previous':previous,'state':'PREPARED'})
        r._save(s)
    t=transitions[-1];params=t['proposal']['params'];cid=params['clientAlgoId']
    latest=r.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
    fresh(latest,s['symbol'],int(time.time()*1000)+getattr(r.x,'offset_ms',0),r.limits.max_age_seconds)
    sign=1 if s['plan']['direction']=='LONG' else -1
    if sign*(number(latest['markPrice'])-r._grid_stop(s))<=0:
        r._stop(s,'Native stop gönderiminden önce takip eşiği aşıldı.')
        return r._cleanup(s,r._results(s),r._algos(s),latest,info,True)
    # The saved unsent proposal has no intent and cannot own a broker order yet.
    if not r._owned_grid(s,r._results(s),r._algos(s)):
        r._stop(s,'Native stop gönderiminden önce envanter boşaldı.')
        return r._cleanup(s,r._results(s),r._algos(s),latest,info,True)
    latest=r.x.get('/fapi/v1/premiumIndex',{'symbol':s['symbol']})
    fresh(latest,s['symbol'],int(time.time()*1000)+getattr(r.x,'offset_ms',0),r.limits.max_age_seconds)
    if sign*(number(latest['markPrice'])-r._grid_stop(s))<=0:
        r._stop(s,'Sahiplik doğrulamasından sonra takip eşiği aşıldı.')
        return r._cleanup(s,r._results(s),r._algos(s),latest,info,True)
    try:r._post(s,t['proposal'])
    except ExchangeError as exc:
        if exc.delivery_status in ('NOT_SENT','REJECTED'):
            r._stop(s,'Native grid stopu reddedildi; yeni girişler kapalı.')
        raise
    actual=r.x.get('/fapi/v1/algoOrder',{'clientAlgoId':cid})
    verify(params,actual);algos[cid]=actual
    # Stop activation or a native child during verification must never retire
    # the previous stop or allow a new grid opening.
    observed=r._algos(s)
    if r._bad_grid_algos(s,observed):
        r._stop(s,'Native stop doğrulanırken koruma tetiklendi/değişti.')
        return r._cleanup(s,r._results(s),observed,latest,info,True)
    r._owned_grid(s,r._results(s),observed)
    t['state']='VERIFIED';r._save(s)
    if t['previous']:
        r._cancel('/fapi/v1/algoOrder',{'clientAlgoId':t['previous']})
        old=r.x.get('/fapi/v1/algoOrder',{'clientAlgoId':t['previous']})
        if old.get('algoStatus')!='CANCELED' or old.get('actualOrderId') not in (None,'',0,'0'):
            r._stop(s,'Önceki native stop iptali terminal/çocuksuz doğrulanamadı.')
            raise ValueError('Önceki native stop uzlaştırılmalı; yenisi ve sabit koruma tutuluyor.')
    t['state']='APPLIED';r._save(s)
    return {'state':'GRID_STOP_MOVED','session_id':s['id'],'executed':True,'trigger_price':params['triggerPrice']}
