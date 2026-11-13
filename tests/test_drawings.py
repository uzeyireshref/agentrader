from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from agentrader.drawings.service import DrawingService, DrawingError, DrawingConflict, DrawingNotFound
from agentrader.migrations import migrate, MIGRATIONS
from agentrader.application.commands import CommandQueue


def line(symbol='BTCUSDT'):
    return {'kind': 'horizontal', 'symbol': symbol, 'price_source': 'LAST_PRICE',
            'label': 'Direnç', 'anchors': [{'time': 1800000000, 'price': '80000.10'}]}


def zone():
    return {'kind': 'zone', 'symbol': 'BTCUSDT', 'price_source': 'LAST_PRICE', 'label': 'Talep',
            'anchors': [{'time': 1800000900, 'price': '79000'}, {'time': 1800000000, 'price': '80000'}]}


class DrawingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'app.db'
        migrate(self.path)
        self.service = DrawingService(self.path, 'owner')

    def test_trend_and_fibonacci_preserve_direction_across_restart_and_revision(self):
        for kind in ('trend', 'fibonacci'):
            with self.subTest(kind=kind):
                value = dict(zone(), kind=kind)
                created = self.service.create('main', kind + '-create', value)
                restarted = DrawingService(self.path, 'owner')
                saved = restarted.show(created['drawing_id'])
                self.assertEqual(saved['geometry']['anchors'], value['anchors'])
                changed = copy.deepcopy(value)
                changed['anchors'][0]['price'] = '78500'
                updated = restarted.update(created['drawing_id'], kind + '-update', 1, changed)
                self.assertEqual(updated['revision'], 2)
                self.assertEqual(updated['geometry']['kind'], kind)
                with self.assertRaises(DrawingConflict):
                    restarted.update(created['drawing_id'], kind + '-stale', 1, value)

    def test_create_duplicate_and_restart_keep_one_revision(self):
        result = self.service.create('main', 'r1', line())
        restarted = DrawingService(self.path, 'owner')
        repeat = restarted.create('main', 'r1', line())
        self.assertTrue(repeat['duplicate'])
        self.assertEqual(result['drawing_id'], repeat['drawing_id'])
        self.assertEqual(len(restarted.list('main', 'BTCUSDT')), 1)
        self.assertEqual(restarted.show(result['drawing_id'])['revision'], 1)

    def test_same_request_identity_with_different_geometry_is_rejected(self):
        self.service.create('main', 'r1', line())
        with self.assertRaises(DrawingConflict):
            self.service.create('main', 'r1', dict(line(), label='Başka çizgi'))

    def test_update_is_revision_checked_and_old_geometry_remains_in_history(self):
        created = self.service.create('main', 'r1', line())
        moved = copy.deepcopy(line())
        moved['anchors'][0]['price'] = '81000.10'
        result = self.service.update(created['drawing_id'], 'r2', 1, moved)
        self.assertEqual(result['revision'], 2)
        with self.assertRaises(DrawingConflict):
            self.service.update(created['drawing_id'], 'r3', 1, line())
        with closing(sqlite3.connect(self.path)) as db:
            original = json.loads(db.execute('SELECT geometry FROM app_drawing_revisions WHERE revision=1').fetchone()[0])
        self.assertEqual(original['anchors'][0]['price'], '80000.10')

    def test_delete_is_tombstone_and_undo_redo_are_new_revisions(self):
        created = self.service.create('main', 'r1', zone())
        deleted = self.service.update(created['drawing_id'], 'r2', 1, deleted=True)
        self.assertTrue(deleted['deleted'])
        self.assertEqual(self.service.list('main', 'BTCUSDT'), [])
        restored = self.service.update(created['drawing_id'], 'r3', 2, created['geometry'])
        self.assertFalse(restored['deleted'])
        again = self.service.update(created['drawing_id'], 'r4', 3, deleted=True)
        self.assertEqual(again['revision'], 4)

    def test_owner_workspace_and_symbol_are_isolated(self):
        created = self.service.create('main', 'r1', line())
        self.service.create('other', 'r2', line('ETHUSDT'))
        other = DrawingService(self.path, 'other-user')
        self.assertEqual(other.list('main', 'BTCUSDT'), [])
        with self.assertRaises(DrawingNotFound):
            other.show(created['drawing_id'])
        self.assertEqual(self.service.list('other', 'BTCUSDT'), [])
        self.assertEqual(len(self.service.list('other', 'ETHUSDT')), 1)

    def test_drawing_cannot_silently_change_symbol_or_kind(self):
        created = self.service.create('main', 'r1', line())
        for value in [line('ETHUSDT'), zone()]:
            with self.assertRaises(DrawingError):
                self.service.update(created['drawing_id'], 'r2', 1, value)

    def test_invalid_geometry_has_no_persisted_effect(self):
        for price in ['NaN', 'Infinity', '-1', '0', 80000]:
            value = line()
            value['anchors'][0]['price'] = price
            with self.assertRaises(DrawingError):
                self.service.create('main', 'invalid', value)
        value = zone()
        value['anchors'][1]['price'] = value['anchors'][0]['price']
        with self.assertRaises(DrawingError):
            self.service.create('main', 'invalid-zone', value)
        self.assertEqual(self.service.list('main', 'BTCUSDT'), [])

    def test_zone_anchors_are_time_sorted_and_price_strings_preserved(self):
        created = self.service.create('main', 'r1', zone())
        self.assertLess(created['geometry']['anchors'][0]['time'], created['geometry']['anchors'][1]['time'])
        self.assertIsInstance(created['geometry']['anchors'][0]['price'], str)

    def test_workspace_selection_persists_and_stale_client_cannot_overwrite(self):
        self.assertEqual(self.service.workspace('main')['revision'], 0)
        preferences = {'symbol': 'ETHUSDT', 'interval': '4h'}
        self.service.save_workspace('main', 'w1', 0, preferences)
        with self.assertRaises(DrawingConflict):
            self.service.save_workspace('main', 'w2', 0, {'symbol': 'BTCUSDT', 'interval': '15m'})
        self.assertEqual(DrawingService(self.path, 'owner').workspace('main')['preferences'], preferences)
        with self.assertRaises(DrawingError):
            self.service.save_workspace('main', 'w3', 1, {'symbol': 'BTCUSDT', 'interval': []})

    def test_upgrade_takes_consistent_v1_backup_and_keeps_pending_command(self):
        old = Path(self.temp.name)/'v1.db'
        with patch('agentrader.migrations.MIGRATIONS', MIGRATIONS[:1]):
            migrate(old)
        CommandQueue(old).accept('owner', {'request_id': 'pending', 'action': 'runtime.inspect', 'payload': {}})
        migrate(old)
        backups = list(old.parent.glob('v1.db.before-v2-*.bak'))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as db:
            self.assertEqual(db.execute('SELECT state FROM app_commands').fetchone()[0], 'QUEUED')
            self.assertEqual(db.execute('SELECT MAX(version) FROM app_schema_migrations').fetchone()[0], 1)
        self.assertEqual(CommandQueue(old).show('owner', 'pending')['state'], 'QUEUED')
        migrate(old)
        self.assertEqual(len(list(old.parent.glob('v1.db.before-v2-*.bak'))), 1)
