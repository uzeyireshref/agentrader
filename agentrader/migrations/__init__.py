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
    (10, "demo_shadow_tracking", (
        """CREATE TABLE app_shadow_runs (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            binding_id TEXT NOT NULL,binding_revision INTEGER NOT NULL,definition_hash TEXT NOT NULL,
            state TEXT NOT NULL,reason TEXT,expires_at REAL NOT NULL,checkpoint TEXT NOT NULL,
            updated_at REAL NOT NULL,PRIMARY KEY(owner,workspace_id,binding_id,binding_revision))""",
        """CREATE TABLE app_shadow_events (event_id TEXT PRIMARY KEY,owner TEXT NOT NULL,
            workspace_id TEXT NOT NULL,binding_id TEXT NOT NULL,binding_revision INTEGER NOT NULL,
            created_at REAL NOT NULL,body TEXT NOT NULL,evidence TEXT NOT NULL)""",
        "CREATE INDEX app_shadow_event_history ON app_shadow_events(owner,workspace_id,created_at)",
        "CREATE TABLE app_shadow_worker (name TEXT PRIMARY KEY,state TEXT NOT NULL,observed_at REAL NOT NULL)",
    )),

    (11, "shadow_signal_plan_previews", (
        """CREATE TABLE app_signal_previews (owner TEXT NOT NULL,workspace_id TEXT NOT NULL,
            event_id TEXT NOT NULL,version INTEGER NOT NULL,parameters_hash TEXT NOT NULL,
            body TEXT NOT NULL,PRIMARY KEY(owner,event_id,version))""",
        "CREATE TABLE app_signal_preview_heads (owner TEXT NOT NULL,event_id TEXT NOT NULL,version INTEGER NOT NULL,PRIMARY KEY(owner,event_id))",
    )),
    (12, "explicit_chart_approval_requests", (
        """CREATE TABLE app_chart_approvals (owner TEXT NOT NULL,request_id TEXT NOT NULL,
            payload TEXT NOT NULL,payload_hash TEXT NOT NULL,state TEXT NOT NULL,
            created_at REAL NOT NULL,expires_at REAL NOT NULL,updated_at REAL NOT NULL,
            result TEXT,error_code TEXT,PRIMARY KEY(owner,request_id))""",
        """CREATE TABLE app_chart_approval_worker (owner TEXT PRIMARY KEY,
            updated_at REAL NOT NULL,mode TEXT NOT NULL)""",
    )),

    (13, 'drawing_origins_and_linked_notes', (
        """CREATE TABLE app_drawing_origins (owner TEXT NOT NULL,drawing_id TEXT NOT NULL,
            body TEXT NOT NULL,PRIMARY KEY(owner,drawing_id))""",
        """CREATE TABLE app_drawing_audit (owner TEXT NOT NULL,drawing_id TEXT NOT NULL,
            revision INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(owner,drawing_id,revision))""",
        """CREATE TABLE app_drawing_notes (owner TEXT NOT NULL,drawing_id TEXT NOT NULL,
            note_id TEXT NOT NULL,revision INTEGER NOT NULL,text TEXT NOT NULL,deleted INTEGER NOT NULL,
            updated_at REAL NOT NULL,actor TEXT NOT NULL,target_revision INTEGER NOT NULL,PRIMARY KEY(owner,drawing_id,revision))""",
        """INSERT INTO app_drawing_origins SELECT r.owner,r.drawing_id,
            json_object('schema','drawing-origin/1','kind','manual','source','legacy','actor_id',owner,
            'bot_id',NULL,'strategy_id',NULL,'created_at',updated_at)
            FROM app_drawing_revisions r WHERE revision=(SELECT MIN(x.revision) FROM app_drawing_revisions x WHERE x.owner=r.owner AND x.drawing_id=r.drawing_id)""",
        """INSERT INTO app_drawing_audit SELECT owner,drawing_id,revision,
            json_object('kind','manual','actor_id',owner,'bot_id',NULL,'strategy_id',NULL,'source','legacy')
            FROM app_drawing_revisions""",
        """CREATE TRIGGER app_drawing_origin_immutable_update BEFORE UPDATE ON app_drawing_origins
            BEGIN SELECT RAISE(ABORT,'DRAWING_ORIGIN_IMMUTABLE'); END""",
        """CREATE TRIGGER app_drawing_origin_immutable_delete BEFORE DELETE ON app_drawing_origins
            BEGIN SELECT RAISE(ABORT,'DRAWING_ORIGIN_IMMUTABLE'); END""",
    )),
    (14, 'bot_terminal_queue', (
        """CREATE TABLE IF NOT EXISTS app_bot_jobs (
            job_id TEXT PRIMARY KEY,owner TEXT NOT NULL,action TEXT NOT NULL,payload TEXT NOT NULL,
            payload_hash TEXT NOT NULL,state TEXT NOT NULL,created_at REAL NOT NULL,updated_at REAL NOT NULL,
            result TEXT,result_hash TEXT,error_code TEXT)""",
        """CREATE TABLE IF NOT EXISTS app_bot_worker (
            owner TEXT PRIMARY KEY,updated_at REAL NOT NULL,mode TEXT NOT NULL,error_code TEXT)""",
        "CREATE INDEX app_bot_queue ON app_bot_jobs(owner,state,created_at,job_id)",
        "CREATE INDEX app_bot_recent ON app_bot_jobs(owner,created_at DESC,job_id DESC)",
    )),
    (15, 'bot_job_outcome_summaries', (
        "CREATE TABLE app_bot_job_outcomes (job_id TEXT PRIMARY KEY,result_state TEXT)",
        """INSERT INTO app_bot_job_outcomes SELECT job_id,outcome FROM
            (SELECT job_id,CASE WHEN json_valid(result) THEN json_extract(result,'$.state') END AS outcome FROM app_bot_jobs)
            WHERE typeof(outcome)='text' AND length(outcome)<=64""",
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
                if version == 14:
                    expected = {
                        'app_bot_jobs': ('job_id','owner','action','payload','payload_hash','state','created_at','updated_at','result','result_hash','error_code'),
                        'app_bot_worker': ('owner','updated_at','mode','error_code'),
                    }
                    for table, columns in expected.items():
                        info = list(db.execute(f'PRAGMA table_info({table})'))
                        existing = tuple(r['name'] for r in info)
                        if existing and existing != columns:
                            raise ValueError('BOT_QUEUE_SCHEMA_MISMATCH')
                        nullable = {'job_id','result','result_hash','error_code'} if table=='app_bot_jobs' else {'owner','error_code'}
                        primary = 'job_id' if table=='app_bot_jobs' else 'owner'
                        for field in info:
                            field_name = field['name']
                            kind = 'REAL' if field_name in ('created_at','updated_at') else 'TEXT'
                            if (field['type'].upper()!=kind or field['pk']!=int(field_name==primary)
                                    or field['notnull']!=int(field_name not in nullable)):
                                raise ValueError('BOT_QUEUE_SCHEMA_MISMATCH')
                for statement in statements:
                    db.execute(statement)
                db.execute('INSERT INTO app_schema_migrations VALUES (?,?,?)', (version, name, checksum))
            db.commit()
        except BaseException:
            db.rollback()
            raise
    return {'schema_version': MIGRATIONS[-1][0]}
