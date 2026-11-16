"""Add context metadata without changing legacy account/order/plan identities."""
import json

from agentrader.shared.product_registry import EXECUTION_CONTEXT


def tables(db):return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def check_execution(db):
    existing=tables(db)
    if 'discovery_contexts' in existing:raise ValueError('DISCOVERY_CACHE_IS_NOT_EXECUTION_JOURNAL')
    if 'execution_namespace' in existing:
        rows=db.execute('SELECT body FROM execution_namespace').fetchall()
        try:valid=len(rows)==1 and json.loads(rows[0][0])==EXECUTION_CONTEXT
        except (ValueError,TypeError):valid=False
        if not valid:raise ValueError('EXECUTION_NAMESPACE_MISMATCH')


def bind_execution(db):
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS execution_namespace (id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO execution_namespace VALUES(1,?)',(json.dumps(EXECUTION_CONTEXT,sort_keys=True),))


def check_market(db):
    if 'discovery_contexts' in tables(db):raise ValueError('DISCOVERY_CACHE_IS_NOT_MARKET_STORE')
