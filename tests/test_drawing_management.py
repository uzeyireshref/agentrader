from contextlib import closing
import copy
import json
from pathlib import Path
import tempfile
import unittest

from agentrader.drawings.service import DrawingService, DrawingError, DrawingConflict, DrawingLocked, DrawingNotFound, management
from agentrader.drawings.calculations import canonical_hash
from agentrader.migrations import migrate, connect
from test_drawings import line


class DrawingManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'app.db'
        migrate(self.path)
        self.s = DrawingService(self.path, 'owner')
        self.a = self.s.create('main', 'a', line())
        self.b = self.s.create('main', 'b', {**line(), 'label': 'second'})

    def op(self, d, **changes):
        return dict(drawing_id=d['drawing_id'], expected_revision=d['revision'], geometry=d['geometry'],
                    management=d['management'], deleted=d['deleted']) | changes

    def test_lock_blocks_geometry_delete_and_style_but_allows_hide_and_unlock(self):
        a = self.s.operations('main', 'lock', [self.op(self.a, management=management() | {'locked': True})])['drawings'][0]
        for op in [self.op(a, geometry={**a['geometry'], 'label': 'changed'}), self.op(a, deleted=True),
                   self.op(a, management=a['management'] | {'color': '#2962ff'})]:
            with self.assertRaises(DrawingLocked):
                self.s.operations('main', 'blocked', [op])
        with self.assertRaises(DrawingLocked):
            self.s.update(a['drawing_id'], 'legacy-delete', a['revision'], deleted=True)
        hidden = self.s.operations('main', 'hide', [self.op(a, management=a['management'] | {'hidden': True})])['drawings'][0]
        self.assertTrue(hidden['management']['locked'])
        self.assertEqual(canonical_hash(hidden['geometry']), canonical_hash(self.a['geometry']))
        self.assertEqual(hidden['tracking'], 'NOT_IMPLEMENTED')
        from agentrader.drawings.contracts import legacy_contract
        self.assertEqual(legacy_contract(hidden)['edit_state'], 'LOCKED')
        self.assertTrue(legacy_contract(hidden)['capabilities']['computable'])
        unlocked = self.s.operations('main', 'unlock', [self.op(hidden, management=hidden['management'] | {'locked': False})])['drawings'][0]
        self.s.update(unlocked['drawing_id'], 'edit', unlocked['revision'], {**unlocked['geometry'], 'label': 'allowed'})

    def test_batch_conflict_rolls_back_all_heads_and_history(self):
        a_op = self.op(self.a, geometry={**self.a['geometry'], 'label': 'move A'})
        b_op = self.op(self.b, expected_revision=99)
        with self.assertRaises(DrawingConflict):
            self.s.operations('main', 'atomic', [a_op, b_op])
        self.assertEqual(self.s.show(self.a['drawing_id'])['revision'], 1)
        with closing(connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM app_drawing_revisions').fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM app_drawing_requests WHERE request_id='atomic'").fetchone()[0], 0)

    def test_response_loss_retry_returns_same_ids_and_single_revision(self):
        ops = [self.op(self.a, geometry={**line(), 'label': 'moved'}), self.op(self.b, geometry={**line(), 'label': 'moved B'})]
        first = self.s.operations('main', 'same', ops)
        replay = DrawingService(self.path, 'owner').operations('main', 'same', ops)
        self.assertFalse(first['duplicate']); self.assertTrue(replay['duplicate'])
        self.assertEqual(first['drawings'], replay['drawings'])
        self.assertEqual([d['revision'] for d in replay['drawings']], [2, 2])
        with self.assertRaises(DrawingConflict):
            self.s.operations('main', 'same', [self.op(self.a)])

    def test_style_timeframes_restart_and_duplicate_have_independent_identity(self):
        m = management() | dict(color='#9b6ed6', line_width=3, line_style='dotted', intervals=['4h', '15m'], hidden=True)
        changed = self.s.operations('main', 'props', [self.op(self.a, management=m)])['drawings'][0]
        reloaded = DrawingService(self.path, 'owner').show(changed['drawing_id'])
        self.assertEqual(reloaded['management'], management(m))
        self.assertEqual(reloaded['geometry'], self.a['geometry'])
        create = self.op(reloaded, drawing_id=None, expected_revision=0, management=reloaded['management'] | {'locked': False})
        copied = self.s.operations('main', 'copy', [create])['drawings'][0]
        self.assertNotEqual(copied['drawing_id'], changed['drawing_id'])
        self.assertEqual(copied['tracking'], 'NOT_IMPLEMENTED')
        self.assertEqual(copied['revision'], 1)

    def test_strict_validation_owner_workspace_and_market_isolation(self):
        invalid = [dict(locked=1), dict(hidden='yes'), dict(intervals=['3m']), dict(intervals=['15m', '15m']),
                   dict(color='red'), dict(line_width=True), dict(line_style='url(x)'), dict(extra=True)]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(DrawingError):
                self.s.operations('main', 'invalid', [self.op(self.a, management=management() | change)])
        with self.assertRaises(DrawingNotFound):
            DrawingService(self.path, 'other').operations('main', 'foreign', [self.op(self.a)])
        with self.assertRaises(DrawingNotFound):
            self.s.operations('other', 'workspace', [self.op(self.a)])
        with self.assertRaises(DrawingError):
            self.s.operations('main', 'mixed', [self.op(self.a), self.op(self.b, geometry=line('ETHUSDT'))])
        with self.assertRaises(DrawingError):
            self.s.operations('main', 'duplicates', [self.op(self.a)] * 2)

    def test_batch_inverse_and_redo_preserve_properties_and_deleted_identity(self):
        moved = self.s.operations('main', 'move', [self.op(d, geometry={**d['geometry'], 'label': 'moved'}) for d in [self.a, self.b]])['drawings']
        restored = self.s.operations('main', 'inverse', [self.op(now, geometry=old['geometry']) for now, old in zip(moved, [self.a, self.b])])['drawings']
        self.assertEqual([d['geometry'] for d in restored], [self.a['geometry'], self.b['geometry']])
        redone = self.s.operations('main', 'redo', [self.op(now, geometry=old['geometry']) for now, old in zip(restored, moved)])['drawings']
        self.assertEqual([d['revision'] for d in redone], [4, 4])

    def test_v2_database_migrates_without_rewriting_old_geometry_or_revision(self):
        from unittest.mock import patch
        import agentrader.migrations as migrations
        old_path=Path(self.temp.name)/'old.db'
        with patch.object(migrations, 'MIGRATIONS', migrations.MIGRATIONS[:2]):
            migrations.migrate(old_path)
        with closing(connect(old_path)) as db, db:
            db.execute('INSERT INTO app_drawing_revisions VALUES (?,?,?,?,?,?,?)', ('owner','old',7,'main',json.dumps(line()),0,123))
            db.execute('INSERT INTO app_drawing_heads VALUES (?,?,?)', ('owner','old',7))
        migrate(old_path)
        saved=DrawingService(old_path,'owner').show('old')
        self.assertEqual(saved['revision'],7)
        self.assertEqual(saved['geometry'],line())
        self.assertEqual(saved['updated_at'],123)
        self.assertEqual(saved['management'],management())

    def test_v4_read_and_write_isolation_from_older_clients(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        with TestClient(create_app(WebSettings(self.path, Path(self.temp.name)/'exec.db', market_database=Path(self.temp.name)/'market.db')), base_url='http://127.0.0.1') as c:
            endpoint='/api/workspaces/main/drawing-operations'
            # The API uses its configured local owner, rather than the service's test owner.
            saved=c.post('/api/workspaces/main/drawings', json=dict(request_id='api-a', geometry=line())).json()
            payload=dict(request_id='api-lock', operations=[self.op(saved, management=management() | {'locked': True})])
            self.assertEqual(c.post(endpoint, json=payload).status_code, 422)
            locked=c.post(endpoint+'?format_version=4', json=payload)
            self.assertEqual(locked.status_code, 200)
            for version in [1,2,3]:
                suffix='?format_version='+str(version)
                self.assertEqual(c.get('/api/workspaces/main/drawings'+suffix).json()['drawings'], [])
                self.assertEqual(c.get('/api/drawings/'+saved['drawing_id']+suffix).status_code, 422)
            self.assertEqual(c.patch('/api/drawings/'+saved['drawing_id']+'?format_version=4', json=dict(request_id='no', expected_revision=2, geometry={**line(), 'label':'changed'})).status_code, 423)
