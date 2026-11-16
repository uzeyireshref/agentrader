"""Validate real Demo strategy observation against frozen production sources."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib,json,re
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/chart-interface-g11-20261115'

def main():
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def read(p):return json.loads((OUT/p).read_text(encoding='utf-8-sig'))
    live=read('live-current/observation.json');probe=read('public-probe.json');replay=read('replay.log')
    assert probe['passed'] and len(probe['checks'])==5
    assert live['state']=='COMPLETED' and live['passed'] and len(live['checks'])==11 and all(c['passed'] for c in live['checks'])
    assert live['scope']=='REAL_DEMO_PUBLIC_FEED_PRODUCTION_HTTP_ADAPTER_SEPARATE_STRATEGY_PROCESS'
    assert all(sha(ROOT/p)==h for p,h in live['source_sha256'].items()),'Observed sources changed'
    assert live['account_requests']==live['order_requests']==0 and not (OUT/'live-current/runtime/execution.db').exists()
    assert live['controlled_subscription_pause']['state']=='PAUSED' and live['immediate_restart_result']['state']=='NO_CHANGE'
    phases=[[json.loads(line) for line in (OUT/'live-current'/f'strategy-phase{i}.jsonl').read_text(encoding='utf-8').splitlines()] for i in (1,2)]
    assert phases[1][0]['state']=='NO_CHANGE','Restarted production process must deduplicate before next close'
    decisions=[e for phase in phases for e in phase if e['state']=='APPLIED']
    assert len(decisions)>=3 and len({e['drawing_id'] for e in decisions})==1 and len({e['bar_time'] for e in decisions})==len(decisions)
    for e in decisions:
        assert e['indicator']['state']=='READY' and not e['indicator']['open_candle_used'] and e['indicator']['effective_time']==e['bar_time']
        assert e['indicator']['consumed_data_hash']==e['source_readiness']['consumed_data_hash']
        ratio=e['query']['result']['value'];assert Fraction(int(ratio['numerator']),int(ratio['denominator']))==Fraction(e['geometry']['anchors'][0]['price'])
        note=json.loads(e['note']);assert note['bar_time']==e['bar_time'] and note['context_id']==e['context_id']
    python=(OUT/'python-final.log').read_text(encoding='utf-8-sig');strategy=(OUT/'strategy-tests.log').read_text(encoding='utf-8-sig')
    assert '1259 passed' in python and '7 passed' in strategy
    assert replay['passed'] and replay['count']==replay['total']==36
    manifest=json.loads((ROOT/'agentrader/binding_evidence.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in manifest['runtime_sources'])
    prior=json.loads((ROOT/'reports/chart-interface-g10-20261115/validation.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/p)==h for p,h in prior['frontend_build_sha256'].items())
    assert all(sha(ROOT/p)==h for p,h in prior['source_sha256'].items() if p.startswith('frontend/'))
    sources={p for folder in ('agentrader','tests') for p in (ROOT/folder).rglob('*.py')}
    sources.update(ROOT/p for p in ['agentrader/binding_evidence.json','agentrader/replay_validation.json','scripts/chart/build_binding_evidence.py','scripts/integration/observe_g11_chart_strategy.py','scripts/integration/finalize_g11_report.py','docs/chart/DEMO-STRATEGY-G11.md','docs/integration/history/46-BOT-GRAFIK-ORTAK-ARAYUZ-VE-CIZIM-ADAPTORU-GELISTIRME-PLANI.md'])
    validation=dict(schema='chart-interface-g11-validation/1',state='PASS',date='2026-11-15',scope=live['scope'],live_observation='live-current/observation.json',
        strategy='closed-ema20-horizontal/1',closed_bar_decisions=len(decisions),one_bot_drawing=True,manual_sentinel_unchanged=True,server_and_strategy_restart_deduplicated=True,
        stale_subscription_absence_blocks_writes=True,python_passed=1259,python_log='python-final.log',strategy_tests=7,strategy_log='strategy-tests.log',replay_passed=36,replay_log='replay.log',account_requests=0,order_requests=0,
        frontend=dict(source_and_build_unchanged_from_g10=True,tests='G10 360 passed; unchanged source/build verified'),migration=dict(current=13,new=False),
        limitations=live['limitations'],runtime_manifest_verified=True,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(sources)},frontend_build_sha256=prior['frontend_build_sha256'],
        evidence_sha256={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.suffix in ('.json','.jsonl','.log','.md') and p.name!='validation.json'})
    (OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(state='PASS',decisions=len(decisions),python=1259,replay=36,source_files=len(sources))))

if __name__=='__main__':main()
