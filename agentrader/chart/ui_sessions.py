"""Owned, leased, process-local UI reports. Never market or execution evidence."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid

from agentrader.chart.chart_context import IDENTITY
from agentrader.chart.chart_market import validate_selection
from agentrader.chart.drawings.service import DrawingError, identifier

SCHEMA='chart-ui-session/1'
TTL_SECONDS=30
MIN_INTERVAL_SECONDS=.5
HEARTBEAT_SECONDS=5


class UIError(DrawingError):
    def __init__(self,code,status=422):
        self.code,self.status=code,status
        super().__init__(code)


def fields(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys.split()):raise UIError('INVALID_UI_SNAPSHOT')


def integer(value,low=0,high=32503680000000):
    if type(value) is not int or not low<=value<=high:raise UIError('INVALID_UI_SNAPSHOT')


def text(value,limit=64):
    if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 for c in value):raise UIError('INVALID_UI_SNAPSHOT')


def booleans(value,keys):
    fields(value,keys)
    if any(type(v) is not bool for v in value.values()):raise UIError('INVALID_UI_SNAPSHOT')


def decimal(value,nonnegative=False):
    text(value,128)
    if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',value):raise UIError('INVALID_UI_DECIMAL')
    try:n=Decimal(value)
    except InvalidOperation:raise UIError('INVALID_UI_DECIMAL') from None
    if not n.is_finite() or not -30<=n.adjusted()<=30 or nonnegative and n<0:raise UIError('INVALID_UI_DECIMAL')


def ids(values,limit=100):
    if not isinstance(values,list) or len(values)>limit:raise UIError('INVALID_UI_SNAPSHOT')
    for value in values:identifier(value)
    if len(set(values))!=len(values):raise UIError('INVALID_UI_SNAPSHOT')


def snapshot(value):
    fields(value,'market market_data viewport selection crosshair magnet panels indicators theme favorites notifications history persistent_refs loading')
    market=value['market'];fields(market,'source environment product price_type symbol interval')
    if {k:market[k] for k in IDENTITY}!=IDENTITY:raise UIError('SOURCE_MISMATCH')
    validate_selection(market['symbol'],market['interval'])
    data=value['market_data'];fields(data,'status stream_epoch generation sequence')
    text(data['status']);integer(data['generation'],-1);integer(data['sequence'],-1)
    if data['stream_epoch'] is not None:text(data['stream_epoch'])
    view=value['viewport'];fields(view,'logical_range time_range price_range width height scale inverted')
    integer(view['width'],0,100000);integer(view['height'],0,100000)
    if view['scale'] not in ('LINEAR','LOG') or type(view['inverted']) is not bool:raise UIError('INVALID_UI_SNAPSHOT')
    for name in ('logical_range','time_range','price_range'):
        bound=view[name]
        if bound is None:continue
        fields(bound,'from to')
        for v in bound.values():
            if name=='price_range':decimal(v)
            elif name=='time_range':integer(v,1,32503680000)
            elif type(v) not in (float,int) or not -1e9<=v<=1e9:raise UIError('INVALID_UI_SNAPSHOT')
    selected=value['selection'];fields(selected,'drawing_ids tool');ids(selected['drawing_ids']);text(selected['tool'])
    hover=value['crosshair'];fields(hover,'time price pane hover_candle')
    if hover['time'] is not None:integer(hover['time'],1,32503680000)
    if hover['price'] is not None:decimal(hover['price'])
    if hover['pane'] is not None:integer(hover['pane'],0,20)
    row=hover['hover_candle']
    if row is not None:
        fields(row,'time closed open high low close volume quote_volume');integer(row['time'],1,32503680000)
        if row['time']!=hover['time'] or type(row['closed']) is not bool:raise UIError('INVALID_UI_SNAPSHOT')
        for name in ('open','high','low','close','volume','quote_volume'):decimal(row[name],True)
    if type(value['magnet']) is not bool or value['theme'] not in ('dark','light'):raise UIError('INVALID_UI_SNAPSHOT')
    panel=value['panels'];fields(panel,'sidebar volume indicator_settings alerts templates bindings local_events replay command_dialog fullscreen pane_preset pane_weights')
    if panel['sidebar'] not in ('markets','drawings','data',None) or panel['pane_preset'] not in ('balanced','price-focus'):raise UIError('INVALID_UI_SNAPSHOT')
    if any(type(panel[k]) is not bool for k in ('volume','indicator_settings','alerts','templates','bindings','local_events','replay','command_dialog','fullscreen')):raise UIError('INVALID_UI_SNAPSHOT')
    fields(panel['pane_weights'],'price volume rsi atr macd')
    if any(type(v) not in (int,float) or not 0<v<=1000 for v in panel['pane_weights'].values()):raise UIError('INVALID_UI_SNAPSHOT')
    indic=value['indicators'];fields(indic,'settings_revision visible_ids');integer(indic['settings_revision']);ids(indic['visible_ids'],9)
    if any(v not in ('ema-fast','ema-slow','rsi-main','sma-main','atr-main','macd-main','bb-main','session-vwap','anchored-vwap') for v in indic['visible_ids']):raise UIError('INVALID_UI_SNAPSHOT')
    if not isinstance(value['favorites'],list) or len(value['favorites'])>200:raise UIError('INVALID_UI_SNAPSHOT')
    for symbol in value['favorites']:validate_selection(symbol,'15m')
    notice=value['notifications'];fields(notice,'in_app sound desktop desktop_permission sound_ready')
    if any(type(notice[k]) is not bool for k in ('in_app','sound','desktop','sound_ready')) or notice['desktop_permission'] not in ('granted','denied','default','unsupported'):raise UIError('INVALID_UI_SNAPSHOT')
    history=value['history'];fields(history,'can_undo can_redo undo_targets redo_targets')
    if any(type(history[k]) is not bool for k in ('can_undo','can_redo')):raise UIError('INVALID_UI_SNAPSHOT')
    for key in ('undo_targets','redo_targets'):
        if not isinstance(history[key],list) or len(history[key])>100:raise UIError('INVALID_UI_SNAPSHOT')
        for ref in history[key]:fields(ref,'drawing_id revision');identifier(ref['drawing_id']);integer(ref['revision'],1)
    fields(value['persistent_refs'],'workspace_revision profile_revision indicator_settings_revision')
    for v in value['persistent_refs'].values():
        if v is not None:integer(v)
    booleans(value['loading'],'drawings indicators profile')
    return deepcopy(value)


class UISessionStore:
    def __init__(self,*,clock=time.time,monotonic=time.monotonic,ttl=TTL_SECONDS,max_sessions=128):
        self.clock,self.monotonic,self.ttl=clock,monotonic,ttl
        self.max_sessions=max_sessions;self.server_instance_id=uuid.uuid4().hex
        self.rows={};self.lock=threading.RLock();self.retired=0

    def retired_bits(self,key):
        # Fixed 8 KiB Bloom tombstones: no retired ID can revive after row eviction.
        # Collisions only reject a fresh identity; the publisher rotates and retries.
        digest=hashlib.sha256(json.dumps(key).encode()).digest()
        return sum(1 << bit for bit in {int.from_bytes(digest[i:i+2],'big') for i in (0,2,4)})


class UISessions:
    def __init__(self,database,owner,*,store=None):
        self.database,self.owner=Path(database),owner
        self.store=store or UISessionStore()

    def policy(self,authentication_required=False):
        return dict(schema_version='chart-ui-policy/1',server_instance_id=self.store.server_instance_id,
                    ttl_seconds=self.store.ttl,min_publish_interval_ms=500,heartbeat_seconds=HEARTBEAT_SECONDS,
                    authentication_required=authentication_required,client_reported=True,order_authority=False)

    def put(self,workspace_id,session_id,publisher_key,payload):
        identifier(workspace_id);identifier(session_id)
        if not isinstance(publisher_key,str) or not re.fullmatch('[a-f0-9]{64}',publisher_key):raise UIError('UI_PUBLISHER_KEY_REQUIRED',403)
        fields(payload,'schema_version server_instance_id sequence client_time_ms visibility client_status snapshot')
        if payload['schema_version']!=SCHEMA:raise UIError('INVALID_UI_SESSION_SCHEMA')
        if payload['server_instance_id']!=self.store.server_instance_id:raise UIError('UI_SESSION_SERVER_RESTARTED',409)
        integer(payload['sequence'],1,2**53-1);integer(payload['client_time_ms'])
        if payload['visibility'] not in ('visible','hidden') or payload['client_status'] not in ('CONNECTED','OFFLINE','CLOSED'):raise UIError('INVALID_UI_SNAPSHOT')
        clean=snapshot(payload['snapshot'])
        key=(self.owner,workspace_id,session_id);hashed=hashlib.sha256(publisher_key.encode()).digest()
        wire=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)
        with self.store.lock:
            now=self.store.monotonic();previous=self.store.rows.get(key)
            if previous:
                if not hmac.compare_digest(previous['key_hash'],hashed):raise UIError('UI_PUBLISHER_MISMATCH',403)
                if payload['sequence']==previous['sequence'] and wire==previous['wire']:return self._ack(session_id,previous,True)
                if payload['sequence']<=previous['sequence']:raise UIError('UI_SESSION_SEQUENCE_CONFLICT',409)
                if previous['client_status']=='CLOSED':raise UIError('UI_SESSION_CLOSED',410)
                if now-previous['received_mono']>=self.store.ttl:raise UIError('UI_SESSION_EXPIRED',410)
                restrictive=payload['visibility']=='hidden' or payload['client_status']!='CONNECTED'
                if now-previous['received_mono']<MIN_INTERVAL_SECONDS and not restrictive:raise UIError('UI_SESSION_RATE_LIMIT',429)
            else:
                bits=self.store.retired_bits(key)
                if self.store.retired & bits == bits:raise UIError('UI_SESSION_EXPIRED',410)
                if payload['sequence']!=1 and payload['client_status']!='CLOSED':raise UIError('UI_SESSION_UNKNOWN',409)
                if len(self.store.rows)>=self.store.max_sessions:
                    retired=next((k for k,r in self.store.rows.items() if r['client_status']=='CLOSED' or now-r['received_mono']>=self.store.ttl),None)
                    if retired is None:raise UIError('UI_SESSION_LIMIT',429)
                    self.store.retired |= self.store.retired_bits(retired)
                    del self.store.rows[retired]
            row=dict(key_hash=hashed,sequence=payload['sequence'],wire=wire,snapshot=clean,
                     received_mono=now,received_at=self.store.clock(),client_time_ms=payload['client_time_ms'],
                     visibility=payload['visibility'],client_status=payload['client_status'])
            self.store.rows[key]=row
            return self._ack(session_id,row,False)

    def _ack(self,session_id,row,duplicate):
        return dict(schema_version=SCHEMA,ui_session_id=session_id,server_instance_id=self.store.server_instance_id,
                    sequence=row['sequence'],duplicate=duplicate,ttl_seconds=self.store.ttl,order_authority=False)

    def _view(self,session_id,row,include_snapshot=False):
        age=max(0,self.store.monotonic()-row['received_mono'])
        reason=('HIDDEN' if row['visibility']!='visible' else 'CLOSED' if row['client_status']=='CLOSED' else
                'OFFLINE' if row['client_status']=='OFFLINE' else 'EXPIRED' if age>=self.store.ttl else None)
        result=dict(schema_version='chart-ui-session-view/1',ui_session_id=session_id,
                    server_instance_id=self.store.server_instance_id,sequence=row['sequence'],
                    state='UI_UNAVAILABLE' if reason else 'READY',reason=reason,stale=age>=self.store.ttl,
                    age_ms=round(age*1000),ttl_seconds=self.store.ttl,
                    server_received_utc=datetime.fromtimestamp(row['received_at'],timezone.utc).isoformat(),
                    client_time_ms=row['client_time_ms'],client_time_trusted=False,
                    authority='CLIENT_REPORTED_UI_NOT_MARKET_EVIDENCE',order_authority=False)
        if reason is None and include_snapshot:result['snapshot']=deepcopy(row['snapshot'])
        return result

    def list(self,workspace_id,policy_only=False,authentication_required=False):
        identifier(workspace_id)
        with self.store.lock:
            sessions=[] if policy_only else [self._view(sid,row) for (owner,work,sid),row in self.store.rows.items()
                                            if owner==self.owner and work==workspace_id and row['visibility']=='visible' and row['client_status']!='CLOSED']
        return dict(schema_version='chart-ui-sessions/1',policy=self.policy(authentication_required),sessions=sessions,order_authority=False)

    def show(self,workspace_id,session_id):
        identifier(workspace_id);identifier(session_id)
        with self.store.lock:
            row=self.store.rows.get((self.owner,workspace_id,session_id))
            if row is None or row['visibility']!='visible':
                return dict(state='UI_UNAVAILABLE',reason='MISSING_OR_HIDDEN',order_authority=False)
            result=self._view(session_id,row,True)
        if 'snapshot' not in result:return result
        value=result['snapshot'];selected=value['selection']['drawing_ids']
        refs=value['history']['undo_targets']+value['history']['redo_targets']
        requested=list(set(selected+[r['drawing_id'] for r in refs]));heads={}
        if requested:
            with closing(sqlite3.connect(self.database.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)) as db:
                rows=db.execute('''SELECT r.drawing_id,r.revision,r.geometry,r.deleted FROM app_drawing_revisions r JOIN app_drawing_heads h
                    ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision
                    WHERE r.owner=? AND r.workspace_id=? AND r.drawing_id IN ('''+','.join('?' for _ in requested)+')',
                    [self.owner,workspace_id,*requested]).fetchall()
                heads={r[0]:(r[1],bool(r[3])) for r in rows if json.loads(r[2])['symbol']==value['market']['symbol']}
        value['selection']['drawing_ids']=[sid for sid in selected if sid in heads and not heads[sid][1]]
        result['selection_reconciled']=value['selection']['drawing_ids']!=selected
        for name in ('undo_targets','redo_targets'):
            value['history'][name]=[{**r,'current_revision':heads[r['drawing_id']][0],
                                    'revision_matches':r['revision']==heads[r['drawing_id']][0],
                                    'target_deleted':heads[r['drawing_id']][1]}
                                    for r in value['history'][name] if r['drawing_id'] in heads]
        result['ui_context_id']=hashlib.sha256(json.dumps(dict(server=self.store.server_instance_id,session=session_id,
                                                              sequence=result['sequence'],snapshot=value),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return result
