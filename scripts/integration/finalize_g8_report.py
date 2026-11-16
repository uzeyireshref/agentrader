"""Assemble G8 evidence from the production adapter's recorded acceptance."""

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
    out=ROOT/'reports/chart-interface-g8-20261115'
    def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    def hashed(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    acceptance=read('adapter-acceptance.json');replay=read('replay.log');preflight=read('g7-preflight.json')
    assert acceptance['passed'] and len(acceptance['cases'])==25 and len(acceptance['checks'])==19
    assert all(c['passed'] for c in acceptance['checks']) and not acceptance['page_errors'] and not acceptance['unexpected_requests']
    assert sum(c['numeric_state']=='READY' for c in acceptance['cases'])==22
    assert sum(c['numeric_state']=='UNSUPPORTED_OPERATION' for c in acceptance['cases'])==3
    assert replay['passed'] and replay['count']==replay['total']==36 and preflight['state']=='PASS' and not preflight['hash_mismatch']
    python=(out/'python-tests.log').read_text(encoding='utf-8-sig')
    frontend=(out/'frontend-tests.log').read_text(encoding='utf-8-sig')
    assert '1244 passed' in python and '# pass 356' in frontend and '# fail 0' in frontend
    assert '13 passed' in (out/'g7-preflight-python.log').read_text(encoding='utf-8-sig')
    assert '# pass 4' in (out/'g7-preflight-frontend.log').read_text(encoding='utf-8-sig')
    g7=json.loads((ROOT/'reports/chart-interface-g7-20261115/validation.json').read_text(encoding='utf-8'))
    frontend_sources={p:h for p,h in g7['source_sha256'].items() if p.startswith('frontend/')}
    assert all(hashed(p)==h for p,h in frontend_sources.items())
    assert all(hashed(p)==h for p,h in g7['frontend_build_sha256'].items())
    evidence=json.loads((ROOT/'agentrader/binding_evidence.json').read_text(encoding='utf-8'))
    assert all(hashed(row['path'])==row['sha256'] for row in evidence['runtime_sources'])
    sources=['agentrader/integration/chart_bot.py','agentrader/cli/chart_bot_cli.py','agentrader/__main__.py',
             'agentrader/chart/drawings/actors.py','agentrader/api/app.py','scripts/chart/build_binding_evidence.py',
             'scripts/integration/chart_bot_fixture.py','scripts/integration/g8_fixture_server.py','scripts/integration/check_g8_chart_bot.py',
             'tests/test_chart_bot.py','agentrader/binding_evidence.json','agentrader/replay_validation.json',
             'docs/chart/BOT-ADAPTER-G8.md','scripts/integration/finalize_g8_report.py']
    scope='PRODUCTION_BOT_ADAPTER_AND_CLI_REAL_HTTP_SYNTHETIC_MARKET_NOT_AUTONOMOUS_STRATEGY_OR_LIVE_DEMO_EXECUTION'
    validation=dict(schema='chart-interface-g8-validation/1',date='2026-11-15',state='PASS',scope=scope,
         g7_preflight=dict(passed=True,source_files=26,build_files=8,backend_tests=13,frontend_tests=4,evidence='g7-preflight.json'),
         new_backend_tests=15,targeted_tests=28,
         python=dict(passed=1244,warnings=1,duration_seconds=float(re.search(r'in ([0-9.]+)s',python).group(1)),log='python-tests.log'),
         frontend=dict(passed=356,log='frontend-tests.log'),replay=dict(passed=36,total=36,log='replay.log'),
         adapter_acceptance=dict(passed=True,variants=25,math_ready=22,expected_display_only_blocks=3,checks=19,evidence='adapter-acceptance.json',
                                 real_loopback_http=True,production_cli_separate_process=True,server_restart_tested=True,
                                 committed_response_loss_injected_at_transport=True,manual_sentinels_preserved=True,user_undo_available=True),
         indicator_adapter=dict(real_http_slots_tested=9,evidence='tests/test_chart_bot.py'),
         frontend_build=dict(reused_from_G7=True,sources_unchanged=True,build_files_unchanged=True,used_by_current_G8_browser=True,build_log='../chart-interface-g7-20261115/build.log'),
         journal=dict(storage='SEPARATE_SQLITE_FULL_SYNC',namespace_and_workspace_bound=True,pending_restart_recovery=True,credentials_not_automatically_stored=True),
         limitations=['Synthetic frozen-clock source; no live Demo account/strategy execution',
                      'Earlier numeric formula/projection and UI TTL evidence is inherited, not claimed as rerun G8 browser numeric acceptance',
                      'Completed journal results are historical ACKs; fresh HTTP read is required for current object state',
                      'Logical object cleanup preserves archived revisions/notes; it is not physical deletion',
                      'G9 missing tool/interactions, G10 lifecycle integration and G11 Demo runtime acceptance remain pending'],
         runtime_manifest_verified=True,source_sha256={p:hashed(p) for p in sources},
         unchanged_frontend_source_sha256=frontend_sources,frontend_build_sha256=g7['frontend_build_sha256'])
    write('validation.json',validation);write('registry.json',registry())
    rows=[{k:v for k,v in row.items() if k!='query'} for row in acceptance['cases']]
    write('capability-matrix.json',dict(schema='chart-bot-capability-matrix/6',date='2026-11-15',state='G8_PRODUCTION_ADAPTER_ACCEPTED_SYNTHETIC_HTTP',scope=scope,
         drawing_variants=rows,production_adapter='agentrader.integration.chart_bot.ChartBot',production_cli='python -m agentrader chart-bot',
         manual_origin_enforcement='PASS_G7_PREFLIGHT_AND_CURRENT_G8_SERVER_AND_ADAPTER',linked_long_notes='PASS_ALL_25_VARIANTS_VIA_ADAPTER',
         own_discovery_restart='PASS_REAL_SERVER_AND_SEPARATE_CLI_PROCESS',pending_recovery='PASS_COMMITTED_RESPONSE_LOSS_AND_RESTART',
         inherited_evidence=dict(mathematics='../chart-interface-g5-20261115/README.md',ui_leases='../chart-interface-g6-20261115/README.md',origin_migration='../chart-interface-g7-20261115/README.md'),
         missing_tools='G9_PENDING',lifecycle_integration='G10_PENDING',demo_runtime='G11_PENDING',order_authority=False))
    write('synthetic-adapter-example.json',dict(scope=scope,identity=acceptance['adapter_identity'],
          case=acceptance['cases'][0],manual_sentinels_sha256=acceptance['manual_sentinels_sha256'],
          note='All IDs and prices are from an isolated temporary fixture; these are not live market signals'))
    print(json.dumps(dict(passed=True,python=1244,frontend=356,variants=25,checks=19,replay=36,build_files=8)))


if __name__=='__main__':main()
