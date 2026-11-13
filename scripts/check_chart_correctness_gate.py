"""A5 evidence audit. Does not run tests: run the referenced producers first."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(report_name='chart-correctness-gate-20261109.json',next_task='B1'):
    names = {
        'A1': 'chart-render-recovery-browser-20261109.json',
        'A2': 'chart-connection-browser-20261109.json',
        'A3': 'chart-context-races-browser-20261109.json',
        'A4': 'chart-lifecycle-browser-20261109.json',
        'frontend': 'chart-correctness-frontend-20261109.json',
        'backend': 'chart-workspace-validation-20261109.json',
        'history_boundary': 'chart-gram-history-boundary-20261109.json',
    }
    evidence = {key: json.loads((ROOT/'reports'/name).read_text(encoding='utf-8-sig')) for key, name in names.items()}
    checks = {}
    for key, minimum in [('A1',6), ('A2',14), ('A3',11), ('A4',9)]:
        item = evidence[key]
        checks[key] = item['passed'] and len(item['cases']) >= minimum and all(c['passed'] for c in item['cases']) and not item['page_errors']
        checks[key+'_isolated'] = item['account_requests']==0 and item['user_workspace_writes']==0 and not item.get('unexpected_requests', item.get('blocked_requests', []))
    lifecycle = evidence['A4']['cases']
    for label in ['independent_decimal_values_after_live_close_change', 'independent_decimal_values_after_candle_finalization']:
        checks[label] = any(c['name']==label and c['numeric_values']==818 and c['max_error']<=1e-8 for c in lifecycle)
    checks['50_pane_cycles'] = any(c.get('cycles')==50 and c['off_panes']==2 and c['on_panes']==3 for c in lifecycle)
    front, back = evidence['frontend'], evidence['backend']
    checks['frontend'] = front['passed'] and front['tests']==116 and front['build_exit']==0 and front['skipped']==0
    checks['backend_previous_run'] = back['result']=='PASSED' and back['test_count']==675 and back['skipped_count']==0 and back['local_http']['result']=='PASSED' and back['existing_runtime_databases_and_risk_unchanged']
    checks['bundle'] = front['bundle'] in (ROOT/'agentrader/web_assets/index.html').read_text(encoding='utf-8')
    checks['history_boundary'] = evidence['history_boundary']['passed'] and evidence['history_boundary']['older_http_status']==200
    groups = {
        'G01': {'covered': ['React pointer ownership and eight cancellation paths', 'prior browser creation/body/anchor and handle hit-test evidence'], 'remaining': ['R01']},
        'G02': {'covered': ['native/SVG numeric alignment', 'gap/fractional and reversed Fibonacci', 'history and pane lifecycle'], 'remaining': ['R02']},
        'G03': {'covered': ['11 hook races', 'full App delayed reads/bootstrap/preferences', 'isolated HTTP idempotency/conflict/restart', 'prior two-tab UI evidence'], 'remaining': ['R03']},
        'G04': {'covered': ['render recovery', 'controlled App disconnect/stale/old packets/close/new bar/resync', 'history/live races and empty listing boundary'], 'remaining': ['R04','R05']},
        'G05': {'covered': ['independent Decimal fixtures and warmup', 'native values after history/live close/finalization', '50 native series/pane cycles'], 'remaining': ['R06']},
    }
    remaining = [
        {'id':'R01','scope':'Full browser drag cancellation/outside-release matrix and physical second-touch behavior','owners':['C2','C5','B5','E1']},
        {'id':'R02','scope':'Final interaction/DPR/viewport matrix and raster visual acceptance','owners':['B2','B3','B5','C5','E1']},
        {'id':'R03','scope':'Updated end-to-end multi-tab edit/write-retry/undo workflow; hook and HTTP evidence is not all browser races','owners':['C4','C5','E1']},
        {'id':'R04','scope':'Render failure in full App/independent indicator effects; A1 covers shared writer in native harness','owners':['E1']},
        {'id':'R05','scope':'Extended upstream outage and client clock skew; local Date.now comparison remains a known design limit','owners':['D4','E1','E3']},
        {'id':'R06','scope':'Heap/listener/socket retention across long sessions; pane counts alone are not leak acceptance','owners':['D3','D4','D5']},
        {'id':'R07','scope':'G06/G07 full performance, keyboard/mobile/native touch and release acceptance','owners':['B5','D1','D2','D3','D4','D5','E1']},
    ]
    sources = [*list((ROOT/'frontend/src').rglob('*.ts')), *list((ROOT/'frontend/src').rglob('*.tsx')), ROOT/'frontend/package-lock.json', ROOT/'agentrader/chart_market.py', ROOT/'agentrader/market_feed.py', ROOT/'agentrader/market_data.py']
    source_hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)}
    passed = all(checks.values())
    report = {
        'date':'2026-11-09', 'task':'A5' if next_task=='B1' else 'A5_REVALIDATION', 'passed':passed,
        'decision':f'PROCEED_TO_{next_task}_WITH_DECLARED_REMAINING_ACCEPTANCE' if passed else 'KEEP_CORRECTNESS_REVIEW_OPEN',
        'scope':'Desktop Chromium controlled chart correctness baseline; not full G01-G07/release/bot acceptance',
        'full_chart_acceptance':False, 'bot_integration_authorized':False,
        'known_reproduced_unresolved_blockers':[], 'checks':checks, 'groups':groups, 'remaining_acceptance':remaining,
        'evidence':{k:{'path':'reports/'+v, 'sha256':hashlib.sha256((ROOT/'reports'/v).read_bytes()).hexdigest()} for k,v in names.items()},
        'browser_scenarios':sum(len(evidence[k]['cases']) for k in ['A1','A2','A3','A4']),
        'frontend_tests':116, 'backend_tests':675, 'backend_suite_reused_from_A4':True,
        'source_hashes_at_review':source_hashes,
        'source_fingerprint':hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest(),
        'note':'Evidence schema audit plus explicit coverage review. Not a substitute for producers or proof that all bugs are absent. Any later source change requires affected checks to be rerun.'}
    path = ROOT/'reports'/report_name
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':passed,'decision':report['decision'],'checks':checks,'browser_scenarios':report['browser_scenarios']}))
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
