from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path

from agentrader.migrations import migrate, MIGRATIONS
from agentrader.application.commands import CommandQueue


class ApplicationMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'app.db'

    def test_repeat_preserves_existing_tables_user_version_and_queued_commands(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE old_records (body TEXT)')
            db.execute("INSERT INTO old_records VALUES ('kept')")
            db.execute('PRAGMA user_version=17')
        self.assertEqual(migrate(self.path), {'schema_version': MIGRATIONS[-1][0]})
        CommandQueue(self.path).accept('owner', {'request_id': 'r', 'action': 'runtime.inspect', 'payload': {}})
        migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT * FROM old_records').fetchone(), ('kept',))
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 17)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM app_commands').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM app_schema_migrations').fetchone()[0], len(MIGRATIONS))

    def test_edited_migration_digest_is_rejected_without_losing_commands(self):
        migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE app_schema_migrations SET digest='edited'")
        with self.assertRaises(ValueError):
            migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT digest FROM app_schema_migrations').fetchone()[0], 'edited')

    def test_future_version_is_rejected(self):
        migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO app_schema_migrations VALUES (99,'future','hash')")
        with self.assertRaises(ValueError):
            migrate(self.path)

    def test_failed_migration_rolls_back_all_ddl_and_preserves_existing_data(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE app_worker_state (legacy TEXT)')
            db.execute("INSERT INTO app_worker_state VALUES ('original')")
        with self.assertRaises(sqlite3.OperationalError):
            migrate(self.path)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute('SELECT * FROM app_worker_state').fetchall(), [('original',)])
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn('app_commands', tables)
            self.assertNotIn('app_schema_migrations', tables)
