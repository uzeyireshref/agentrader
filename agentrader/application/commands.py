"""Bounded read-only command inbox shared by future terminal/Telegram adapters."""
from contextlib import closing
import hashlib
import json
import re
import time

from ..migrations import connect


class InvalidCommand(ValueError):
    pass


class CommandConflict(ValueError):
    pass


class CommandNotFound(LookupError):
    pass


def validate_command(command):
    if not isinstance(command, dict) or set(command) != {'request_id', 'action', 'payload'}:
        raise InvalidCommand('Komut alanları geçersiz.')
    rid = command['request_id']
    if not isinstance(rid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', rid):
        raise InvalidCommand('Komut kimliği geçersiz.')
    # No trade/stop/approve/settings commands are supported by this W1 inbox.
    if command['action'] != 'runtime.inspect' or command['payload'] != {}:
        raise InvalidCommand('Yalnız boş parametreli runtime.inspect destekleniyor.')
    return rid, command['action'], '{}'


class CommandQueue:
    def __init__(self, database, clock=time.time):
        self.database, self.clock = database, clock

    @staticmethod
    def _view(row):
        return {k: row[k] for k in ('request_id', 'action', 'state', 'created_at', 'updated_at', 'attempts')} | {
            'result': json.loads(row['result']) if row['result'] else None,
            'error_code': row['error_code']}

    def accept(self, actor, command):
        rid, action, payload = validate_command(command)
        digest = hashlib.sha256(json.dumps([actor, action, payload]).encode()).hexdigest()
        now = self.clock()
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM app_commands WHERE actor=? AND request_id=?', (actor, rid)).fetchone()
            if old:
                if old['digest'] != digest:
                    raise CommandConflict('Komut kimliği başka içerikle kullanılmış.')
                return self._view(old) | {'duplicate': True}
            db.execute('''INSERT INTO app_commands
                (actor,request_id,action,payload,digest,state,created_at,updated_at)
                VALUES (?,?,?,?,?,'QUEUED',?,?)''', (actor, rid, action, payload, digest, now, now))
            row = db.execute('SELECT * FROM app_commands WHERE actor=? AND request_id=?', (actor, rid)).fetchone()
            return self._view(row) | {'duplicate': False}

    def show(self, actor, rid):
        with closing(connect(self.database)) as db:
            row = db.execute('SELECT * FROM app_commands WHERE actor=? AND request_id=?', (actor, rid)).fetchone()
            if row is None:
                raise CommandNotFound()
            return self._view(row)

    def claim(self, actor):
        # Caller holds the worker lock. A crashed read-only inspect is replayable.
        # Financial commands must never be added here without delivery reconciliation.
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('''SELECT * FROM app_commands WHERE actor=?
                AND state IN ('QUEUED','RUNNING') ORDER BY created_at,request_id LIMIT 1''', (actor,)).fetchone()
            if row is None:
                return None
            expected = hashlib.sha256(json.dumps([actor, row['action'], row['payload']]).encode()).hexdigest()
            if row['action'] != 'runtime.inspect' or row['payload'] != '{}' or row['digest'] != expected:
                db.execute("UPDATE app_commands SET state='FAILED',error_code='INVALID_STORED_COMMAND',updated_at=? WHERE actor=? AND request_id=?",
                           (self.clock(), actor, row['request_id']))
                return {'request_id': row['request_id'], 'state': 'FAILED'}
            db.execute("UPDATE app_commands SET state='RUNNING',attempts=attempts+1,updated_at=? WHERE actor=? AND request_id=?",
                       (self.clock(), actor, row['request_id']))
            return {'request_id': row['request_id'], 'state': 'RUNNING'}

    def finish(self, actor, rid, *, result=None, error_code=None):
        with closing(connect(self.database)) as db, db:
            changed = db.execute('''UPDATE app_commands SET state=?,result=?,error_code=?,updated_at=?
                WHERE actor=? AND request_id=? AND state='RUNNING' ''',
                ('FAILED' if error_code else 'SUCCEEDED', json.dumps(result) if result is not None else None,
                 error_code, self.clock(), actor, rid)).rowcount
            if changed != 1:
                raise CommandConflict('Komut yürütme durumu değişmiş.')

    def heartbeat(self, state):
        with closing(connect(self.database)) as db, db:
            db.execute("INSERT OR REPLACE INTO app_worker_state VALUES ('command-worker',?,?)", (state, self.clock()))

    def worker_status(self):
        with closing(connect(self.database)) as db:
            row = db.execute("SELECT * FROM app_worker_state WHERE name='command-worker'").fetchone()
            if row is None:
                return {'state': 'NOT_OBSERVED'}
            age = self.clock() - row['updated_at']
            return {'state': row['state'], 'observed_at': row['updated_at'],
                    'health': 'STOPPED' if row['state'] == 'STOPPED' else ('FRESH' if 0 <= age <= 15 else 'STALE')}
