from contextlib import closing
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from agentrader.application.environment import bind_demo_store
from agentrader.migrations import migrate,connect
from agentrader.chart.drawings.service import DrawingService,DrawingError,DrawingConflict,DrawingProtected
from agentrader.chart.drawings.actors import DrawingActor
from agentrader.chart.drawings.packages import DrawingPackages,validate_package,PackageMismatch
from agentrader.chart.drawings.notes import DrawingNotes
from agentrader.chart.drawings.calculations import query,CalculationBlocked
from agentrader.chart.drawings.contracts import capability,legacy_contract
from agentrader.chart.chart_profiles import ProfileService,default_view
from scripts.integration.chart_tool_matrix_cases import drawing_cases,START,STEP

ROOT=Path(__file__).resolve().parents[1]


def projection():return drawing_cases(include_projection=True)[-1]['geometry']


class ProjectionPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'app.db';bind_demo_store(self.path);migrate(self.path)
        self.draw=DrawingService(self.path,'owner');self.pack=DrawingPackages(self.path,'owner');self.notes=DrawingNotes(self.path,'owner')
        self.bot=DrawingPackages(self.path,'owner',actor=DrawingActor('bot','bot:alpha','alpha','test'))
    def export(self,item):
        return self.pack.export('main','BTCUSDT','15m',[dict(drawing_id=item['drawing_id'],expected_revision=item['revision'],expected_note_revision=item['linked_note']['revision'])])

    def test_independent_exact_projection_vectors_linear_log_and_extension_difference(self):
        for case in json.loads((ROOT/'frontend/tests/fixtures/projection-g9.json').read_text(encoding='utf-8')):
            g=projection();g['levels']=['0',case['ratio']] if case['ratio']!='0' else ['0','1']
            for anchor,price in zip(g['anchors'],case['prices']):anchor['price']=price
            for scale in ('LINEAR','LOG'):
                with self.subTest(case=case['id'],scale=scale):
                    if 'blocked' in case:
                        with self.assertRaises(CalculationBlocked) as caught:query(g,'level',ratio=case['ratio'],time=g['anchors'][2]['time'],scale=scale)
                        self.assertEqual(caught.exception.code,case['blocked'])
                    else:
                        value=query(g,'level',ratio=case['ratio'],time=g['anchors'][2]['time'],scale=scale)['value']
                        self.assertEqual(Fraction(int(value['numerator']),int(value['denominator'])),Fraction(case['expected']))
        g=projection();g['anchors'][2]['price']='200'
        projection_value=query(g,'level',ratio='1',time=g['anchors'][2]['time'])['value']
        self.assertEqual(projection_value['decimal'],'220.5')

    def test_projection_strict_anchors_basis_scope_schema_and_contract(self):
        g=projection();saved=self.draw.create('main','projection',g)
        c=legacy_contract(saved);self.assertEqual(c['params']['anchor_roles'],['A_IMPULSE_START','B_IMPULSE_END','C_BASE'])
        self.assertEqual(capability('drawing','fibonacci_projection')['format_version'],10)
        for changes in [dict(basis='LOG'),dict(schema='chart-fibonacci/1'),dict(anchors=g['anchors'][:2]),dict(levels=['1','1.0'])]:
            with self.assertRaises(DrawingError):self.draw.create('main','invalid',g|changes)
        g['time_scope']='bounded';low=g['anchors'][2]['time'];high=low+14*STEP
        query(g,'level',ratio='1',time=high)
        for time in (low-1,high+1):
            with self.assertRaises(CalculationBlocked):query(g,'level',ratio='1',time=time)
        g['time_scope']='unbounded';query(g,'level',ratio='1',time=1)

    def test_all_26_variants_copy_notes_style_actor_and_repeated_paste(self):
        for i,case in enumerate(drawing_cases(include_projection=True)):
            with self.subTest(case=case['case_id']):
                item=self.draw.create('main','source-'+str(i),case['geometry'])
                self.notes.save_note(item['drawing_id'],'note-'+str(i),0,1,'🧭'*4000)
                item=self.draw.show(item['drawing_id']);before=deepcopy(item);package=self.export(item)
                self.assertEqual(set(package['items'][0]),{'geometry','management','linked_note'})
                pasted=self.bot.paste('main','paste-'+str(i),'BTCUSDT','15m',package)['drawings'][0]
                self.assertEqual(pasted['geometry'],item['geometry']);self.assertEqual(pasted['management'],item['management'])
                self.assertEqual(pasted['linked_note']['text'],item['linked_note']['text']);self.assertNotEqual(pasted['linked_note']['note_id'],item['linked_note']['note_id'])
                self.assertNotEqual(pasted['drawing_id'],item['drawing_id']);self.assertEqual(pasted['origin']['kind'],'bot')
                self.assertEqual(self.draw.show(item['drawing_id']),before)
                repeated=self.bot.paste('main','paste-'+str(i),'BTCUSDT','15m',package)['drawings'][0]
                self.assertEqual(repeated['drawing_id'],pasted['drawing_id'])
                again=self.pack.paste('main','manual-paste-'+str(i),'BTCUSDT','15m',package)['drawings'][0]
                self.assertEqual(again['origin']['kind'],'manual');self.assertNotEqual(again['drawing_id'],pasted['drawing_id'])

    def test_malformed_package_source_mismatch_and_forged_identity_fail_atomically(self):
        item=self.draw.create('main','source',projection());package=self.export(item)
        for key in ('drawing_id','origin','revision','bot_id'):
            bad=deepcopy(package);bad['items'][0][key]='forged'
            with self.assertRaises(DrawingError):self.pack.paste('main','forged','BTCUSDT','15m',bad)
        for symbol,interval in [('ETHUSDT','15m'),('BTCUSDT','1h')]:
            with self.assertRaises(PackageMismatch):self.pack.paste('main','mismatch',symbol,interval,package)
        bad=deepcopy(package);bad['items']*=21
        with self.assertRaises(DrawingError):validate_package(bad,'BTCUSDT','15m')
        bad=deepcopy(package);bad['items'].append({**deepcopy(bad['items'][0]),'linked_note':{'text':'x'*4001}})
        before=self.path.read_bytes()
        with self.assertRaises(DrawingError):self.pack.paste('main','atomic','BTCUSDT','15m',bad)
        self.assertEqual(before,self.path.read_bytes())

    def test_export_is_readonly_revision_owner_workspace_and_note_guarded(self):
        item=self.draw.create('main','source',projection());before=self.path.read_bytes();self.export(item)
        self.assertEqual(before,self.path.read_bytes())
        self.notes.save_note(item['drawing_id'],'new-note',0,1,'changed')
        with self.assertRaises(DrawingConflict):self.export(item)
        foreign=DrawingPackages(self.path,'other')
        with self.assertRaises(DrawingError):foreign.export('main','BTCUSDT','15m',[dict(drawing_id=item['drawing_id'],expected_revision=1,expected_note_revision=1)])

    def test_paste_history_archives_and_restores_note_without_manual_takeover(self):
        source=self.draw.create('main','source',projection());self.notes.save_note(source['drawing_id'],'note',0,1,'long\n🧭')
        package=self.export(self.draw.show(source['drawing_id']));pasted=self.pack.paste('main','paste','BTCUSDT','15m',package)['drawings'][0]
        self.draw.update(pasted['drawing_id'],'undo',1,deleted=True)
        self.assertEqual(self.notes.show_note(pasted['drawing_id'])['state'],'TARGET_ARCHIVED')
        restored=self.draw.update(pasted['drawing_id'],'redo',2,pasted['geometry'])
        self.assertEqual(restored['linked_note']['text'],'long\n🧭');self.assertEqual(restored['origin'],pasted['origin'])
        with self.assertRaises(DrawingProtected):self.bot.update(source['drawing_id'],'takeover',1,deleted=True)

    def test_projection_profile_defaults_validate_and_preserve_basis(self):
        p=ProfileService(self.path,'owner');body=p.profile('main')['body']
        body['drawing_defaults']={'fibonacci_projection':dict(style=dict(color='#2962ff',line_width=2,line_style='dotted'),options=dict(levels=['0','1','1.618']))}
        saved=p.save_profile('main','defaults',0,body)
        self.assertEqual(saved['body']['drawing_defaults']['fibonacci_projection']['options']['levels'],['0','1','1.618'])

    def test_http_format10_isolation_package_namespace_and_legacy_clients(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        settings=WebSettings(self.path,Path(self.tmp.name)/'execution.db','h'*40,'owner',market_database=Path(self.tmp.name)/'market.db',bot_token='b'*40)
        app=create_app(settings,hub=SimpleNamespace(binding_context=lambda *args:None,close=lambda:None))
        with TestClient(app,base_url='http://127.0.0.1') as client:
            app.state.shadow_worker.close();app.state.alert_worker.close();headers={'Authorization':'Bearer '+'h'*40}
            response=client.post('/api/workspaces/main/drawings?format_version=10',headers=headers,json=dict(request_id='http',geometry=projection()))
            self.assertEqual(response.status_code,201,response.text);did=response.json()['drawing_id']
            self.assertEqual(client.get('/api/drawings/'+did+'?format_version=9').status_code,422)
            self.assertEqual(client.get('/api/workspaces/main/drawings?format_version=9').json()['drawings'],[])
            self.assertEqual(len(client.get('/api/workspaces/main/drawings?format_version=10').json()['drawings']),1)
            export=client.post('/api/workspaces/main/drawing-packages/export',headers=headers,json=dict(symbol='BTCUSDT',interval='15m',targets=[dict(drawing_id=did,expected_revision=1,expected_note_revision=0)]))
            self.assertEqual(export.status_code,200,export.text)
            pasted=client.post('/api/workspaces/main/drawing-packages/paste',headers={'Authorization':'Bearer '+'b'*40},json=dict(request_id='http-paste',symbol='BTCUSDT',interval='15m',package=export.json()))
            self.assertEqual(pasted.status_code,200,pasted.text);self.assertEqual(pasted.json()['drawings'][0]['origin']['kind'],'bot')
