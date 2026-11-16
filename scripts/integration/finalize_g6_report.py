"""Assemble G6 evidence only after recorded current checks have passed."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.chart.drawings.contracts import registry


def main():
    out=ROOT/'reports/chart-interface-g6-20261115'
    read=lambda name:json.loads((out/name).read_text(encoding='utf-8'))
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    browser=read('browser.json')
    assert browser['passed'] and len(browser['checks'])==21 and all(c['passed'] for c in browser['checks'])
    assert not browser['page_errors'] and not browser['unexpected_requests']
    python=(out/'python-tests.log').read_text(encoding='utf-8-sig')
    frontend=(out/'frontend-tests.log').read_text(encoding='utf-8-sig')
    build=(out/'build.log').read_text(encoding='utf-8-sig')
    assert '1216 passed' in python and '# pass 352' in frontend and '# fail 0' in frontend and 'built in' in build
    replay=read('replay.log');assert replay['passed'] and replay['count']==replay['total']==36
    sources=['agentrader/chart/ui_sessions.py','agentrader/api/ui_sessions.py','agentrader/api/app.py','agentrader/api/market.py',
             'agentrader/chart/chart_context.py','agentrader/api/chart_context.py','agentrader/chart/drawings/tool_access.py',
             'agentrader/chart/drawings/contracts.py','frontend/src/uiSession.ts','frontend/src/useUiSession.ts','frontend/src/uiCrosshair.ts',
             'frontend/src/App.tsx','frontend/src/useDrawings.ts','tests/test_ui_sessions.py','tests/test_chart_tool_access.py',
             'frontend/tests/uiSession.test.ts','frontend/tests/fixtures/ui-session-g6.json','scripts/integration/check_g6_ui_sessions.py',
             'scripts/chart/build_binding_evidence.py','agentrader/binding_evidence.json','agentrader/replay_validation.json',
             'docs/chart/UI-SESSIONS-G6.md','scripts/integration/finalize_g6_report.py']
    hashed=lambda path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    validation=dict(schema='chart-interface-g6-validation/1',date='2026-11-15',state='PASS',
                    scope='EXPLICIT_SYNTHETIC_UI_HTTP_AND_PRODUCTION_BROWSER_NOT_AUTONOMOUS_BOT_OR_DEMO_EXECUTION',
                    new_backend_tests=9,new_frontend_tests=6,
                    python=dict(passed=1216,warnings=1,duration_seconds=float(re.search(r'in ([0-9.]+)s',python).group(1)),log='python-tests.log'),
                    frontend=dict(passed=352,log='frontend-tests.log'),
                    replay=dict(passed=36,total=36,log='replay.log'),
                    browser=dict(passed=True,checks=21,evidence='browser.json',pointer_burst=browser['pointer_burst']),
                    build=dict(passed=True,log='build.log',warning='Existing main bundle >500 kB'),
                    lifetime=dict(ttl_seconds=30,heartbeat_seconds=5,min_normal_publish_interval_ms=500,
                                  max_sessions=128,retired_identity_filter_bytes=8192,storage='PROCESS_LOCAL_RAM'),
                    limitations=['Client reported UI is not market evidence or order authority',
                                 'Undelivered close/offline report becomes unavailable at server TTL',
                                 'Process-local store; distributed multi-worker leases not implemented',
                                 'G7 origin/manual protection and G8 autonomous bot adapter remain pending'],
                    source_sha256={p:hashed(p) for p in sources},
                    frontend_build_sha256={p.relative_to(ROOT).as_posix():hashed(p.relative_to(ROOT)) for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()})
    write('validation.json',validation)
    catalog=registry();write('registry.json',catalog)
    variants=[dict(category=t['category'],kind=t['kind'],record_schema=v['record_schema'],features=v['features']) for t in catalog['tools'] for v in t['record_variants']]
    write('capability-matrix.json',dict(schema='chart-bot-capability-matrix/4',date='2026-11-15',state='G6_UI_BRIDGE_ACCEPTED_NOT_BOT_RUNTIME',
         scope=validation['scope'],record_variants=variants,
         inherited_evidence=dict(drawings_and_indicator_numeric='../chart-interface-g5-20261115/README.md',current_full_regression='validation.json',
                                 statement='G5 numeric/projection evidence is inherited, not reported as rerun G6 browser numeric acceptance'),
         volatile_ui_state_http=dict(state='PASS_ISOLATED_HTTP_AND_PRODUCTION_APP',evidence='browser.json',explicit_session_required=True,ttl_seconds=30,client_reported=True,order_authority=False),
         manual_origin_enforcement='G7_PENDING',linked_long_notes='G7_PENDING',autonomous_bot_adapter='G8_PENDING',demo_runtime='G11_PENDING'))
    write('synthetic-http-example.json',dict(scope='SYNTHETIC_FIXTURE_NOT_LIVE_MARKET_EVIDENCE',
          request='GET /api/workspaces/main/chart-context?symbol=BTCUSDT&interval=15m&ui_session_id=<explicit-tab-id>',
          response=browser['sample_context']))
    print(json.dumps(dict(passed=True,python=1216,frontend=352,browser=21,replay=36,build_files=len(validation['frontend_build_sha256']))))


if __name__=='__main__':main()
