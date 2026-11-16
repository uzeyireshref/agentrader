"""Validate the 5–8 delivery, inventory coverage and installed skill identity."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/research/crypto-bot-20261115'
REPORT=ROOT/'reports/crypto-bot-research-20261115'


def load(p):return json.loads(p.read_text(encoding='utf-8'))


def main():
    findings=load(DATA/'final-gap-register.json')
    baseline=load(DATA/'operation-support-audit.json')
    assert len(findings['operation_mapping'])==555
    assert {r['operation_id'] for r in baseline['operations']}=={r['operation_id'] for r in findings['operation_mapping']}
    assert len(findings['findings'])==34 and all(r['findings'] for r in findings['operation_mapping'])
    ids={f['id'] for f in findings['findings']}
    assert all(set(r['findings'])<=ids for r in findings['operation_mapping'])
    assert len(findings['official_supplements'])==3
    confirmed={(r['product'],r['method'],r['path']) for r in baseline['operations']}
    for r in findings['official_supplements']:
        assert (r['product'],r['method'],r['path']) not in confirmed
        confirmed.add((r['product'],r['method'],r['path']))
    assert len(confirmed)==558
    assert len(findings['implementation_candidates'])==3
    assert not findings['candidates_in_confirmed_count']
    repos=load(DATA/'repository-assessment.json')
    assert len(repos['repositories'])==20
    assert all(re.fullmatch('[a-f0-9]{40}',r['commit']) for r in repos['repositories'])
    for repo in repos['repositories']:
        assert repo['evidence']
        for item in repo['evidence']:
            assert hashlib.sha256((ROOT/item['local_file']).read_bytes()).hexdigest()==item['sha256']
    env=load(DATA/'environment-capability-matrix.json')
    assert len(env['products'])==10 and len(env['comparisons'])==3
    assert all(r['financial_execution_acceptance']=='NOT_RUN' for r in env['products'])
    from build_environment_comparison import canonical
    assert canonical([{'stepSize':'0.0100','filterType':'LOT_SIZE'},{'filterType':'PRICE_FILTER','tickSize':'1.0'}])==canonical([{'tickSize':'1','filterType':'PRICE_FILTER'},{'filterType':'LOT_SIZE','stepSize':'0.01'}])
    assert canonical({'minQty':'0.1'})!=canonical({'minQty':'0.2'})
    source=ROOT/'tools/skills/agentrader-exchange-development'
    installed=Path(repos['selected_skill']['installed_path'])
    skill_files=list(source.rglob('*'))
    compared=[]
    for path in skill_files:
        if path.is_file():
            other=installed/path.relative_to(source)
            assert other.is_file() and other.read_bytes()==path.read_bytes()
            compared.append(path.relative_to(source).as_posix())
    assert compared and (installed/'SKILL.md').exists()
    names=['RESEARCH-CLOSURE-5-8.md','ENVIRONMENT-REVIEW.md','SOURCE-CONFLICT-RESOLUTIONS.md','REPOSITORY-SELECTION.md','FINAL-GAP-REGISTER.md']
    for name in names:
        text=(DATA/name).read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if not link.startswith(('http://','https://')):
                assert (DATA/link).exists(),(name,link)
    result=dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),status='PASS',
                delivery_scope='Research steps 5-8, not full exchange execution certification',
                baseline_mapped=555,official_supplement_count=3,confirmed_inventory=558,implementation_only_candidates=3,
                findings=34,repository_reviews=20,environment_products=10,public_comparisons=3,
                installed_skill=installed.as_posix(),skill_files_compared=compared,
                exchange_mutations=0,runtime_feature_changes=0,
                overall_research_closure='CONDITIONAL_CRITICAL_CONTRACT_GATES_REMAIN',
                evidence_documents={name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in names})
    (REPORT/'research-closure-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
