"""Sanitized local observations. Opens the execution store in SQLite read-only mode."""
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import time

from ..capabilities import list_capabilities


class StorageUnavailable(RuntimeError):
    pass


def execution_status(database, owner, clock=time.time):
    database = Path(database)
    if not database.exists():
        return {'storage': 'NOT_INITIALIZED', 'observation': 'LOCAL_ONLY', 'exchange_access': 'NOT_CHECKED',
                'entry_halted': None, 'active_sessions': [], 'intent_counts': {}}
    try:
        with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')  # All summaries refer to the same local snapshot.
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'control', 'intents', 'managed_sessions'} <= tables:
                return {'storage': 'INCOMPLETE_SCHEMA', 'observation': 'LOCAL_ONLY', 'exchange_access': 'NOT_CHECKED',
                        'entry_halted': None, 'active_sessions': [], 'intent_counts': {}}
            owner_row = db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone() if 'control' in tables else None
            if owner_row and owner_row[0] != owner:
                return {'storage': 'OWNER_MISMATCH', 'observation': 'LOCAL_ONLY', 'exchange_access': 'NOT_CHECKED',
                        'entry_halted': None, 'active_sessions': [], 'intent_counts': {}}
            halted = bool(db.execute("SELECT 1 FROM control WHERE name='halt'").fetchone()) if 'control' in tables else False
            counts = {r['state']: r['n'] for r in db.execute('SELECT state,COUNT(*) AS n FROM intents GROUP BY state')} if 'intents' in tables else {}
            sessions = []
            if 'managed_sessions' in tables:
                rows = db.execute('SELECT session_id,body FROM managed_sessions WHERE active=1 ORDER BY session_id LIMIT 101').fetchall()
                if len(rows) > 100:
                    raise StorageUnavailable()
                for row in rows:
                    body = json.loads(row['body'])
                    item = {'session_id': row['session_id'], 'symbol': body.get('symbol'),
                            'engine': body.get('engine', 'legacy'), 'state': body.get('status')}
                    h = db.execute('SELECT value FROM control WHERE name=?', ('runtime_health:' + row['session_id'],)).fetchone() if 'control' in tables else None
                    if h:
                        health = json.loads(h[0])
                        stamp = float(health['observed_at'])
                        if not math.isfinite(stamp):
                            raise ValueError('Invalid health time')
                        age = clock() - stamp
                        stopped = health.get('service_stopped') is True or health.get('state') in ('CLOSED', 'MONITOR_STOPPED')
                        item['monitor'] = {'health': 'STOPPED' if stopped else ('FRESH' if 0 <= age <= 90 else 'STALE'),
                                           'observed_at': stamp}
                    else:
                        item['monitor'] = {'health': 'NOT_OBSERVED'}
                    sessions.append(item)
            return {'storage': 'AVAILABLE', 'observation': 'LOCAL_ONLY', 'exchange_access': 'NOT_CHECKED',
                    'entry_halted': halted, 'active_sessions': sessions, 'intent_counts': counts}
    except (sqlite3.Error, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise StorageUnavailable('Yerel işlem durumu okunamadı.') from None


def capabilities():
    return list_capabilities()
