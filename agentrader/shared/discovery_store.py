"""Separate discovery cache/audit ledger, partitioned by context and credential."""
import json
from pathlib import Path
import sqlite3
import time

from agentrader.bot.plans import canonical,digest
from agentrader.shared.storage_context import tables


class DiscoveryStore:
    def __init__(self,path=Path('data/discovery.sqlite3')):
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,timeout=10);self.db.row_factory=sqlite3.Row
        existing=tables(self.db)
        if existing-{'sqlite_sequence'} and ('discovery_contexts' not in existing or existing&{'intents','execution_namespace','plan_versions','candles','app_market_context','app_schema_migrations'}):
            self.db.close();raise ValueError('DISCOVERY_REQUIRES_SEPARATE_DATABASE')
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS discovery_contexts (
                context_ref TEXT PRIMARY KEY,body TEXT NOT NULL,digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS discovery_runs (
                run_id TEXT PRIMARY KEY,context_ref TEXT NOT NULL,kind TEXT NOT NULL,observed_ms INTEGER NOT NULL,
                body TEXT NOT NULL,digest TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS discovery_latest ON discovery_runs(context_ref,kind,observed_ms);
        ''')

    def close(self):self.db.close()

    def _validate(self,report,identity):
        if (report.get('identity')!=identity or report.get('read_only') is not True or report.get('write_permission')!='NOT_VERIFIED' or
                report.get('financial_execution_authorized') is not False or report.get('accounting_adopted') is not False):
            raise ValueError('DISCOVERY_REPORT_CONTEXT_OR_AUTHORITY_INVALID')
        if report.get('kind') not in ('ACCOUNT_DISCOVERY','NORMAL_ORDER_LOOKUP') or type(report.get('observed_ms')) is not int:
            raise ValueError('DISCOVERY_REPORT_SCHEMA_INVALID')

    def save(self,report):
        identity=report['identity'];self._validate(report,identity);encoded=canonical(report)
        with self.db:
            old=self.db.execute('SELECT body,digest FROM discovery_contexts WHERE context_ref=?',(identity['context_ref'],)).fetchone()
            if old and (old['body']!=canonical(identity) or old['digest']!=digest(identity)):raise ValueError('DISCOVERY_CONTEXT_IMMUTABLE')
            self.db.execute('INSERT OR IGNORE INTO discovery_contexts VALUES(?,?,?)',(identity['context_ref'],canonical(identity),digest(identity)))
            old=self.db.execute('SELECT body,digest FROM discovery_runs WHERE run_id=?',(report['run_id'],)).fetchone()
            if old:
                if old['body']!=encoded or old['digest']!=digest(report):raise ValueError('DISCOVERY_RUN_IMMUTABLE')
                return False
            self.db.execute('INSERT INTO discovery_runs VALUES(?,?,?,?,?,?)',
                (report['run_id'],identity['context_ref'],report['kind'],report['observed_ms'],encoded,digest(report)))
        return True

    def latest(self,identity,*,kind='ACCOUNT_DISCOVERY',max_age=300,now_ms=None):
        if kind not in ('ACCOUNT_DISCOVERY','NORMAL_ORDER_LOOKUP') or type(max_age) is not int or not 1<=max_age<=3600:raise ValueError('DISCOVERY_CACHE_QUERY_INVALID')
        result={'identity':dict(identity),'write_permission':'NOT_VERIFIED','financial_execution_authorized':False,'read_only':True}
        row=self.db.execute('SELECT * FROM discovery_runs WHERE context_ref=? AND kind=? ORDER BY observed_ms DESC,rowid DESC LIMIT 1',
                            (identity['context_ref'],kind)).fetchone()
        if row is None:return result|{'evidence_status':'NOT_FOUND'}
        context=self.db.execute('SELECT * FROM discovery_contexts WHERE context_ref=?',(identity['context_ref'],)).fetchone()
        try:
            report=json.loads(row['body']);self._validate(report,identity)
            if (digest(report)!=row['digest'] or row['observed_ms']!=report['observed_ms'] or row['kind']!=report['kind'] or context is None or
                    json.loads(context['body'])!=identity or context['digest']!=digest(identity)):raise ValueError('CORRUPT')
        except (ValueError,TypeError,KeyError):return result|{'evidence_status':'CORRUPT'}
        now_ms=int(time.time()*1000) if now_ms is None else now_ms;age=(now_ms-report['observed_ms'])/1000
        return result|{'evidence_status':'FRESH' if 0<=age<=max_age else 'STALE','age_seconds':age,'report':report}
