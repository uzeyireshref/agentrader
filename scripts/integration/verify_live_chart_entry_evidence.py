"""Independent GET/SQLite-read-only audit of the actual chart entry chain."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.integration.run_live_chart_entry_acceptance import chart_session
from agentrader.application.settings import WebSettings
from agentrader.chart.chart_bindings import BindingService,binding_hash
from agentrader.integration.chart_execution import _key,execution_plan
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.history_reconciliation import HistoryReads,terminal_response
from agentrader.chart.local_chart_events import closed_candidate
from agentrader.bot.plans import digest
from agentrader.integration.shadow_tracking import PROFILE


def verify(path):
    source=json.loads(path.read_text(encoding='utf-8'));settings=WebSettings.load()
    if source.get('final_flat') is not True or not source.get('plan_id'):raise ValueError('COMPLETED_CHART_PLAN_REQUIRED')
    x=HistoryReads(DemoExchange(Config.load()));x.sync_time()
    if hashlib.sha256(x.config.api_key.encode()).hexdigest()!=source['account_ref']:raise ValueError('ACCOUNT_MISMATCH')
    b=BindingService(settings.application_database,settings.owner).show('main',source['binding_id'])
    with closing(sqlite3.connect(settings.application_database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        event_id=source['event']['event_id']
        event_row=db.execute('SELECT body,evidence FROM app_shadow_events WHERE event_id=? AND owner=?',(event_id,settings.owner)).fetchone()
        if not event_row:raise ValueError('EVENT_MISSING')
        event,evidence=map(json.loads,event_row)
        preview_row=db.execute('SELECT body FROM app_signal_previews WHERE event_id=? AND version=? AND owner=?',(event_id,source['preview_version'],settings.owner)).fetchone()
        if not preview_row:raise ValueError('PREVIEW_MISSING')
        preview=json.loads(preview_row[0])
    expected_id=binding_hash(dict(profile=PROFILE,owner=settings.owner,workspace='main',binding_id=b['binding_id'],revision=b['revision'],
        definition_hash=b['definition_hash'],candle_time=event['candle_time'],kind=event['kind']))
    if (expected_id!=event_id or event!=source['event'] or event['evidence_hash']!=binding_hash(evidence['context'])
            or binding_hash(evidence['definition'])!=b['definition_hash']):raise ValueError('EVENT_EVIDENCE_MISMATCH')
    candidate=closed_candidate(b,evidence['context'])
    if not candidate or any(candidate[k]!=event[k] for k in candidate if k not in ('schema','profile')):raise ValueError('REAL_RULE_NOT_PROVEN')
    if (binding_hash({k:v for k,v in preview.items() if k!='content_hash'})!=preview['content_hash']
            or preview['content_hash']!=source['preview_hash'] or preview['plan_digest']!=binding_hash(preview['plan'])):
        raise ValueError('PREVIEW_HASH_MISMATCH')
    with closing(sqlite3.connect(settings.execution_database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        row=dict(db.execute('SELECT * FROM plan_versions WHERE plan_id=? AND version=1 AND owner=?',(source['plan_id'],settings.owner)).fetchone())
        plan=json.loads(row['body'])
        source_row=db.execute('SELECT value FROM control WHERE name=?',(_key(plan),)).fetchone()
        if not source_row:raise ValueError('SOURCE_BINDING_MISSING')
        binding=json.loads(source_row[0])
        sessions=[json.loads(v[0]) for v in db.execute('SELECT body FROM managed_sessions')]
        s=chart_session(sessions,source['plan_id'])
        intent=dict(db.execute('SELECT * FROM intents WHERE client_id=?',(s['entry_id'],)).fetchone())
    if (row['digest']!=digest(plan) or source['plan_digest']!=row['digest'] or execution_plan(preview,settings.owner)!=plan
            or plan['analysis_ref']!='shadow-event:'+event_id or row['state']!='CLOSED' or s['active']):
        raise ValueError('EXECUTION_PLAN_CHAIN_MISMATCH')
    if (binding_hash({k:v for k,v in binding.items() if k!='content_hash'})!=binding['content_hash']
            or binding['account_ref']!=source['account_ref'] or binding['execution_digest']!=row['digest']
            or binding['preview_hash']!=preview['content_hash'] or binding['risk_profile_hash']!=preview['risk_profile_hash']):
        raise ValueError('DURABLE_SOURCE_BINDING_MISMATCH')
    if s['prepared']['entry']['params']!=json.loads(intent['params']):raise ValueError('ENTRY_INTENT_MISMATCH')
    order=x.get('/fapi/v1/order',dict(symbol=plan['symbol'],origClientOrderId=s['entry_id']))
    terminal=terminal_response(intent,order)
    return dict(schema='live-chart-entry-evidence/1',state='VERIFIED',observed_at=time.time(),source_report=str(path),
        original_runner_state=source['state'],original_runner_error=source.get('error_type'),read_only=True,order_requests=0,
        drawing_id=source['drawing_id'],binding_id=b['binding_id'],event_id=event_id,event_kind=event['kind'],event_candle_time=event['candle_time'],
        event_level=event['level'],event_closed_price=event['closed_price'],plan_id=plan['plan_id'],plan_digest=row['digest'],
        account_ref=source['account_ref'],risk_profile_hash=preview['risk_profile_hash'],session_id=s['id'],
        exchange_entry=order,entry_terminal=terminal,plan_state=row['state'],active_session=s['active'],requests=x.calls)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args()
    r=verify(args.report);out=args.report.with_name(args.report.stem+'-evidence.json')
    out.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(report=str(out),state=r['state'],entry_terminal=r['entry_terminal'],order_id=r['exchange_entry']['orderId'])))
