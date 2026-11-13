"""Read the executed isolated validation artifact; never executes tests from HTTP."""
import hashlib,json
from pathlib import Path
from .binding_catalog import catalog
ROOT=Path(__file__).resolve().parents[1]
REPORT=Path(__file__).with_name('replay_validation.json')

def replay_summary():
    base=dict(schema='chart-replay-summary/1',state='BLOCKED',reason='REPLAY_EVIDENCE_STALE_OR_MISSING',
              total=36,passed_count=0,cases=[],runtime_connected=False,order_authority=False,
              decision='KEEP_LIVE_DISABLED_PENDING_QA01_AND_PHYSICAL_REVIEW')
    try:
        raw=REPORT.read_bytes()
        if len(raw)>4000000:return base
        r=json.loads(raw)
        effects=r['side_effects']
        good=(r['schema']=='chart-replay-validation/1' and r['passed'] is True and r['total']==r['passed_count']==36
              and len(r['cases'])==36 and {c['id'] for c in r['cases']}=={'DR'+str(i).zfill(2) for i in range(1,37)}
              and all(c['passed'] is True and not c['differences'] and all(c['observed'].get(k)==v for k,v in c['expected'].items()) for c in r['cases'])
              and all(type(effects[k]) is int and effects[k]==0 for k in ('network_attempts','order_requests','account_requests','external_messages','execution_store_mutations'))
              and effects['runtime_worker_started'] is False and r['runtime_connected'] is False and r['order_authority'] is False
              and r['identity_golden_verified'] is True and bool(r['source_hashes']) and catalog()['state']=='VERIFIED_TRACEABILITY'
              and all((ROOT/p).resolve().is_relative_to(ROOT) and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_hashes'].items()))
        if not good:return base
        return dict(base,state='VERIFIED_ISOLATED',reason=None,passed_count=36,date=r['date'],
                    report_sha256=hashlib.sha256(raw).hexdigest(),side_effects=effects,
                    open_acceptance=r['open_acceptance'],identity_golden_verified=True,
                    cases=[{k:c[k] for k in ('id','title','passed','expected','observed','amendments')} for c in r['cases']])
    except (OSError,ValueError,KeyError,TypeError,AttributeError):return base
