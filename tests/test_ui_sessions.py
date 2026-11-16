"""G6: transient reports use synthetic data and isolated SQLite, never execution."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agentrader.chart.ui_sessions import UISessions, UISessionStore, UIError, snapshot
from agentrader.chart.chart_context import ChartContext
from agentrader.chart.drawings.service import DrawingService
from agentrader.migrations import migrate
from scripts.integration.chart_tool_matrix_cases import drawing_cases

ROOT=Path(__file__).resolve().parents[1]


class UISessionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.database=Path(self.temp.name)/'app.db';migrate(self.database)
        self.mono=[100.];self.wall=[1800000000.]
        self.store=UISessionStore(clock=lambda:self.wall[0],monotonic=lambda:self.mono[0])
        self.service=UISessions(self.database,'owner',store=self.store)
        self.key='a'*64
        self.value=json.loads((ROOT/'frontend/tests/fixtures/ui-session-g6.json').read_text())

    def packet(self,sequence=1,**changes):
        return dict(schema_version='chart-ui-session/1',server_instance_id=self.store.server_instance_id,
                    sequence=sequence,client_time_ms=1800000000000,visibility='visible',client_status='CONNECTED',
                    snapshot=copy.deepcopy(self.value)) | changes

    def put(self,sequence=1,sid='tab-a',**changes):
        return self.service.put('main',sid,self.key,self.packet(sequence,**changes))

    def error(self,code,fn):
        with self.assertRaises(UIError) as caught:fn()
        self.assertEqual(caught.exception.code,code)

    def test_two_tabs_owner_workspace_isolation_and_no_database_writes(self):
        before=self.database.read_bytes();self.put();self.value['theme']='light';self.put(sid='tab-b')
        self.assertEqual(self.service.show('main','tab-a')['snapshot']['theme'],'dark')
        self.assertEqual(self.service.show('main','tab-b')['snapshot']['theme'],'light')
        other=UISessions(self.database,'another-owner',store=self.store)
        self.assertEqual(other.list('main')['sessions'],[])
        self.assertEqual(other.show('main','tab-a')['reason'],'MISSING_OR_HIDDEN')
        self.assertEqual(self.service.show('other','tab-a')['reason'],'MISSING_OR_HIDDEN')
        self.assertEqual(len(self.service.list('main')['sessions']),2)
        self.assertTrue(all('snapshot' not in row for row in self.service.list('main')['sessions']))
        encoded=json.dumps(self.service.list('main'))+json.dumps(self.service.show('main','tab-a'))
        self.assertNotIn(self.key,encoded);self.assertNotIn('key_hash',encoded)
        self.assertEqual(self.database.read_bytes(),before)

    def test_monotonic_lease_duplicate_does_not_extend_and_expired_cannot_revive(self):
        self.put();self.wall[0]+=1e6;self.mono[0]+=29
        self.assertTrue(self.put()['duplicate'])
        self.assertEqual(self.service.show('main','tab-a')['state'],'READY')
        self.mono[0]+=1
        result=self.service.show('main','tab-a');self.assertEqual(result['reason'],'EXPIRED')
        self.assertNotIn('snapshot',result)
        self.error('UI_SESSION_EXPIRED',lambda:self.put(2))
        self.put(sid='new-tab');self.assertEqual(self.service.show('main','new-tab')['state'],'READY')

    def test_hidden_offline_closed_redact_and_old_packets_cannot_reopen(self):
        self.put();self.put(2,visibility='hidden')
        self.assertEqual(self.service.list('main')['sessions'],[])
        self.assertEqual(self.service.show('main','tab-a')['reason'],'MISSING_OR_HIDDEN')
        self.error('UI_SESSION_SEQUENCE_CONFLICT',lambda:self.put())
        self.mono[0]+=.5;self.put(3)
        self.put(4,client_status='OFFLINE');self.assertEqual(self.service.show('main','tab-a')['reason'],'OFFLINE')
        self.put(5,client_status='CLOSED')
        self.assertNotIn('snapshot',self.service.show('main','tab-a'))
        self.error('UI_SESSION_CLOSED',lambda:self.put(6))
        self.put(3,sid='close-before-first',client_status='CLOSED',visibility='hidden')
        self.error('UI_SESSION_SEQUENCE_CONFLICT',lambda:self.put(sid='close-before-first'))

    def test_out_of_order_conflicting_key_rate_limits_and_epoch(self):
        self.put()
        self.error('UI_SESSION_RATE_LIMIT',lambda:self.put(2))
        self.mono[0]+=.5;self.put(3)
        self.error('UI_SESSION_SEQUENCE_CONFLICT',lambda:self.put(2))
        self.value['theme']='light';self.error('UI_SESSION_SEQUENCE_CONFLICT',lambda:self.put(3))
        self.error('UI_PUBLISHER_MISMATCH',lambda:self.service.put('main','tab-a','b'*64,self.packet(4)))
        self.error('UI_PUBLISHER_KEY_REQUIRED',lambda:self.service.put('main','tab-c','bad',self.packet()))
        self.error('UI_SESSION_UNKNOWN',lambda:self.put(2,sid='unknown'))
        restarted=UISessions(self.database,'owner')
        self.error('UI_SESSION_SERVER_RESTARTED',lambda:restarted.put('main','tab-a',self.key,self.packet(4)))

    def test_capacity_bounded_and_retired_rows_evicted_without_accepting_delayed_sequence(self):
        self.store.max_sessions=2;self.put();self.put(sid='tab-b')
        self.error('UI_SESSION_LIMIT',lambda:self.put(sid='tab-c'))
        self.put(2,client_status='CLOSED');self.put(sid='tab-c')
        self.assertEqual(len(self.store.rows),2)
        self.error('UI_SESSION_EXPIRED',lambda:self.put(3))
        self.error('UI_SESSION_EXPIRED',lambda:self.put())

    def test_exact_hover_and_schema_validation_rejects_stack_and_nonfinite_values(self):
        self.assertEqual(snapshot(self.value)['crosshair']['hover_candle']['open'],'100.00')
        paths=[('viewport','logical_range',dict(**{'from':float('nan'),'to':1})),
               ('viewport','price_range',dict(**{'from':'Infinity','to':'1'})),
               ('viewport','time_range',dict(**{'from':1800000000000,'to':1800000900000})),
               ('crosshair','price',1.25),('crosshair','time',True),
               ('panels','pane_weights',dict(price=float('inf'),volume=1,rsi=1,atr=1,macd=1)),
               ('history','undo_targets',[dict(drawing_id='x',revision=1,before={'secret':'stack'})])]
        for group,key,value in paths:
            with self.subTest(group=group,key=key):
                bad=copy.deepcopy(self.value);bad[group][key]=value
                with self.assertRaises(UIError):snapshot(bad)
        bad=copy.deepcopy(self.value);bad['crosshair']['hover_candle']['time']+=900
        with self.assertRaises(UIError):snapshot(bad)

    def test_deleted_foreign_and_other_symbol_refs_reconciled_without_mutating_report(self):
        drawings=DrawingService(self.database,'owner');geometry=drawing_cases()[0]['geometry']
        own=drawings.create('main','own',geometry)
        foreign=DrawingService(self.database,'other').create('main','foreign',geometry)
        eth=drawings.create('main','eth',{**geometry,'symbol':'ETHUSDT'})
        self.value['selection']['drawing_ids']=[own['drawing_id'],foreign['drawing_id'],eth['drawing_id']]
        self.value['history'].update(can_undo=True,undo_targets=[dict(drawing_id=own['drawing_id'],revision=1)])
        self.put();before=self.database.read_bytes();view=self.service.show('main','tab-a')
        self.assertEqual(view['snapshot']['selection']['drawing_ids'],[own['drawing_id']])
        self.assertTrue(view['selection_reconciled'])
        self.assertTrue(view['snapshot']['history']['undo_targets'][0]['revision_matches'])
        self.assertEqual(self.database.read_bytes(),before)
        drawings.update(own['drawing_id'],'delete-own',1,deleted=True)
        view=self.service.show('main','tab-a');self.assertEqual(view['snapshot']['selection']['drawing_ids'],[])
        self.assertTrue(view['snapshot']['history']['undo_targets'][0]['target_deleted'])
        self.assertFalse(view['snapshot']['history']['undo_targets'][0]['revision_matches'])

    def test_explicit_ui_context_is_independent_of_market_and_saved_profile(self):
        hub=SimpleNamespace(binding_context=lambda *args:None)
        context=ChartContext(self.database,'owner',hub,ui_sessions=self.service)
        plain=context.read('main');self.assertEqual(plain['ui']['reason'],'UI_SESSION_NOT_SELECTED')
        self.value['theme']='light';self.value['market']['symbol']='ETHUSDT';self.put()
        a=context.read('main',symbol='BTCUSDT',interval='15m',ui_session_id='tab-a')
        self.assertFalse(a['ui']['market_matches_requested'])
        self.assertEqual(a['persistent_view']['body']['view']['theme'],'dark')
        self.assertEqual(a['ui']['snapshot']['theme'],'light')
        self.mono[0]+=1;self.put(2)
        b=context.read('main',symbol='BTCUSDT',interval='15m',ui_session_id='tab-a')
        self.assertEqual(a['context_id'],b['context_id']);self.assertNotEqual(a['ui_context_id'],b['ui_context_id'])
        self.assertFalse(b['order_authority']);self.assertFalse(b['ui']['order_authority'])

    def test_http_auth_cookie_origin_bounds_and_context_cannot_bypass_auth(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.api.session import cookie_value, COOKIE
        from agentrader.application.settings import WebSettings
        settings=WebSettings(self.database,Path(self.temp.name)/'execution.db','test-secret-123456789012345678901234','owner',market_database=Path(self.temp.name)/'market.db')
        app=create_app(settings,hub=SimpleNamespace(binding_context=lambda *args:None,close=lambda:None))
        with TestClient(app,base_url='http://127.0.0.1') as client:
            app.state.shadow_worker.close();app.state.alert_worker.close()
            policy=app.state.ui_sessions.policy()
            auth={'Authorization':'Bearer test-secret-123456789012345678901234','X-UI-Publisher-Key':self.key}
            path='/api/workspaces/main/ui-sessions/tab-a'
            value=self.packet();value['server_instance_id']=policy['server_instance_id']
            self.assertEqual(client.put(path,json=value).status_code,401)
            self.assertEqual(client.get(path).status_code,401)
            self.assertEqual(client.get('/api/workspaces/main/chart-context?ui_session_id=tab-a').status_code,401)
            self.assertEqual(client.put(path,json=value,headers=auth).status_code,200)
            self.assertEqual(client.get(path,headers=auth).json()['state'],'READY')
            self.assertEqual(client.get(path,headers={**auth,'Origin':'http://foreign.invalid'}).status_code,403)
            self.assertEqual(client.get(path,headers={**auth,'Host':'foreign.invalid'}).status_code,400)
            self.assertEqual(client.put(path,content=' '*32769,headers={**auth,'Content-Type':'application/json'}).status_code,422)
            self.assertEqual(client.put(path,content=json.dumps(value).replace('1800000000000','NaN'),headers={**auth,'Content-Type':'application/json'}).status_code,422)
            client.cookies.set(COOKIE,cookie_value(settings))
            self.assertEqual(client.get(path).status_code,200)
            self.assertEqual(client.get('/api/workspaces/main/chart-context?ui_session_id=tab-a').json()['ui']['state'],'READY')
        self.assertFalse(settings.execution_database.exists())

