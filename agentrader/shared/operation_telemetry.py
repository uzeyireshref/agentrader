"""Bounded numeric lifecycle observations, committed with their journal state."""
import math

STREAM_STATES={'STREAM_RECONNECTING','STREAM_CONNECTED','STREAM_REST_RECONCILED'}
PENDING={'SUBMITTING','UNKNOWN','READ_FAILED'}


def schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS operation_timing (
        command_id TEXT PRIMARY KEY, unresolved_since REAL NOT NULL,
        recovered_at REAL, recovery_seconds REAL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS operation_counters (
        kind TEXT PRIMARY KEY, count INTEGER NOT NULL, last_seen REAL NOT NULL)''')


def command_state(db,command_id,state,now):
    if not math.isfinite(now) or now<0:raise ValueError('OPERATION_CLOCK_INVALID')
    if state in PENDING:
        db.execute('INSERT OR IGNORE INTO operation_timing VALUES (?,?,NULL,NULL)',(command_id,now))
    else:
        db.execute('''UPDATE operation_timing SET recovered_at=?,
            recovery_seconds=CASE WHEN ?>=unresolved_since THEN ?-unresolved_since ELSE NULL END
            WHERE command_id=? AND recovered_at IS NULL''',(now,now,now,command_id))


def runtime_note(db,state,now):
    if state not in STREAM_STATES:return
    if not math.isfinite(now) or now<0:raise ValueError('OPERATION_CLOCK_INVALID')
    schema(db)
    db.execute('''INSERT INTO operation_counters VALUES (?,1,?) ON CONFLICT(kind)
        DO UPDATE SET count=count+1,last_seen=excluded.last_seen''',(state,now))
