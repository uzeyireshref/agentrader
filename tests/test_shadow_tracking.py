from contextlib import closing
import copy,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from scripts.chart.run_chart_p7 import Harness
from agentrader.integration.shadow_tracking import ShadowTracking,ShadowWorker,ShadowError
from agentrader.chart.chart_bindings import BindingService
from agentrader.chart.drawings.service import DrawingConflict
from agentrader.migrations import connect


class ShadowTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness();self.addCleanup(self.h.close)
        self.s=ShadowTracking(self.h.db,'fixture',clock=lambda:self.h.clock[1],monotonic=lambda:self.h.clock[0])
        self.b=self.h.b

    def start(self):
        return self.s.command('main','binding',self.b['revision'],self.b['definition_hash'],'start',3600)

    def run_record(self):return self.s.runs()[0]
    def process(self,n=0,**kw):return self.s.process(self.run_record(),self.h.context(n,**kw),'boot')
    def events(self):return self.s.status('main','binding')['events']

    def test_initial_seed_never_emits_even_if_rule_matches(self):
        self.start();r=self.process(0,close='99.8',high='100',low='99.4')
        self.assertEqual(r['reason'],'SEEDED_NO_HISTORICAL_SIGNAL');self.assertFalse(self.events())

    def test_touch_is_durable_single_latched_and_has_reason_and_evidence(self):
        self.start();run=self.run_record();self.process()
        c=self.h.context(1,close='99.8',high='100',low='99.4')
        r=self.s.process(run,c,'boot');self.assertTrue(r['created']);self.assertFalse(r['order_authority'])
        self.assertFalse(self.s.process(run,c,'boot')['created']);self.assertEqual(len(self.events()),1)
        e=self.events()[0];self.assertEqual(e['kind'],'TOUCH');self.assertEqual(e['reason']['closed_price'],'99.8')
        with closing(connect(self.h.db)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM app_chart_local_intents').fetchone()[0],0)
            self.assertIn('eligibility',json.loads(db.execute('SELECT evidence FROM app_shadow_events').fetchone()[0]))
        with self.assertRaisesRegex(ShadowError,'EXPLICIT_REBIND'):self.start()

    def test_start_retry_does_not_extend_ttl(self):
        a=self.start()['run'];self.h.clock[0]+=1;self.h.clock[1]+=1;b=self.start()['run']
        self.assertEqual(a['expires_at'],b['expires_at']);self.assertEqual(a['binding_revision'],b['binding_revision'])

    def test_transaction_failure_rolls_back_event_and_checkpoint(self):
        self.start();self.process();run=self.run_record();before=self.s.status('main','binding')['run']['checkpoint']
        def fault(_):raise RuntimeError('injected crash')
        c=self.h.context(1,close='99.8',high='100',low='99.4')
        with self.assertRaises(RuntimeError):self.s.process(run,c,'boot',_fault=fault)
        self.assertFalse(self.events());self.assertEqual(self.s.status('main','binding')['run']['checkpoint'],before)
        self.assertTrue(self.s.process(run,c,'boot')['created'])

    def test_revision_change_stops_tracking_without_signal(self):
        self.start();run=self.run_record();self.h.edit()
        self.assertEqual(self.s.process(run,self.h.context(1),'boot')['state'],'STOPPED');self.assertFalse(self.events())
        with self.assertRaises(DrawingConflict):self.start()

    def test_source_or_stale_evidence_blocks_and_recovery_seeds(self):
        for mutation in (lambda c:c['identity'].update(environment='live_public'),lambda c:c['timing'].update(state='STALE')):
            with self.subTest(mutation=mutation):
                self.start();self.process();c=self.h.context(1,close='99.8',high='100',low='99.4');mutation(c)
                self.assertEqual(self.s.process(self.run_record(),c,'boot')['state'],'WAITING_DATA')
                self.assertEqual(self.process(1)['reason'],'SEEDED_NO_HISTORICAL_SIGNAL');self.assertFalse(self.events())

    def test_restart_and_epoch_change_skip_missed_closes(self):
        self.start();self.process();run=self.run_record();c=self.h.context(1,close='99.8',high='100',low='99.4')
        self.assertEqual(self.s.process(run,c,'new-boot')['reason'],'SEEDED_NO_HISTORICAL_SIGNAL')
        c=self.h.context(2,close='99.8',high='100',low='99.4');c['stream_epoch']='b'*32;self.h.proof(c)
        self.assertEqual(self.s.process(run,c,'new-boot')['reason'],'SEEDED_NO_HISTORICAL_SIGNAL');self.assertFalse(self.events())

    def test_gap_resync_is_not_a_fresh_signal(self):
        self.start();self.process();r=self.process(3,close='99.8',high='100',low='99.4')
        self.assertEqual(r['reason'],'RESYNC_NO_HISTORICAL_SIGNAL');self.assertFalse(self.events())

    def test_pause_resume_does_not_extend_ttl_and_seeds_current_close(self):
        a=self.start()['run'];self.process()
        self.s.command('main','binding',1,self.b['definition_hash'],'pause')
        self.assertEqual(self.s.runs(),[])
        self.s.command('main','binding',1,self.b['definition_hash'],'resume')
        self.assertEqual(self.process(1,close='99.8',high='100',low='99.4')['reason'],'SEEDED_NO_HISTORICAL_SIGNAL')
        self.assertEqual(self.s.status('main','binding')['run']['expires_at'],a['expires_at']);self.assertFalse(self.events())

    def test_ttl_expires_without_event(self):
        self.start();run=self.run_record();self.h.clock[0]+=3601;self.h.clock[1]+=3601
        self.assertEqual(self.s.process(run,self.h.context(1),'boot')['state'],'EXPIRED');self.assertFalse(self.events())

    def test_wall_clock_jump_fails_closed(self):
        self.start();self.process();self.h.clock[1]+=1
        self.assertEqual(self.process(1)['reason'],'CLOCK_UNTRUSTED');self.assertFalse(self.events())

    def test_same_semantic_close_changed_data_stops_for_review(self):
        self.start();self.process();c=self.h.context(0,close='97')
        self.assertEqual(self.s.process(self.run_record(),c,'boot')['reason'],'SEMANTIC_PAYLOAD_CONFLICT')

    def test_wrong_owner_and_unsupported_observe_rule_cannot_start(self):
        with self.assertRaises(Exception):ShadowTracking(self.h.db,'other').command('main','binding',1,self.b['definition_hash'],'start')
        d=self.b['definition'];b=self.h.s.save_binding('main','observe','obs',0,{k:d['target'][k] for k in ('type','object_id','revision')},'BTCUSDT','15m','LINEAR',d['grid']['times'],None,d['query'],{**d['rule'],'kind':'observe','tolerance':'0'})
        with self.assertRaisesRegex(ShadowError,'UNSUPPORTED'):self.s.command('main','observe',1,b['definition_hash'],'start')

    def test_approach_and_strict_cross_share_canonical_candidate(self):
        for kind,close,high,low,tolerance,expected in [('approach','99.5','99.6','99.4','1','APPROACH'),('close_cross','100.1','100.2','100','0','CLOSE_CROSS')]:
            d=self.b['definition'];bid=kind;b=self.h.s.save_binding('main',bid,bid,0,{k:d['target'][k] for k in ('type','object_id','revision')},'BTCUSDT','15m','LINEAR',d['grid']['times'],None,d['query'],{**d['rule'],'kind':kind,'tolerance':tolerance})
            self.s.command('main',bid,1,b['definition_hash'],'start');run=next(r for r in self.s.runs() if r['binding_id']==bid)
            self.s.process(run,self.h.context(0),'boot');self.assertTrue(self.s.process(run,self.h.context(1,close=close,high=high,low=low),'boot')['created'])
            self.assertEqual(self.s.status('main',bid)['events'][0]['kind'],expected)

    def test_worker_acquires_feed_without_browser_and_releases_it(self):
        self.start();hub=Mock();hub.binding_context.return_value=self.h.context(0)
        worker=ShadowWorker(self.s,hub);worker.tick();hub.acquire.assert_called_once_with('BTCUSDT','15m')
        self.s.command('main','binding',1,self.b['definition_hash'],'pause');worker.tick();hub.release.assert_called_once()

    def test_one_process_lease_blocks_second_worker(self):
        first=ShadowWorker(self.s,Mock());second=ShadowWorker(self.s,Mock());first.start()
        try:
            self.assertFalse(second.start());self.assertIsNone(second.thread)
            self.assertEqual(second.error,'SHADOW_WORKER_ALREADY_RUNNING')
        finally:first.close()
        self.assertFalse(first.thread.is_alive())
