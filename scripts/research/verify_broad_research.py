"""Check research deliverable integrity and distinguish evidence layers."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/research/crypto-bot-20261115'
OUT=ROOT/'reports/crypto-bot-research-20261115'


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def main():
    contracts=read(DATA/'detailed-operation-contracts.json')
    support=read(DATA/'operation-support-audit.json')
    lifecycle=read(DATA/'operation-lifecycle-requirements.json')
    ids={x['operation_id'] for x in contracts['contracts']}
    assert len(ids)==555
    assert ids=={x['operation_id'] for x in support['operations']}=={x['id'] for x in lifecycle['operations']}
    assert all(x['comparison']=='MATCHED_SDK_ROUTE' for x in contracts['contracts'])
    assert len(contracts['websocket_contracts'])==83
    assert all(x['websocket_method'] for x in contracts['websocket_contracts'])
    assert len({(x['product'],x['websocket_method']) for x in contracts['websocket_contracts']})==83
    for kind in ('sdk','models'):
        manifest=read(OUT/f'official-snapshots/{kind}/manifest.json')
        assert all(x['status']==200 for x in manifest['files'])
        assert all((OUT/f'official-snapshots/{kind}'/x['file']).exists() for x in manifest['files'])
    for name,sha in support['code_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha, name
    assert read(DATA/'official-response-models.json')['count']==2010
    audit=read(OUT/'fresh-extended-symbol-scenario-audit.json')
    assert audit['source_symbols']==528 and audit['executed_symbols']==527
    assert audit['executed_cases']==527*62==32674
    assert sum(audit['counts'].values())==32674
    assert audit['counts']==dict(ALIGNED=30039,REFERENCE_GAP=2635)
    assert set(audit['gaps_by_case'])=={'CALLBACK_7.5','CALLBACK_10','CALLBACK_20','RESPONSE_ACK','RESPONSE_RESULT'}
    assert audit['blocked_symbols'][0]['symbol']=='SXPUSDT'
    boundaries=read(OUT/'filter-boundary-audit.json')
    assert boundaries['count']==1054
    products=read(OUT/'product-symbol-surface-audit.json')
    assert products['probe_count']==len(products['probes'])==3720
    assert sum(x['active_symbols'] for x in products['products'])==3720
    spottext=(OUT/'official-snapshots/spot-rest-api.md').read_text(encoding='utf-8')
    routes=set(re.findall(r'^\s*(GET|POST|PUT|DELETE|PATCH)\s+(/api/v3/[^\s`]+)',spottext,re.M))
    baseline={(x['method'],'/'+x['path']) for x in contracts['contracts'] if x['product']=='spot'}
    assert routes==baseline and len(routes)==48
    documents=['BROAD-RESEARCH-1-5.md','PRODUCT-CONTRACT-DECISIONS.md','WORKFLOW-CAPABILITY-REVIEW.md','FAILURE-RECOVERY-REVIEW.md','SYMBOL-SCENARIO-COVERAGE.md','BOUNDED-OPEN-QUESTIONS.md']
    for doc in documents:
        text=(DATA/doc).read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if not link.startswith(('https://','http://')):
                assert (DATA/link).exists(), (doc,link)
    payload=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),status='PASS',
                 scope='Source extraction, source hashes, evidence counts, ID completeness and document links',
                 baseline_rest=555,websocket_api_methods=83,response_model_classes=2010,
                 independent_spot_markdown_routes=48,source_operation_statuses=dict(Counter(x['support'] for x in support['operations'])),
                 fresh_validator_cases=32674,reference_aligned=30039,reference_gaps=2635,boundary_probes=1054,
                 product_plan_schema_probes=3720,blocked_symbol='SXPUSDT',
                 observed_regression_run=dict(command='python -m unittest discover -s tests',tests_run=1262,seconds=180.841,result='OK',
                    evidence='Observed exec output in the 1-5 research run. Not rerun by this integrity script.'),
                 exchange_mutations=0,exchange_execution_acceptance='NOT_RUN',
                 bounded_questions='docs/research/crypto-bot-20261115/BOUNDED-OPEN-QUESTIONS.md',
                 artifact_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA/x for x in documents]+[DATA/'detailed-operation-contracts.json',DATA/'operation-support-audit.json',DATA/'operation-lifecycle-requirements.json',DATA/'official-response-models.json']})
    (OUT/'broad-research-verification.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k!='artifact_sha256'},ensure_ascii=False))


if __name__=='__main__':main()
