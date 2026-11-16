from contextlib import closing
import copy,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from scripts.chart.run_chart_p7 import Harness
from agentrader.integration.signal_previews import SignalPreviews,PreviewError
from agentrader.integration.shadow_tracking import ShadowTracking
from agentrader.bot.risk import RiskLimits
from agentrader.chart.drawings.service import DrawingConflict,DrawingNotFound
from agentrader.migrations import connect
from agentrader.bot.plan_v2 import validate_v2
from test_orders import SYMBOL


def inputs(**changes):return dict(direction='LONG',entry_price='100',stop='98',target='104',notional='60',leverage=2,margin_mode='ISOLATED',position_mode='one-way',max_drift_bps='25',ttl_seconds=120,**changes)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.h=Harness();self.addCleanup(self.h.close);self.clock=self.h.clock
        self.shadow=ShadowTracking(self.h.db,'fixture',clock=lambda:self.clock[1],monotonic=lambda:self.clock[0])
        b=self.h.b;self.shadow.command('main','binding',1,b['definition_hash'],'start')
        run=self.shadow.runs()[0];self.shadow.process(run,self.h.context(0),'boot')
        self.context=self.h.context(1,close='99.8',high='100',low='99.4');self.shadow.process(run,self.context,'boot')
        self.event=self.shadow.status('main','binding')['events'][0]['event_id']
        self.hub=SimpleNamespace(binding_context=lambda *a:copy.deepcopy(self.context))
        self.public=Mock();self.symbol=copy.deepcopy(SYMBOL);self.symbol['contractType']='PERPETUAL'
        def get(path,params=None):
            if path.endswith('exchangeInfo'):return dict(symbols=[self.symbol])
            if path.endswith('premiumIndex'):return dict(symbol='BTCUSDT',markPrice='100',time=int(self.clock[1]*1000))
            if path.endswith('/time'):return dict(serverTime=int(self.clock[1]*1000))
            raise AssertionError('Unexpected public request')
        self.public.get.side_effect=get
        self.service=SignalPreviews(self.h.db,'fixture',self.hub,public_factory=lambda:self.public,limits=RiskLimits(),clock=lambda:self.clock[1],monotonic=lambda:self.clock[0])

    def create(self,p=None,version=0):return self.service.create('main',self.event,version,inputs() if p is None else p)

    def test_valid_v2_draft_has_no_authority_and_no_execution_tables(self):
        r=self.create();validate_v2(r['plan'])
        self.assertEqual(r['state'],'PREVIEW_ONLY');self.assertFalse(r['order_authority']);self.assertFalse(r['execution_eligible'])
        self.assertEqual(r['account_preflight'],'NOT_CHECKED');self.assertEqual(r['approval_state'],'NOT_REQUESTED')
        self.assertGreater(float(r['estimates']['quantity']),0);self.assertLessEqual(float(r['estimates']['stop_loss_with_cost_reserve']),5)
        self.assertEqual(r['plan']['analysis_ref'],'shadow-event:'+self.event)
        self.public.request.assert_not_called()
        with closing(connect(self.h.db)) as db:
            names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertFalse({'intents','plans','risk_reservations'}&names)

    def test_same_event_and_parameters_are_idempotent_without_extending_expiry(self):
        a=self.create();self.clock[0]+=1;self.clock[1]+=1;self.public.reset_mock();b=self.create()
        self.assertEqual((a['version'],a['expires_at']),(b['version'],b['expires_at']));self.public.get.assert_not_called()

    def test_changed_parameters_create_explicit_version_and_old_is_superseded(self):
        a=self.create();p=inputs();p['target']='105';b=self.create(p,1)
        self.assertEqual(b['version'],2);self.assertEqual(a['plan']['plan_id'],b['plan']['plan_id'])
        self.assertEqual(self.service.show('main',self.event,1)['state'],'SUPERSEDED')
        p['target']='106'
        with self.assertRaises(DrawingConflict):self.create(p,0)

    def test_expired_preview_does_not_renew_on_retry(self):
        self.create();self.clock[0]+=121;self.clock[1]+=121
        self.assertEqual(self.create()['state'],'EXPIRED')

    def test_event_age_and_revision_changes_block_new_previews(self):
        self.clock[0]+=301;self.clock[1]+=301
        with self.assertRaisesRegex(PreviewError,'EVENT_EXPIRED'):self.create()

    def test_binding_edit_invalidates_existing_preview(self):
        self.create();self.h.edit()
        self.assertEqual(self.service.show('main',self.event)['state'],'INVALIDATED')
        with self.assertRaisesRegex(PreviewError,'REVISION_CHANGED'):self.create()

    def test_stale_source_and_gap_data_block_creation_and_existing_view(self):
        self.create();self.context['timing']['state']='STALE'
        self.assertEqual(self.service.show('main',self.event)['state'],'BLOCKED')
        with self.assertRaisesRegex(PreviewError,'DATA_NOT_FRESH'):self.create()

    def test_independent_budget_and_stop_loss_caps_cannot_be_overridden(self):
        for change in (dict(notional='101'),dict(stop='50')):
            p=inputs();p.update(change)
            with self.subTest(change=change),self.assertRaisesRegex(PreviewError,'RISK_LIMIT'):self.create(p)

    def test_filters_minimum_notional_tick_and_invalid_prices_fail(self):
        for change in (dict(notional='1'),dict(entry_price='100.01'),dict(stop='101'),dict(target='99'),dict(notional='NaN'),dict(leverage=True)):
            p=inputs();p.update(change)
            with self.subTest(change=change),self.assertRaises(PreviewError):self.create(p)

    def test_short_and_hedge_plan_remain_explicit_drafts(self):
        p=inputs();p.update(direction='SHORT',stop='102',target='96',position_mode='hedge')
        r=self.create(p);self.assertEqual(r['plan']['direction'],'SHORT');self.assertEqual(r['plan']['position_mode'],'hedge');validate_v2(r['plan'])

    def test_corrupt_event_evidence_is_rejected(self):
        with closing(connect(self.h.db)) as db,db:
            row=db.execute('SELECT body FROM app_shadow_events WHERE event_id=?',(self.event,)).fetchone();e=json.loads(row[0]);e['closed_price']='1'
            db.execute('UPDATE app_shadow_events SET body=? WHERE event_id=?',(json.dumps(e),self.event))
        with self.assertRaisesRegex(PreviewError,'INTEGRITY'):self.create()

    def test_changed_risk_profile_invalidates_preview(self):
        self.create();self.service.fixed_limits=RiskLimits(max_notional=__import__('decimal').Decimal('80'))
        self.assertEqual(self.service.show('main',self.event)['state'],'INVALIDATED')

    def test_other_owner_and_workspace_cannot_read_preview(self):
        self.create()
        with self.assertRaises(DrawingNotFound):SignalPreviews(self.h.db,'other',self.hub).show('main',self.event)
        with self.assertRaises(DrawingNotFound):self.service.show('other',self.event)

    def test_quote_failure_and_tampered_stored_plan_do_not_look_ready(self):
        self.public.get.side_effect=ValueError('bad quote')
        with self.assertRaisesRegex(PreviewError,'QUOTE_UNAVAILABLE'):self.create()
        self.setUpPublicForTest()

    def setUpPublicForTest(self):
        # Restore the minimal public responses for a separate integrity assertion.
        self.public.get.side_effect=lambda path,params=None:dict(symbols=[self.symbol]) if path.endswith('exchangeInfo') else dict(serverTime=1000000) if path.endswith('/time') else dict(symbol='BTCUSDT',markPrice='100',time=1000000)
        self.create()
        with closing(connect(self.h.db)) as db,db:
            row=db.execute('SELECT body FROM app_signal_previews').fetchone();body=json.loads(row[0]);body['plan']['stop']='1';db.execute('UPDATE app_signal_previews SET body=?',(json.dumps(body),))
        self.assertEqual(self.service.show('main',self.event)['state'],'INVALIDATED')


    def test_concurrent_same_event_creates_one_draft(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.create(),range(2)))
        self.assertEqual([r['version'] for r in results],[1,1])
        with closing(connect(self.h.db)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM app_signal_previews').fetchone()[0],1)

    def test_no_client_authority_or_auto_direction_is_accepted(self):
        p=inputs();p['order_authority']=True
        with self.assertRaises(PreviewError):self.create(p)
        p=inputs();p['direction']='AUTO'
        with self.assertRaises(PreviewError):self.create(p)
