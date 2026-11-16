"""Do not reinterpret an old public-market workspace as a demo workspace."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3

from agentrader.shared.market_environment import SOURCE, ENVIRONMENT, PRODUCT

CONTEXT = dict(schema='application-market-context/1', source=SOURCE,
               environment=ENVIRONMENT, product=PRODUCT)


def bind_demo_store(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=10)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'app_market_context' in tables:
            rows = db.execute('SELECT body FROM app_market_context').fetchall()
            if len(rows) != 1 or json.loads(rows[0][0]) != CONTEXT:
                raise ValueError('DEMO_APPLICATION_CONTEXT_MISMATCH')
            return
        # Schema-only stores can be initialized. Any existing user data requires
        # explicit export/copy; in particular old active alerts must not run here.
        for table in tables:
            if table.startswith('app_') and table != 'app_schema_migrations':
                quoted = '"'+table.replace('"', '""')+'"'
                if db.execute('SELECT 1 FROM '+quoted+' LIMIT 1').fetchone():
                    raise ValueError('LEGACY_APPLICATION_REQUIRES_SEPARATE_DEMO_STORE')
        db.execute('CREATE TABLE app_market_context (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
        db.execute('INSERT INTO app_market_context VALUES (1,?)', (json.dumps(CONTEXT, sort_keys=True),))
