"""G7 isolated origin, actor, linked-note and migration acceptance."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentrader import migrations
from agentrader.application.environment import bind_demo_store
from agentrader.chart.drawings.actors import DrawingActor
from agentrader.chart.drawings.service import DrawingService,DrawingProtected,DrawingLocked,DrawingConflict,DrawingError,management
from agentrader.chart.drawings.notes import DrawingNotes
from agentrader.chart.chart_context import ChartContext,ContextChanged
from agentrader.chart.chart_queries import ChartQueries
from agentrader.chart.chart_profiles import ProfileService,default_view
from scripts.integration.chart_tool_matrix_cases import drawing_cases


class OriginNoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'app.db';bind_demo_store(self.path);migrations.migrate(self.path)
        self.human=DrawingService(self.path,'owner')
        self.actor=DrawingActor('bot','bot:alpha','alpha','strategy-a')
        self.bot=DrawingService(self.path,'owner',actor=self.actor)
        self.notes=DrawingNotes(self.path,'owner');self.botnotes=DrawingNotes(self.path,'owner',actor=self.actor)
        self.geometry=drawing_cases()[0]['geometry']
        self.manual=self.human.create('main','manual',self.geometry)

    def op(self,item,**changes):
        return dict(drawing_id=item['drawing_id'],expected_revision=item['revision'],geometry=item['geometry'],management=item['management'],deleted=item['deleted'])|changes

    def test_all_25_schemas_preserve_existing_text_and_support_separate_notes(self):
        for i,case in enumerate(drawing_cases()):
            with self.subTest(case=case['case_id']):
                item=self.human.create('main','case-'+str(i),case['geometry'])
                text='Uzun açıklama 🧭\nİstanbul 日本語\t\r\n<script>test</script>'
                note=self.notes.save_note(item['drawing_id'],'note-'+str(i),0,1,text)
                self.assertEqual(note['text'],text)
                read=self.human.show(item['drawing_id']);self.assertEqual(read['geometry'],item['geometry'])
                self.assertEqual(read['revision'],1);self.assertEqual(read['linked_note']['text'],text)
                self.assertEqual(read['origin']['kind'],'manual')

    def test_bot_cannot_edit_delete_style_unlock_or_history_restore_manual(self):
        item=self.manual;before=self.human.show(item['drawing_id'])
        calls=[lambda:self.bot.update(item['drawing_id'],'edit',1,{**item['geometry'],'label':'bot'}),
               lambda:self.bot.update(item['drawing_id'],'delete',1,deleted=True),
               lambda:self.bot.operations('main','style',[self.op(item,management={**item['management'],'color':'#2962ff'})]),
               lambda:self.bot.operations('main','undo',[self.op(item,deleted=True)]),
               lambda:self.botnotes.save_note(item['drawing_id'],'note-denied',0,1,'forbidden')]
        for call in calls:
            with self.assertRaises(DrawingProtected):call()
        self.assertEqual(self.human.show(item['drawing_id']),before)
        self.human.update(item['drawing_id'],'human-delete',1,deleted=True)
        with self.assertRaises(DrawingProtected):self.bot.operations('main','resurrect',[self.op(item,expected_revision=2)])

    def test_mixed_bulk_is_atomic_and_duplicate_is_new_identity_without_takeover(self):
        own=self.bot.create('main','own',self.geometry)
        with self.assertRaises(DrawingProtected):
            self.bot.operations('main','mixed',[self.op(own,geometry={**own['geometry'],'label':'changed'}),self.op(self.manual,deleted=True)])
        self.assertEqual(self.bot.show(own['drawing_id'])['revision'],1)
        copy=self.bot.operations('main','duplicate',[self.op(self.manual,drawing_id=None,expected_revision=0)])['drawings'][0]
        self.assertNotEqual(copy['drawing_id'],self.manual['drawing_id'])
        self.assertEqual(copy['origin']['kind'],'bot');self.assertEqual(self.human.show(self.manual['drawing_id'])['origin']['kind'],'manual')

    def test_bot_strategy_scope_and_human_edits_preserve_immutable_origin(self):
        item=self.bot.create('main','bot-item',self.geometry)
        changed=self.bot.update(item['drawing_id'],'bot-edit',1,{**self.geometry,'label':'alpha'})
        self.assertEqual(changed['origin'],item['origin']);self.assertEqual(changed['change']['updated_by'],self.actor.view())
        other=DrawingService(self.path,'owner',actor=DrawingActor('bot','bot:alpha','alpha','strategy-b'))
        with self.assertRaises(DrawingProtected):other.update(item['drawing_id'],'other',2,deleted=True)
        human=self.human.update(item['drawing_id'],'human',2,{**self.geometry,'label':'human edited'})
        self.assertEqual(human['origin'],item['origin']);self.assertEqual(human['change']['updated_by']['kind'],'manual')
        history=self.bot.history(item['drawing_id'],limit=2)
        self.assertEqual([r['updated_by']['kind'] for r in history['revisions']],['manual','bot']);self.assertEqual(history['next_offset'],2)
        with closing(migrations.connect(self.path)) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute("UPDATE app_drawing_origins SET body='{}'")

    def test_idempotency_actor_binding_does_not_return_human_cached_success_to_bot(self):
        self.assertTrue(self.human.create('main','manual',self.geometry)['duplicate'])
        with self.assertRaises(DrawingConflict):self.bot.create('main','manual',self.geometry)
        item=self.bot.create('main','retry-bot',self.geometry)
        self.assertEqual(self.bot.create('main','retry-bot',self.geometry)['drawing_id'],item['drawing_id'])
        self.assertEqual(len(self.bot.history(item['drawing_id'])['revisions']),1)

    def test_notes_revision_conflict_lock_owner_archive_and_restore(self):
        did=self.manual['drawing_id'];note=self.notes.save_note(did,'save',0,1,'ilk\n🧭')
        self.assertTrue(self.notes.save_note(did,'save',0,1,'ilk\n🧭')['duplicate'])
        with self.assertRaises(DrawingConflict):self.notes.save_note(did,'stale',0,1,'lost update')
        locked=self.human.operations('main','lock',[self.op(self.manual,management={**self.manual['management'],'locked':True})])['drawings'][0]
        with self.assertRaises(DrawingLocked):self.notes.save_note(did,'locked',1,2,'locked')
        unlocked=self.human.operations('main','unlock',[self.op(locked,management=management())])['drawings'][0]
        with self.assertRaises(DrawingConflict):self.notes.save_note(did,'old-target',1,1,'stale target')
        note2=self.notes.save_note(did,'save2',1,unlocked['revision'],'ikinci')
        self.assertEqual(self.notes.show_note(did,1)['text'],'ilk\n🧭');self.assertEqual(note['note_id'],note2['note_id'])
        self.human.update(did,'delete-target',unlocked['revision'],deleted=True)
        archived=self.notes.show_note(did);self.assertEqual(archived['state'],'TARGET_ARCHIVED');self.assertEqual(archived['text'],'ikinci')
        with self.assertRaises(DrawingProtected):self.notes.save_note(did,'archive-write',2,4,'no')
        restored=self.human.operations('main','restore-target',[self.op(unlocked,expected_revision=4)])['drawings'][0]
        self.assertEqual(restored['linked_note']['state'],'ACTIVE');self.assertEqual(restored['linked_note']['revision'],2)
        foreign=DrawingNotes(self.path,'foreign')
        with self.assertRaises(DrawingError):foreign.show_note(did)

    def test_note_delete_and_content_limits_no_geometry_or_origin_change(self):
        did=self.manual['drawing_id'];self.notes.save_note(did,'long',0,1,'🧭'*4000)
        deleted=self.notes.save_note(did,'delete-note',1,1,'',deleted=True)
        self.assertEqual(deleted['state'],'NOTE_DELETED');self.assertEqual(self.notes.show_note(did,1)['text'],'🧭'*4000)
        for i,text in enumerate(['x'*4001,'a\x00b','a\x7fb','\ud800']):
            with self.assertRaises(DrawingError):self.notes.save_note(did,'invalid-'+str(i),2,1,text)
        current=self.human.show(did);self.assertEqual(current['geometry'],self.manual['geometry']);self.assertEqual(current['origin'],self.manual['origin'])

    def test_concurrent_note_writers_one_wins_without_lost_revision(self):
        def save(i):
            try:return self.notes.save_note(self.manual['drawing_id'],'race-'+str(i),0,1,str(i))['revision']
            except DrawingConflict:return 'CONFLICT'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,[1,2]))
        self.assertCountEqual(results,[1,'CONFLICT'])

    def test_notes_invalidate_context_and_appear_in_numeric_query_without_writes(self):
        context=ChartContext(self.path,'owner',SimpleNamespace(binding_context=lambda *args:None))
        before=context.read('main');self.notes.save_note(self.manual['drawing_id'],'context-note',0,1,'bağlı not')
        after=context.read('main');self.assertNotEqual(before['context_id'],after['context_id'])
        with self.assertRaises(ContextChanged):context.read('main',expected_context_id=before['context_id'])
        self.assertEqual(after['objects'][0]['linked_note']['text'],'bağlı not')
        stamp=self.path.read_bytes()
        result=ChartQueries(context).single(self.manual['drawing_id'],'chart-query-request/1',dict(symbol='BTCUSDT',interval='15m'),dict(query_id='q',expected_revision=1,operation='priceAt',inputs=dict(time=self.geometry['anchors'][0]['time'])))
        self.assertEqual(result['results'][0]['linked_note']['text'],'bağlı not');self.assertEqual(self.path.read_bytes(),stamp)

    def test_template_import_cannot_bypass_bot_service_guard(self):
        botprofile=ProfileService(self.path,'owner',actor=self.actor)
        with self.assertRaises(DrawingProtected):botprofile.save_profile('main','bot-profile',0,dict(schema='chart-profile/1',view=default_view(),drawing_defaults={}))

    def test_v12_migration_backup_lossless_backfill_and_rollback_copy(self):
        old=Path(self.tmp.name)/'v12.db'
        with patch.object(migrations,'MIGRATIONS',migrations.MIGRATIONS[:12]):migrations.migrate(old)
        geometry=next(c['geometry'] for c in drawing_cases() if c['geometry']['kind']=='note')
        geometry={**geometry,'text':'Eski not\nİstanbul 🧭'}
        with closing(migrations.connect(old)) as db,db:
            db.execute('INSERT INTO app_drawing_revisions VALUES (?,?,?,?,?,?,?,?)',('owner','legacy',1,'main',json.dumps(geometry),0,123.,'{}'))
            db.execute('INSERT INTO app_drawing_heads VALUES (?,?,?)',('owner','legacy',1))
        migrations.migrate(old)
        item=DrawingService(old,'owner').show('legacy')
        self.assertEqual(item['geometry'],geometry);self.assertEqual(item['origin']['source'],'legacy');self.assertEqual(item['origin']['created_at'],123.)
        backup=list(old.parent.glob('v12.db.before-v13-*.bak'));self.assertEqual(len(backup),1)
        restored=Path(self.tmp.name)/'rollback.db';restored.write_bytes(backup[0].read_bytes())
        with closing(migrations.connect(restored)) as db:
            self.assertEqual(db.execute('SELECT MAX(version) FROM app_schema_migrations').fetchone()[0],12)
            self.assertEqual(json.loads(db.execute('SELECT geometry FROM app_drawing_revisions').fetchone()[0]),geometry)
        with patch.object(migrations,'MIGRATIONS',migrations.MIGRATIONS[:12]):migrations.migrate(restored)
        self.assertEqual(migrations.migrate(old)['schema_version'],13)

    def test_failed_migration_rolls_back_and_preserves_preupgrade_geometry(self):
        old=Path(self.tmp.name)/'fail.db';original=migrations.MIGRATIONS
        with patch.object(migrations,'MIGRATIONS',original[:12]):migrations.migrate(old)
        broken=original[:12]+((13,'broken',original[-1][2]+('INVALID SQL',)),)
        with patch.object(migrations,'MIGRATIONS',broken):
            with self.assertRaises(sqlite3.Error):migrations.migrate(old)
        with closing(migrations.connect(old)) as db:
            self.assertEqual(db.execute('SELECT MAX(version) FROM app_schema_migrations').fetchone()[0],12)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='app_drawing_origins'").fetchone())

    def test_http_verified_actor_spoofing_bulk_import_auth_and_private_routes(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        from agentrader.api.session import COOKIE,cookie_value
        settings=WebSettings(self.path,Path(self.tmp.name)/'execution.db','h'*40,'owner',market_database=Path(self.tmp.name)/'market.db',bot_token='b'*40,bot_id='alpha',strategy_id='strategy-a')
        app=create_app(settings,hub=SimpleNamespace(binding_context=lambda *args:None,close=lambda:None))
        with TestClient(app,base_url='http://127.0.0.1') as client:
            app.state.shadow_worker.close();app.state.alert_worker.close()
            bot={'Authorization':'Bearer '+settings.bot_token};human={'Authorization':'Bearer '+settings.token}
            path='/api/workspaces/main/drawings?format_version=9';target='/api/drawings/'+self.manual['drawing_id']
            payload=dict(request_id='http-bot',geometry=self.geometry)
            self.assertEqual(client.post(path,json=payload).status_code,401)
            response=client.post(path,json=payload,headers=bot);self.assertEqual(response.status_code,201,response.text)
            item=response.json();self.assertEqual(item['origin']['bot_id'],'alpha')
            for extra in ('origin','actor','bot_id','strategy_id'):
                self.assertEqual(client.post(path,json={**payload,extra:'manual'},headers=bot).status_code,422)
            self.assertEqual(client.post(path,json={**payload,'request_id':'spoof','geometry':{**self.geometry,'origin':'bot'}},headers=bot).status_code,422)
            self.assertEqual(client.get(target+'?format_version=9',headers=bot).status_code,200)
            self.assertEqual(client.patch(target+'?format_version=9',json=dict(request_id='manual-edit',expected_revision=1,geometry=self.geometry),headers=bot).status_code,403)
            self.assertEqual(client.request('DELETE',target+'?format_version=9',json=dict(request_id='manual-del',expected_revision=1),headers=bot).status_code,403)
            self.assertEqual(client.post('/api/workspaces/main/drawing-operations?format_version=9',json=dict(request_id='manual-bulk',operations=[self.op(self.manual)]),headers=bot).status_code,403)
            self.assertEqual(client.put(target+'/notes',json=dict(request_id='manual-note',expected_revision=0,expected_drawing_revision=1,text='no'),headers=bot).status_code,403)
            own='/api/drawings/'+item['drawing_id']
            response=client.put(own+'/notes',json=dict(request_id='bot-note',expected_revision=0,expected_drawing_revision=1,text='Bot 🧭\nnotu'),headers=bot)
            self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['updated_by']['kind'],'bot')
            for route,method in [('/api/workspaces/main/template-restore','POST'),('/api/workspaces/main/profile','PUT'),('/api/commands','POST'),('/api/status','GET'),('/api/session','POST')]:
                self.assertEqual(client.request(method,route,json={},headers=bot).status_code,403,(route,method))
            self.assertEqual(client.get('/api/workspaces/main/ui-sessions',headers=bot).status_code,200)
            self.assertEqual(client.get('/api/workspaces/main/chart-context?ui_session_id=missing',headers=bot).status_code,200)
            self.assertEqual(client.get(own+'/history',headers=bot).json()['origin']['kind'],'bot')
            client.cookies.set(COOKIE,cookie_value(settings))
            self.assertEqual(client.put(target+'/notes',json=dict(request_id='human-note',expected_revision=0,expected_drawing_revision=1,text='İnsan notu')).status_code,200)
            self.assertEqual(client.get(target+'/notes',headers=bot).json()['text'],'İnsan notu')
            self.assertNotIn(settings.bot_token,client.get(own,params=dict(format_version=9),headers=human).text)
        self.assertFalse(settings.execution_database.exists())
        with self.assertRaises(ValueError):replace(settings,bot_token=settings.token)
        with self.assertRaises(ValueError):replace(settings,token='')
