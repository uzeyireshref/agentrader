"""Reproduce current offline acceptance and bind all runtime, frontend and test sources."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/hardening-20261117'


def source_paths():
    result=set()
    for directory in ('agentrader','tests','scripts/acceptance','frontend/src','frontend/tests','frontend/scripts','docs/development/hardening-20261117'):
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and (path.suffix in ('.py','.ts','.tsx','.json','.css','.md') or directory.startswith('frontend/')):
                result.add(path)
    for name in ('package.json','package-lock.json','tsconfig.json','vite.config.ts','index.html'):
        result.add(ROOT/'frontend'/name)
    result.update(ROOT/p for p in ('scripts/maintenance/benchmark_hardening.py','scripts/maintenance/attest_execution_context.py'))
    result.update(p for p in (ROOT/'agentrader/web_assets').rglob('*') if p.is_file())
    result.update(ROOT/p for p in ('docs/development/exchange-operations-20261115/packages.json','docs/development/exchange-operations-20261115/G23-scope.json'))
    return sorted(result)


def hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths()}


def run(name, args, cwd=ROOT):
    started=time.monotonic()
    result=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',env=os.environ|{'PYTHONIOENCODING':'utf-8'})
    (OUT/(name+'.txt')).write_text(result.stdout,encoding='utf-8')
    print(name+': '+str(result.returncode),flush=True)
    if result.returncode:raise RuntimeError('ACCEPTANCE_FAILED: '+name)
    return result.stdout,round(time.monotonic()-started,3)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    current=OUT/'release-validation.json'
    if current.exists():
        current.replace(OUT/('release-validation.previous-'+uuid.uuid4().hex+'.json'))
    # Regenerate affected evidence, never rewrite old exchange-development reports.
    run('binding-evidence',[sys.executable,'scripts/chart/build_binding_evidence.py'])
    run('chart-replay',[sys.executable,'-c',
        "import json; from scripts.chart.run_chart_p7 import run_suite; from pathlib import Path; r=run_suite(); Path('reports/hardening-20261117/chart-replay.json').write_text(json.dumps(r,indent=2),encoding='utf-8'); assert r['passed']; Path('agentrader/replay_validation.json').write_text(json.dumps(r,indent=2)+'\\n',encoding='utf-8'); print(r['passed_count'])"])
    npm=['cmd.exe','/d','/c','npm'] if os.name=='nt' else ['npm']
    run('frontend-build',npm+['run','build'],ROOT/'frontend')
    before=hashes()
    output,seconds=run('python-tests',[sys.executable,'-m','unittest','discover','-s','tests'])
    tests=int(re.search(r'Ran (\d+) tests?',output).group(1))
    if not re.search(r'^OK\s*$',output,re.M) or 'skipped=' in output:raise RuntimeError('PYTHON_ACCEPTANCE_INCOMPLETE')
    output,front_seconds=run('frontend-tests',npm+['test'],ROOT/'frontend')
    front_tests=int(re.search(r'# tests (\d+)',output).group(1))
    if not re.search(r'# fail 0\b',output) or not re.search(r'# skipped 0\b',output):raise RuntimeError('FRONTEND_ACCEPTANCE_INCOMPLETE')
    run('reliability',[sys.executable,'scripts/acceptance/run_reliability.py','--output',str(OUT/'reliability.json')])
    run('data-access-benchmark',[sys.executable,'scripts/maintenance/benchmark_hardening.py','--output',str(OUT/'after-data-access.json')])
    run('indicator-benchmark',npm+['exec','--','tsx','scripts/benchmark-indicators.ts',str(OUT/'indicators.json')],ROOT/'frontend')
    after=hashes()
    if before!=after:raise RuntimeError('SOURCES_CHANGED_DURING_ACCEPTANCE')
    reliability=json.loads((OUT/'reliability.json').read_text(encoding='utf-8'))
    replay=json.loads((OUT/'chart-replay.json').read_text(encoding='utf-8'))
    report=dict(schema='reliability-priority-validation/1',hardening_scope=True,baseline_regression_tests=1672,
        full_regression=dict(tests_run=tests,seconds=seconds,result='OK',skipped=0),
        frontend=dict(tests_run=front_tests,seconds=front_seconds,result='OK',skipped=0,build='OK'),
        reliability_suite=reliability,chart_replay=dict(passed=replay['passed_count'],total=replay['total']),
        authenticated_exchange_acceptance='NOT_RUN',financial_exchange_actions_performed=False,
        browser_physical_acceptance='NOT_RUN',source_sha256=after)
    (OUT/'release-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    sys.path.insert(0,str(ROOT))
    from agentrader.acceptance.release import verify
    result=verify(ROOT,OUT/'release-validation.json');print(json.dumps(result),flush=True)
    return 0 if result['status']=='LOCAL_SCOPE_VERIFIED_EXTERNAL_ACCEPTANCE_PENDING' else 1

if __name__=='__main__':raise SystemExit(main())
