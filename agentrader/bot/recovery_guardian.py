"""Independent demo recovery supervisor. Never opens a plan or repeats an entry.

The foreground executor owns runtime.lock for its whole lifetime. This process
pulses a separate lease while waiting, then recovers only after that OS lock is
released. Exchange capabilities are restricted to recorded protection/reduction
and cancellation. Default mode performs observations only.
"""
from contextlib import closing
from dataclasses import asdict
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import time

from agentrader.chart.chart_bindings import binding_hash
from agentrader.shared.exchange import allowed_requests
from agentrader.shared.locking import execution_lock, ExecutionBusy
from agentrader.bot.risk import number

MAX_LEASE_AGE = 5


def paths(database):
    database=Path(database).resolve()
    return database,Path(str(database)+'.guardian.lock'),Path(str(database)+'.guardian.json')


def process_token(pid):
    """Live process creation identity; a stale/reused PID is not a guardian."""
    if type(pid) is not int or pid<=0:return None
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
        kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4;kernel.GetProcessTimes.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        handle=kernel.OpenProcess(0x100000|0x1000,False,pid)
        if not handle:return None
        try:
            if kernel.WaitForSingleObject(handle,0)!=0x102:return None
            values=[wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle,*(ctypes.byref(v) for v in values)):return None
            return 'windows:'+str((values[0].dwHighDateTime<<32)|values[0].dwLowDateTime)
        finally:kernel.CloseHandle(handle)
    try:
        os.kill(pid,0)
        stat=Path(f'/proc/{pid}/stat')
        return 'posix:'+stat.read_text().rsplit(')',1)[1].split()[19] if stat.exists() else 'pid:'+str(pid)
    except (OSError,ValueError,IndexError):return None


def account_ref(exchange):
    if not exchange.config.api_key:raise ValueError('DEMO_ACCOUNT_IDENTITY_REQUIRED')
    return hashlib.sha256(exchange.config.api_key.encode()).hexdigest()


def profile_hash(limits):return binding_hash({k:str(v) for k,v in asdict(limits).items()})


def lease_signature(body,exchange):
    secret=exchange.config.api_secret
    if not secret:raise ValueError('DEMO_CREDENTIALS_REQUIRED')
    payload=json.dumps({k:v for k,v in body.items() if k!='signature'},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    return hmac.new(secret.encode(),('agentrader-demo-recovery-lease-v1:'+payload).encode(),hashlib.sha256).hexdigest()


def replace_lease(source,target):
    # Windows readers may briefly deny FILE_SHARE_DELETE. Never truncate an
    # in-use lease or publish partial JSON; retry the atomic rename, bounded <1s.
    for attempt in range(8):
        try:os.replace(source,target);return
        except PermissionError:
            if attempt==7:raise
            time.sleep(.01*2**min(attempt,4))


def read_lease(database):
    try:
        raw=paths(database)[2].read_bytes()
        if len(raw)>8192:return None
        result=json.loads(raw)
        return result if isinstance(result,dict) else None
    except (OSError,ValueError):return None


def lock_held(path):
    try:
        with execution_lock(path):return False
    except ExecutionBusy:return True


def require_guardian(database,owner,exchange,limits,*,runtime_lock=Path('data/runtime.lock'),clock=time.time,pid=os.getpid):
    """Live independent OS lease, same DB/account/owner/risk and executor lock."""
    try:
        db,lock,_=paths(database);lease=read_lease(db)
        if (not lease or lease['schema']!='demo-recovery-guardian/1' or lease['state']!='ARMED'
                or lease['execute_demo'] is not True or type(lease['pid']) is not int or lease['pid']<=0
                or lease['pid']==pid() or not isinstance(lease['instance'],str) or len(lease['instance'])!=32
                or not lease['process_token'] or lease['process_token']!=process_token(lease['pid'])
                or lease['database']!=str(db) or lease['runtime_lock']!=str(Path(runtime_lock).resolve())
                or lease['owner']!=owner or lease['account_ref']!=account_ref(exchange)
                or not hmac.compare_digest(lease['signature'],lease_signature(lease,exchange))
                or lease['risk_profile_hash']!=profile_hash(limits)
                or not math.isfinite(lease['observed_at']) or not 0<=clock()-lease['observed_at']<=MAX_LEASE_AGE
                or not lock_held(lock)):
            raise ValueError()
        return lease['instance']
    except (ValueError,OSError,KeyError,TypeError):
        raise ValueError('INDEPENDENT_DEMO_GUARDIAN_REQUIRED') from None


def status(database,*,clock=time.time):
    lease=read_lease(database)
    if not lease:return dict(state='NOT_RUNNING',entry_ready=False)
    try:
        age=clock()-lease['observed_at']
        alive=math.isfinite(age) and 0<=age<=MAX_LEASE_AGE and lease['process_token'] is not None and lease['process_token']==process_token(lease['pid']) and lock_held(paths(database)[1])
        state='STOPPED' if lease['state']=='STOPPED' else lease['state'] if alive else 'STALE'
        return dict(state=state,entry_ready=bool(alive and lease['state']=='ARMED' and lease['execute_demo'] is True),
                    execute_demo=lease['execute_demo'],pid=lease['pid'],observed_at=lease['observed_at'],mode='RECOVERY_ONLY')
    except (OSError,ValueError,KeyError,TypeError):return dict(state='INVALID',entry_ready=False)


class RecoveryExchange:
    """Every mutation must match an existing session and durable V2 intent."""
    def __init__(self,exchange,store,session_id,execute):
        self._exchange,self.store,self.session_id,self.execute=exchange,store,session_id,execute
        self.config=exchange.config

    @property
    def offset_ms(self):return getattr(self._exchange,'offset_ms',0)

    def sync_time(self):return self._exchange.sync_time()
    def get(self,path,params=None):return self.request('GET',path,params)

    def request(self,method,path,params=None):
        if (method,path) not in allowed_requests():raise ValueError('RECOVERY_ENDPOINT_DENIED')
        if method=='GET':return self._exchange.get(path,params)
        if not self.execute:raise ValueError('RECOVERY_OBSERVATION_ONLY')
        sessions=[s for s in self.store.sessions() if s['id']==self.session_id]
        if len(sessions)!=1:raise ValueError('RECOVERY_SESSION_REQUIRED')
        s=sessions[0];plan=s['plan'];p=dict(params or {})
        if (s.get('engine')!='v2' or not plan.get('analysis_ref','').startswith('shadow-event:')
                or s['account_ref']!=account_ref(self._exchange)):
            raise ValueError('RECOVERY_SCOPE_MISMATCH')
        proposals=s['protections']+s.get('exits',[])
        if method=='DELETE':
            normal={s['entry_id']}|{v['params']['newClientOrderId'] for v in s.get('exits',[])}
            algos={v['params']['clientAlgoId'] for v in s['protections']}
            permitted=(path=='/fapi/v1/order' and set(p)=={'symbol','origClientOrderId'} and p['symbol']==s['symbol'] and p['origClientOrderId'] in normal
                       or path=='/fapi/v1/algoOrder' and set(p)=={'clientAlgoId'} and p['clientAlgoId'] in algos)
        elif method=='POST':
            permitted=any(v['path']==path and v['params']==p for v in proposals)
            side='SELL' if plan['direction']=='LONG' else 'BUY'
            ps='BOTH' if plan['position_mode']=='one-way' else plan['direction']
            permitted=permitted and p.get('symbol')==s['symbol'] and p.get('side')==side and p.get('positionSide')==ps
            if path=='/fapi/v1/order':
                permitted=permitted and p.get('type')=='MARKET' and 0<number(p.get('quantity','0'))<=number(s['prepared']['quantity'])
                if ps=='BOTH':permitted=permitted and p.get('reduceOnly')=='true'
            elif path=='/fapi/v1/algoOrder':
                permitted=permitted and p.get('type') in ('STOP_MARKET','TAKE_PROFIT_MARKET') and p.get('closePosition')=='true'
            else:permitted=False
            cid=p.get('newClientOrderId',p.get('clientAlgoId'));intent=self.store.intent(cid)
            permitted=permitted and bool(intent and intent['state']=='SUBMITTING' and intent['path']==path and json.loads(intent['params'])==p)
        else:permitted=False
        if not permitted:raise ValueError('RECOVERY_NEW_ENTRY_OR_SETTINGS_DENIED')
        return self._exchange.request(method,path,p)


def recover_once(store,owner,exchange,limits,*,execute=False,runner_factory=None):
    """Caller owns runtime.lock. Read-only reconciliation precedes every mutation."""
    from agentrader.bot.plans import PlanService
    from agentrader.bot.v2_runner import V2Runner
    service=PlanService(store,owner);factory=runner_factory or V2Runner
    selected=[s for s in store.sessions() if s.get('engine')=='v2' and s.get('plan',{}).get('analysis_ref','').startswith('shadow-event:')]
    foreign=[s for s in store.sessions() if s not in selected]
    if foreign:
        return dict(state='UNSUPPORTED_ACTIVE_SESSION',sessions=[],entry_ready=False)
    # A crash between claim and session persistence cannot have sent an entry:
    # POST is strictly later. Keep its reservation/authority blocked for review.
    orphans=store.db.execute("SELECT plan_id,version FROM plan_versions p WHERE state IN ('EXECUTING','MANAGING','NEEDS_REVIEW') AND json_extract(body,'$.analysis_ref') LIKE 'shadow-event:%' AND NOT EXISTS (SELECT 1 FROM managed_sessions m WHERE m.session_id=p.session_id)").fetchall()
    if orphans:
        if execute:store.halt('Guardian: oturum kaydı eksik; giriş ve rezerv uzlaştırılmalı.')
        return dict(state='ORPHAN_PLAN_REVIEW_REQUIRED',sessions=[],entry_ready=False)
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='risk_reservations'").fetchone():
        orphan_reserve=store.db.execute("SELECT 1 FROM risk_reservations r WHERE state!='RELEASED' AND NOT EXISTS (SELECT 1 FROM managed_sessions m WHERE m.session_id=r.reservation_id) LIMIT 1").fetchone()
        if orphan_reserve:
            if execute:store.halt('Guardian: kullanılmamış rezerv uzlaştırılmalı; otomatik serbest bırakılmaz.')
            return dict(state='ORPHAN_RESERVATION_REVIEW_REQUIRED',sessions=[],entry_ready=False)
    if not selected:return dict(state='IDLE',sessions=[],entry_ready=True)
    rows=[]
    for s in selected:
        try:
            if s['account_ref']!=account_ref(exchange):raise ValueError('RECOVERY_ACCOUNT_MISMATCH')
            wrapped=RecoveryExchange(exchange,store,s['id'],execute)
            runner=factory(service,wrapped,limits)
            if execute:
                store.halt('Guardian devraldı; yeni girişler kapalı, mevcut pozisyon korunuyor.')
                service.cancel(s['plan_ref']['plan_id'],s['plan_ref']['version'],owner)
            barrier=runner.manage(s['id'],execute=False)
            active=any(v['id']==s['id'] for v in store.sessions())
            result=runner.manage(s['id'],execute=True) if execute and active else barrier
            store.runtime_health(s['id'],result,time.time())
            rows.append(dict(session_id=s['id'],state=result['state'],executed=execute))
        except Exception:
            # Never export signed URLs, credentials or raw account payloads.
            if execute:store.halt('Guardian doğrulaması eksik; yeni giriş kapalı, yerel inceleme gerekiyor.')
            rows.append(dict(session_id=s['id'],state='NEEDS_REVIEW',error_code='RECOVERY_RECONCILIATION_REQUIRED',executed=False))
    return dict(state='NEEDS_REVIEW' if any(v['state']=='NEEDS_REVIEW' for v in rows) else 'RECOVERING',sessions=rows,entry_ready=False)


def run_guardian(database,owner,exchange_factory,limits,*,execute=False,interval=1,iterations=0,
                 runtime_lock=Path('data/runtime.lock'),clock=time.time,sleep=time.sleep,emit=None):
    """Separate process only. No financial activity until execute=True is explicit."""
    if type(interval) is not int or not 1<=interval<=2 or type(iterations) is not int or iterations<0:
        raise ValueError('Guardian interval 1–2 ve iterations >=0 olmalı.')
    database,guardian_lock,lease_path=paths(database)
    with execution_lock(guardian_lock):
        exchange=exchange_factory();identity=account_ref(exchange)
        lease=dict(schema='demo-recovery-guardian/1',instance=secrets.token_hex(16),pid=os.getpid(),owner=owner,
                   process_token=process_token(os.getpid()),
                   database=str(database),runtime_lock=str(Path(runtime_lock).resolve()),account_ref=identity,
                   risk_profile_hash=profile_hash(limits),execute_demo=execute)
        def pulse(state):
            body={**lease,'state':state,'observed_at':clock()};tmp=Path(str(lease_path)+'.'+lease['instance']+'.tmp')
            body['signature']=lease_signature(body,exchange)
            try:
                with tmp.open('w',encoding='utf-8') as stream:
                    json.dump(body,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
                replace_lease(tmp,lease_path)
            finally:
                if tmp.exists():tmp.unlink()
        turn=0;last='STARTING' if execute else 'OBSERVING'
        try:
            if lease['process_token'] is None:raise ValueError('RECOVERY_PROCESS_IDENTITY_UNAVAILABLE')
            pulse('STARTING')
            exchange.sync_time()
            if exchange.get('/fapi/v1/accountConfig').get('canTrade') is not True:
                raise ValueError('DEMO_RECOVERY_ACCOUNT_NOT_READY')
            while iterations==0 or turn<iterations:
                pulse(last)
                try:
                    with execution_lock(runtime_lock):
                        from agentrader.shared.state import StateStore
                        store=StateStore(database)
                        try:
                            pulse('RECOVERING' if execute else 'OBSERVING')
                            result=recover_once(store,owner,exchange,limits,execute=execute)
                        finally:store.close()
                        last=('ARMED' if execute else 'OBSERVING') if result['state']=='IDLE' else result['state']
                        pulse(last)
                        if emit:emit(result)
                except ExecutionBusy:pass
                turn+=1
                if iterations and turn>=iterations:break
                sleep(interval)
        finally:pulse('STOPPED')
