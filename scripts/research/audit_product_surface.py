"""Read-only product coverage and source evidence for the research baseline."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.bot.plan_v2 import validate_v2
from agentrader.bot.plans import example_plan
from agentrader.shared.exchange import allowed_requests

DATA=ROOT/'docs/research/crypto-bot-20261115'
OUT=ROOT/'reports/crypto-bot-research-20261115'


def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    contracts=json.loads((DATA/'detailed-operation-contracts.json').read_text(encoding='utf-8'))
    refs={}
    tests=[]
    hashes={}
    for path in sorted((ROOT/'agentrader').rglob('*.py')):
        content=path.read_bytes()
        hashes[path.relative_to(ROOT).as_posix()]=hashlib.sha256(content).hexdigest()
        tree=ast.parse(content.decode('utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith(('/fapi/','/dapi/','/eapi/','/sapi/','/api/')):
                if path.name not in ('exchange.py','capabilities.py'):
                    refs.setdefault(node.value,[]).append(dict(file=path.relative_to(ROOT).as_posix(),line=node.lineno))
    for path in sorted((ROOT/'tests').glob('test_*.py')):
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                for fn in cls.body:
                    if isinstance(fn,ast.FunctionDef) and fn.name.startswith('test_'):
                        tests.append(dict(test_id=path.stem+'.'+cls.name+'.'+fn.name,file=path.relative_to(ROOT).as_posix(),line=fn.lineno))
    rows=[]
    for contract in contracts['contracts']:
        path='/'+contract['path'].lstrip('/')
        um=contract['product']=='derivatives_trading_usds_futures'
        enabled=(contract['method'],path) in allowed_requests()
        row=dict(operation_id=contract['operation_id'],product=contract['product'],method=contract['method'],path=path,
                 name=contract['name'],sdk_source=contract['sdk_contract']['source_url'],source_contract='SDK_FIELDS_AND_RULES_EXTRACTED',
                 adapter_allowed=enabled,source_references=refs.get(path,[]),
                 product_entry='DEMO_USD_M_ONLY' if um else 'NO_SUPPORTED_PRODUCT_ENTRY',
                 support='ROUTE_PRESENT_WORKFLOW_RESTRICTED' if enabled else ('OTHER_CLIENT_REFERENCE' if um and path in refs else 'MISSING_PRODUCT_OR_ROUTE'),
                 exchange_execution_acceptance='NOT_RUN',
                 workflow_evidence_limit='Allowed route does not establish arbitrary user-command support. See WORKFLOW-CAPABILITY-REVIEW.md.')
        rows.append(row)
    snapshots=OUT/'official-snapshots'
    summary=[]
    probe_rows=[]
    for name,product,key in [('usdm_demo_info','USD-M','symbols'),('spot_info','SPOT','symbols'),('coinm_info','COIN-M','symbols'),('options_info','OPTIONS','optionSymbols')]:
        source=snapshots/(name+'.json')
        obj=json.loads(source.read_text(encoding='utf-8'))
        symbols=obj[key]
        active=[s for s in symbols if s.get('status',s.get('contractStatus'))=='TRADING']
        features=Counter()
        filters=Counter()
        for s in active:
            for k,v in s.items():
                if type(v) is bool and v:
                    features[k]+=1
            filters.update(f['filterType'] for f in s['filters'])
            p=example_plan()
            p.update(schema_version=2,product=product,symbol=s['symbol'],execution=dict(strategy='SINGLE',leverage=20,margin_mode='CROSSED'))
            try:
                validate_v2(p)
                result='PLAN_SCHEMA_ACCEPTED'
                error=None
            except ValueError as exc:
                result='PLAN_SCHEMA_REJECTED'
                error=str(exc)
            probe_rows.append(dict(product=product,symbol=s['symbol'],result=result,reason=error,exchange_acceptance='NOT_RUN'))
        summary.append(dict(product=product,source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                            all_symbols=len(symbols),active_symbols=len(active),filters=dict(filters),features=dict(features),
                            contract_types=dict(Counter(s.get('contractType','SPOT') for s in active)),
                            quote_assets=dict(Counter(s.get('quoteAsset','UNKNOWN') for s in active)),
                            underlying_count=len(set(s.get('underlying',s.get('pair',s['symbol'])) for s in active)),
                            expiry_count=len(set(s.get('expiryDate',s.get('deliveryDate')) for s in active)),
                            option_sides=dict(Counter(s.get('side','NA') for s in active))))
    write(DATA/'operation-support-audit.json',dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),count=len(rows),
          counts=dict(Counter(r['support'] for r in rows)),operations=rows,code_sha256=hashes))
    write(OUT/'product-symbol-surface-audit.json',dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),
          scope='Public metadata and normal-plan schema probes. No order execution.',products=summary,
          probe_count=len(probe_rows),probe_counts=dict(Counter((r['product']+':'+r['result']) for r in probe_rows)),probes=probe_rows,exchange_mutations=0))
    write(OUT/'existing-test-evidence-index.json',dict(count=len(tests),tests=tests))
    print(json.dumps(dict(operation_counts=dict(Counter(r['support'] for r in rows)),products=summary,plan_probe_count=len(probe_rows),test_method_count=len(tests)),ensure_ascii=False))


if __name__=='__main__':
    main()
