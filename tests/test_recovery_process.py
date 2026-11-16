"""Actual killed executor + independent guardian + shared loopback fake exchange."""
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from agentrader.shared.exchange import ExchangeError
from agentrader.bot.recovery_guardian import read_lease
from test_v2_runner import ExecutionExchange
from test_v2_preflight import SnapshotExchange

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'tests/helpers/recovery_process.py'


class RecoveryProcessTests(unittest.TestCase):
    def scenario(self,stage,*,pending=False,partial=False,expected='MANAGING'):
        with tempfile.TemporaryDirectory(prefix='guardian-crash-') as folder:
            folder=Path(folder);db=folder/'execution.db';marker=folder/'crash-stage'
            x=ExecutionExchange();x.limit_pending=pending;x.partial=partial;mutex=threading.Lock();flat=SnapshotExchange()
            class Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    try:
                        with mutex:
                            if data['method']=='GET':
                                try:result={'canTrade':True,'multiAssetsMargin':True} if data['path']=='/fapi/v1/accountConfig' else x.get(data['path'],data['params'])
                                except AssertionError:
                                    flat.data['/fapi/v1/assetIndex']['time']=int(time.time()*1000)
                                    result=flat.get(data['path'],data['params'])
                            else:result=x.request(data['method'],data['path'],data['params'])
                        value=dict(result=result)
                    except ExchangeError as exc:value=dict(error=True,code=exc.code,delivery_status=exc.delivery_status)
                    self.send_response(200);self.end_headers();self.wfile.write(json.dumps(value).encode())
                def log_message(self,*a):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{server.server_port}';children=[];logs=[]
            try:
                def launch(role,extra=None):
                    output=(folder/(role+'.log')).open('w');logs.append(output)
                    child=subprocess.Popen([sys.executable,str(HELPER),role,'--database',str(db),'--url',url,*(extra or [])],
                        cwd=folder,stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    children.append(child);return child
                def wait(predicate,seconds=12):
                    deadline=time.monotonic()+seconds
                    while time.monotonic()<deadline:
                        if predicate():return
                        time.sleep(.04)
                    for output in logs:output.flush()
                    details='\n'.join(p.read_text() for p in folder.glob('*.log'))
                    self.fail('Timed out at '+stage+'\n'+details)
                guardian=launch('guardian')
                wait(lambda:(read_lease(db) or {}).get('state')=='ARMED')
                executor=launch('executor',['--stage',stage,'--marker',str(marker)])
                wait(marker.exists)
                # Writer is still alive and owns runtime.lock: no guardian takeover.
                self.assertIsNone(executor.poll());self.assertIsNone(guardian.poll())
                before=list(x.calls);time.sleep(.15);self.assertEqual(x.calls,before)
                executor.kill();executor.wait(timeout=10)
                crashed_at=time.time()
                def recovered():
                    if expected.startswith('ORPHAN') or expected=='NEEDS_REVIEW':
                        return (read_lease(db) or {}).get('state')==expected
                    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as state:
                        row=state.execute('SELECT body,active FROM managed_sessions LIMIT 1').fetchone()
                        if not row:return False
                        body=json.loads(row[0]);health=state.execute('SELECT value FROM control WHERE name=?',('runtime_health:'+body['id'],)).fetchone()
                        if not health or json.loads(health[0])['observed_at']<crashed_at:return False
                        return (not row[1]) if expected=='CLOSED' else json.loads(row[0]).get('status')=='PROTECTED'
                wait(recovered)
                time.sleep(.12)
                entries=[c for c in x.calls if c[0]=='POST' and c[1]=='/fapi/v1/order']
                algos=[c for c in x.calls if c[0]=='POST' and c[1]=='/fapi/v1/algoOrder']
                self.assertEqual(len(entries),0 if stage in ('after_reserve','after_claim','after_session','before_delivery') else 1)
                self.assertEqual(len(algos),2 if expected=='MANAGING' else 0)
                self.assertEqual(len({c[2]['clientAlgoId'] for c in algos}),len(algos))
                with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as state:
                    self.assertIsNotNone(state.execute("SELECT 1 FROM control WHERE name='halt'").fetchone())
                    if expected=='NEEDS_REVIEW':
                        self.assertEqual(state.execute('SELECT state FROM intents LIMIT 1').fetchone()[0],'SUBMITTING')
                    if expected.startswith('ORPHAN'):
                        self.assertEqual(state.execute('SELECT COUNT(*) FROM managed_sessions').fetchone()[0],0)
                self.assertTrue(guardian.poll() is None)
            finally:
                for child in children:
                    if child.poll() is None:child.kill()
                    child.wait(timeout=10)
                for output in logs:output.close()
                server.shutdown();server.server_close();thread.join(3)

    def test_kill_after_risk_reservation_never_releases_or_reuses_it(self):self.scenario('after_reserve',expected='ORPHAN_RESERVATION_REVIEW_REQUIRED')
    def test_kill_after_claim_blocks_orphan_plan(self):self.scenario('after_claim',expected='ORPHAN_PLAN_REVIEW_REQUIRED')
    def test_kill_after_session_save_retires_proven_unsent_entry(self):self.scenario('after_session',expected='CLOSED')
    def test_kill_before_delivery_never_reposts_ambiguous_intent(self):self.scenario('before_delivery',expected='NEEDS_REVIEW')
    def test_kill_after_pending_entry_acceptance_cancels_without_reentry(self):self.scenario('entry_accepted',pending=True,expected='CLOSED')
    def test_kill_after_fill_acceptance_installs_two_native_protections(self):self.scenario('entry_accepted')
    def test_kill_after_partial_fill_cancels_remainder_and_protects(self):self.scenario('entry_accepted',partial=True)
    def test_kill_after_first_protection_acceptance_does_not_duplicate_it(self):self.scenario('protection_accepted')
    def test_kill_after_native_protection_keeps_both_orders(self):self.scenario('protected')
