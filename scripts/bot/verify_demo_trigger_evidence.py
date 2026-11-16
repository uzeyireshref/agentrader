"""Read-only post-cleanup native-trigger evidence, including late trigger races."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.bot.run_demo_trigger_acceptance import native_result,verify_generated_fill
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.history_reconciliation import HistoryReads


def verify(report_path,database=Path('data/execution.sqlite3')):
    source=json.loads(report_path.read_text(encoding='utf-8'))
    if source.get('final_flat') is not True or source['state'] not in ('PASSED','PARTIAL','STOPPED'):
        raise ValueError('COMPLETED_FLAT_REPORT_REQUIRED')
    x=HistoryReads(DemoExchange(Config.load()));x.sync_time()
    import hashlib
    if hashlib.sha256(x.config.api_key.encode()).hexdigest()!=source['account_ref']:raise ValueError('ACCOUNT_MISMATCH')
    result=dict(schema='demo-trigger-evidence/1',source=str(report_path),observed_at=time.time(),read_only=True,order_requests=0,cases=[])
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        sessions=[json.loads(row[0]) for row in db.execute('SELECT body FROM managed_sessions')]
    for case in source['cases']:
        matches=[s for s in sessions if s.get('plan',{}).get('plan_id')==case['plan']['plan_id']]
        if len(matches)!=1 or matches[0]['active']:raise ValueError('CLOSED_OWNED_SESSION_REQUIRED')
        s=matches[0]
        if s['account_ref']!=source['account_ref'] or s['plan']!=case['plan']:raise ValueError('SESSION_BINDING_MISMATCH')
        responses=[x.get(p['path'],{'clientAlgoId':p['params']['clientAlgoId']}) for p in s['protections']]
        triggered=native_result(s['protections'],responses);fills=[]
        for trigger in triggered:
            order=x.get('/fapi/v1/order',{'symbol':s['symbol'],'orderId':trigger['order_id']})
            verify_generated_fill(trigger,order,s);fills.append(order)
        result['cases'].append(dict(requested_trigger=case['requested_trigger'],original_observation=case['state'],native_triggers=triggered,
            requested_native_proven=any(t['kind']==case['requested_trigger'] for t in triggered),algo_responses=responses,generated_fills=fills))
    result['requests']=x.calls
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args()
    r=verify(args.report);out=args.report.with_name(args.report.stem+'-evidence.json')
    out.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(report=str(out),proven=[c['requested_trigger'] for c in r['cases'] if c['requested_native_proven']])))
