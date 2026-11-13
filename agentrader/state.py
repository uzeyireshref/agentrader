"""SQLite üzerinde gönderim niyetleri ve kalıcı giriş durdurma durumu."""
import json
import sqlite3
from pathlib import Path


class StateStore:
    def __init__(self, path=Path('data/execution.sqlite3')):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS intents (
              client_id TEXT PRIMARY KEY, path TEXT NOT NULL, params TEXT NOT NULL,
              state TEXT NOT NULL, response TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS control (name TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY, event TEXT NOT NULL, payload TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS managed_sessions (
              session_id TEXT PRIMARY KEY, body TEXT NOT NULL, active INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS plan_versions (
              plan_id TEXT NOT NULL, version INTEGER NOT NULL, body TEXT NOT NULL,
              digest TEXT NOT NULL, state TEXT NOT NULL, owner TEXT NOT NULL,
              token_hash TEXT NOT NULL, approval_until REAL, authorized_by TEXT,
              authorized_at REAL, action_id TEXT, session_id TEXT,
              PRIMARY KEY(plan_id,version));
            CREATE TABLE IF NOT EXISTS plan_slots (
              symbol TEXT PRIMARY KEY, plan_id TEXT NOT NULL, version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS plan_actions (
              action_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, version INTEGER NOT NULL,
              kind TEXT NOT NULL, state TEXT NOT NULL,
              UNIQUE(plan_id,version,kind));
        ''')
        if self.db.execute('PRAGMA user_version').fetchone()[0] < 1:
            self.db.execute('PRAGMA user_version=1')

    def event(self, event, payload):
        with self.db:
            self.db.execute('INSERT INTO events(event,payload) VALUES (?,?)',
                            (event, json.dumps(payload)))

    def reserve(self, client_id, path, params):
        # UNIQUE kimlik iki süreçte de yalnızca bir gönderim hakkı verir.
        try:
            with self.db:
                self.db.execute('INSERT INTO intents(client_id,path,params,state) VALUES (?,?,?,?)',
                                (client_id, path, json.dumps(params), 'SUBMITTING'))
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, client_id, state, response=None):
        with self.db:
            self.db.execute('UPDATE intents SET state=?,response=?,updated_at=CURRENT_TIMESTAMP WHERE client_id=?',
                            (state, json.dumps(response), client_id))

    def intents(self):
        return [dict(row) for row in self.db.execute('SELECT * FROM intents ORDER BY rowid')]

    def intent(self,client_id):
        row=self.db.execute('SELECT * FROM intents WHERE client_id=?',(client_id,)).fetchone()
        return dict(row)if row else None

    def halt(self, reason):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO control VALUES ('halt',?)", (reason,))

    def halt_reason(self):
        row = self.db.execute("SELECT value FROM control WHERE name='halt'").fetchone()
        return row[0] if row else None

    def clear_halt(self):
        with self.db:
            self.db.execute("DELETE FROM control WHERE name='halt'")

    def save_stream_observation(self, session_id, event):
        """Persist the REST barrier and sanitized audit record atomically."""
        body = json.dumps(event)
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',
                            ('stream_pending:'+session_id, body))
            self.db.execute('INSERT INTO events(event,payload) VALUES (?,?)',
                            ('user_stream_observed', body))

    def pending_stream_observation(self, session_id):
        row = self.db.execute('SELECT value FROM control WHERE name=?',
                              ('stream_pending:'+session_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def clear_stream_observation(self, session_id, event_id):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            event = self.pending_stream_observation(session_id)
            if event is not None and event.get('event_id') != event_id:
                raise ValueError('Uzlaştırılacak kullanıcı akışı olayı değişti.')
            self.db.execute('DELETE FROM control WHERE name=?', ('stream_pending:'+session_id,))

    def unresolved_account_command(self):
        if self.db.execute("SELECT 1 FROM control WHERE name LIKE 'stream_pending:%'").fetchone():
            return True
        for table in ('account_commands','margin_commands','order_modifications'):
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                if self.db.execute(f"SELECT 1 FROM {table} WHERE state IN ('UNKNOWN','SUBMITTING','ACKNOWLEDGED')").fetchone():return True
        return False

    def runtime_health(self,session_id,report,observed_at):
        body={'session_id':session_id,'state':report['state'],'observed_at':observed_at,
              'service_stopped':report.get('service_stopped',False)}
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',
                            ('runtime_health:'+session_id,json.dumps(body)))

    def service_stop_request(self,session_id):
        row=self.db.execute('SELECT value FROM control WHERE name=?',('service_stop:'+session_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.db.close()

    def save_session(self, session):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO managed_sessions VALUES (?,?,?)',
                            (session['id'], json.dumps(session), int(session['active'])))

    def sessions(self, active=True):
        return [json.loads(row['body']) for row in self.db.execute(
            'SELECT body FROM managed_sessions WHERE active=?', (int(active),))]
