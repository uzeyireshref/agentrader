"""Versioned application-store migrations, independent of the execution schema."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid


MIGRATIONS = (
    (1, "application_commands", (
        """CREATE TABLE app_commands (
            actor TEXT NOT NULL, request_id TEXT NOT NULL, action TEXT NOT NULL,
            payload TEXT NOT NULL, digest TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','SUCCEEDED','FAILED')),
            result TEXT, error_code TEXT, created_at REAL NOT NULL,
            updated_at REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(actor, request_id))""",
        "CREATE INDEX app_command_queue ON app_commands(state, created_at)",
        """CREATE TABLE app_worker_state (
            name TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at REAL NOT NULL)""",
    )),
    (2, "drawing_workspaces", (
        """CREATE TABLE app_workspaces (
            owner TEXT NOT NULL, workspace_id TEXT NOT NULL, revision INTEGER NOT NULL,
            body TEXT NOT NULL, PRIMARY KEY(owner,workspace_id))""",
        """CREATE TABLE app_drawing_revisions (
            owner TEXT NOT NULL, drawing_id TEXT NOT NULL, revision INTEGER NOT NULL,
            workspace_id TEXT NOT NULL, geometry TEXT NOT NULL, deleted INTEGER NOT NULL,
            updated_at REAL NOT NULL, PRIMARY KEY(owner,drawing_id,revision))""",
        """CREATE TABLE app_drawing_heads (
            owner TEXT NOT NULL, drawing_id TEXT NOT NULL, revision INTEGER NOT NULL,
            PRIMARY KEY(owner,drawing_id))""",
        """CREATE TABLE app_drawing_requests (
            owner TEXT NOT NULL, request_id TEXT NOT NULL, digest TEXT NOT NULL,
            result TEXT NOT NULL, PRIMARY KEY(owner,request_id))""",
    )),
    (3, "drawing_management", (
        "ALTER TABLE app_drawing_revisions ADD COLUMN management TEXT NOT NULL DEFAULT '{}'",
    )),
    (4, "indicator_configurations", (
        """CREATE TABLE app_indicator_configs (
            owner TEXT NOT NULL, workspace_id TEXT NOT NULL, revision INTEGER NOT NULL,
            body TEXT NOT NULL, PRIMARY KEY(owner,workspace_id))""",
    )),
    (5, "chart_profiles_and_templates", (
        """CREATE TABLE app_chart_profiles (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            revision INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(owner,workspace_id))""",
        """CREATE TABLE app_chart_templates (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            template_id TEXT NOT NULL,revision INTEGER NOT NULL,name TEXT NOT NULL,body TEXT NOT NULL,
            PRIMARY KEY(owner,workspace_id,template_id,revision))""",
    )),
    (6, "revision_bound_chart_rules", (
        """CREATE TABLE app_chart_binding_revisions (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            binding_id TEXT NOT NULL,revision INTEGER NOT NULL,state TEXT NOT NULL CHECK(state IN ('DISABLED','STOPPED')),reason TEXT,
            definition TEXT NOT NULL,PRIMARY KEY(owner,binding_id,revision))""",
        """CREATE TABLE app_chart_binding_heads (owner TEXT NOT NULL,binding_id TEXT NOT NULL,
            revision INTEGER NOT NULL,PRIMARY KEY(owner,binding_id))""",
    )),
    (7, "local_chart_event_intents", (
        """CREATE TABLE app_chart_local_events (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            namespace TEXT NOT NULL,semantic_key TEXT NOT NULL,event_id TEXT NOT NULL UNIQUE,
            body TEXT NOT NULL,evidence TEXT NOT NULL,created_at REAL NOT NULL,
            PRIMARY KEY(owner,workspace_id,namespace,semantic_key))""",
        """CREATE TABLE app_chart_local_intents (event_id TEXT PRIMARY KEY,owner TEXT NOT NULL,
            workspace_id TEXT NOT NULL,namespace TEXT NOT NULL,state TEXT NOT NULL
            CHECK(state IN ('PENDING_FAKE','IN_FLIGHT_FAKE','DELIVERED_FAKE','DELIVERY_UNKNOWN','CANCELED_SUPERSEDED')),
            attempts INTEGER NOT NULL DEFAULT 0,body TEXT NOT NULL)""",
        """CREATE TABLE app_chart_local_phases (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            namespace TEXT NOT NULL,binding_id TEXT NOT NULL,binding_revision INTEGER NOT NULL,
            phase TEXT NOT NULL,event_id TEXT NOT NULL,
            PRIMARY KEY(owner,workspace_id,namespace,binding_id,binding_revision))""",
        """CREATE TABLE app_chart_fake_receipts (event_id TEXT PRIMARY KEY,owner TEXT NOT NULL,
            workspace_id TEXT NOT NULL,namespace TEXT NOT NULL,receipt TEXT NOT NULL)""",
    )),
    (8, "isolated_chart_replay_checkpoints", (
        """CREATE TABLE app_chart_replay_checkpoints (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            namespace TEXT NOT NULL,binding_id TEXT NOT NULL,binding_revision INTEGER NOT NULL,
            profile_hash TEXT NOT NULL,body TEXT NOT NULL,
            PRIMARY KEY(owner,workspace_id,namespace,binding_id,binding_revision,profile_hash))""",
        """CREATE TABLE app_chart_replay_observations (id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,workspace_id TEXT NOT NULL,namespace TEXT NOT NULL,
            binding_id TEXT NOT NULL,body TEXT NOT NULL)""",
        """CREATE TABLE app_chart_local_intents_next (event_id TEXT PRIMARY KEY,owner TEXT NOT NULL,
            workspace_id TEXT NOT NULL,namespace TEXT NOT NULL,state TEXT NOT NULL
            CHECK(state IN ('PENDING_FAKE','IN_FLIGHT_FAKE','DELIVERED_FAKE','DELIVERY_UNKNOWN','CANCELED_SUPERSEDED','CHANNEL_UNCONFIGURED','RETRY_BOUNDED','FAILED','EXPIRED')),
            attempts INTEGER NOT NULL DEFAULT 0,body TEXT NOT NULL)""",
        "INSERT INTO app_chart_local_intents_next SELECT * FROM app_chart_local_intents",
        "DROP TABLE app_chart_local_intents",
        "ALTER TABLE app_chart_local_intents_next RENAME TO app_chart_local_intents",
        """CREATE TABLE app_chart_replay_delivery_policy (event_id TEXT PRIMARY KEY,
            expires_at REAL NOT NULL,retry_at REAL NOT NULL)""",
    )),
    (9, "persistent_price_alerts", (
        "CREATE TABLE app_price_alerts (owner TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,body TEXT NOT NULL,state TEXT NOT NULL,checkpoint TEXT NOT NULL,PRIMARY KEY(owner,id))",
        "CREATE TABLE app_price_alert_events (owner TEXT NOT NULL,id TEXT NOT NULL,alert_id TEXT NOT NULL,created_at REAL NOT NULL,body TEXT NOT NULL,PRIMARY KEY(owner,id))",
    )),
)


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    return db


def migrate(path):
    """Apply atomically; reject future or edited migrations; never set user_version.

    This store is separate from execution.sqlite3. No migration opens that store.
    Existing unrelated tables are preserved, including legacy user_version.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS app_schema_migrations (
                version INTEGER PRIMARY KEY, name TEXT NOT NULL, digest TEXT NOT NULL)""")
            applied = {r['version']: dict(r) for r in db.execute('SELECT * FROM app_schema_migrations')}
            known = {m[0] for m in MIGRATIONS}
            if set(applied) - known:
                raise ValueError('Uygulama veritabanı daha yeni bir şema içeriyor.')
            expected_prefix = list(range(1, len(applied) + 1))
            if sorted(applied) != expected_prefix:
                raise ValueError('Uygulama şema geçiş sırası geçersiz.')
            for version, name, statements in MIGRATIONS:
                checksum = hashlib.sha256(json.dumps(statements).encode()).hexdigest()
                if version in applied:
                    if (applied[version]['name'], applied[version]['digest']) != (name, checksum):
                        raise ValueError('Uygulanmış şema geçişi değişmiş.')
                    continue
                if applied:
                    # The IMMEDIATE transaction blocks concurrent writers while a
                    # separate read connection takes the last committed snapshot.
                    backup = path.with_name(path.name + '.before-v' + str(version) + '-' + uuid.uuid4().hex[:12] + '.bak')
                    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as source:
                        with closing(sqlite3.connect(backup)) as destination:
                            source.backup(destination)
                for statement in statements:
                    db.execute(statement)
                db.execute('INSERT INTO app_schema_migrations VALUES (?,?,?)', (version, name, checksum))
            db.commit()
        except BaseException:
            db.rollback()
            raise
    return {'schema_version': MIGRATIONS[-1][0]}
