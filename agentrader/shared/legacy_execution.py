"""Explicit local provenance attestation. Never called by normal store opening."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

from .locking import execution_lock
from .product_registry import EXECUTION_CONTEXT
from .storage_context import tables, execution_context_state, bind_execution


def inspect(db, owner, account_ref):
    existing = tables(db)
    if execution_context_state(db) != 'CONTEXT_UNVERIFIED':
        raise ValueError('ONLY_UNVERIFIED_EXECUTION_STORE_CAN_BE_ATTESTED')
    if not {'control','intents','managed_sessions','plan_versions'} <= existing:
        raise ValueError('LEGACY_EXECUTION_SCHEMA_REQUIRED')
    row = db.execute("SELECT value FROM control WHERE name='plan_owner'").fetchone()
    if not row or row[0] != owner:
        raise ValueError('LEGACY_OWNER_MISMATCH')
    for table in ('managed_sessions','account_commands','exchange_commands','risk_reservations','margin_commands'):
        if table not in existing:
            continue
        for body, in db.execute(f'SELECT body FROM {table}'):
            value = json.loads(body)
            ref = value.get('account_ref')
            if ref is not None and ref != account_ref:
                raise ValueError('LEGACY_ACCOUNT_MISMATCH')
    return dict(state='EXPLICIT_PROVENANCE_ATTESTATION_REQUIRED', context=EXECUTION_CONTEXT,
                owner_verified=True, historical_exchange_acceptance=False, financial_execution_authorized=False)


def attest(path, owner, account_ref, *, context, apply=False):
    if context != 'usdm-demo' or not re.fullmatch('[a-f0-9]{64}', account_ref) or not owner:
        raise ValueError('EXPLICIT_DEMO_OWNER_ACCOUNT_REQUIRED')
    path = Path(path).resolve()
    with execution_lock():
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as source:
            report = inspect(source, owner, account_ref)
        if not apply:
            return report | {'applied': False}
        with closing(sqlite3.connect(path.as_uri()+'?mode=rw',uri=True)) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                inspect(db, owner, account_ref)
                backup = path.with_name(path.name+'.before-context-'+uuid.uuid4().hex+'.bak')
                with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as source:
                    with closing(sqlite3.connect(backup)) as destination:
                        source.backup(destination)
                # bind_execution commits only the new namespace; all legacy identities stay unchanged.
                bind_execution(db)
            except BaseException:
                db.rollback()
                raise
    return report | {'state':'CONTEXT_ATTESTED','applied':True,'backup':str(backup)}
