"""Add context metadata without changing legacy account/order/plan identities."""
import json

from agentrader.shared.product_registry import EXECUTION_CONTEXT


def tables(db):return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def execution_context_state(db):
    existing = tables(db)
    if 'discovery_contexts' in existing or 'app_schema_migrations' in existing or 'candles' in existing:
        return 'CONTEXT_MISMATCH'
    if 'execution_namespace' not in existing:
        return 'CONTEXT_UNVERIFIED'
    try:
        rows = db.execute('SELECT body FROM execution_namespace').fetchall()
        valid = len(rows) == 1 and json.loads(rows[0][0]) == EXECUTION_CONTEXT
    except (ValueError, TypeError):
        valid = False
    return 'VERIFIED' if valid else 'CONTEXT_MISMATCH'


def check_execution(db):
    existing = tables(db)
    if 'discovery_contexts' in existing:
        raise ValueError('DISCOVERY_CACHE_IS_NOT_EXECUTION_JOURNAL')
    # Only a genuinely empty store may be initialized implicitly.
    if not existing - {'sqlite_sequence'}:
        return
    state = execution_context_state(db)
    if state != 'VERIFIED':
        raise ValueError('EXECUTION_' + state)


def bind_execution(db):
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS execution_namespace (id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO execution_namespace VALUES(1,?)',(json.dumps(EXECUTION_CONTEXT,sort_keys=True),))


def check_market(db):
    if 'discovery_contexts' in tables(db):raise ValueError('DISCOVERY_CACHE_IS_NOT_MARKET_STORE')
