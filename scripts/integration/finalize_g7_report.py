"""Assemble G7 evidence from successful current isolated checks."""

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
    out=ROOT/'reports/chart-interface-g7-20261115'
    def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    browser=read('browser.json');replay=read('replay.log')
    assert browser['passed'] and len(browser['checks'])==19 and all(c['passed'] for c in browser['checks'])
    assert not browser['page_errors'] and not browser['unexpected_requests']
    assert replay['passed'] and replay['count']==replay['total']==36
    python=(out/'python-tests.log').read_text(encoding='utf-8-sig')
    frontend=(out/'frontend-tests.log').read_text(encoding='utf-8-sig')
    build=(out/'build.log').read_text(encoding='utf-8-sig')
    assert '1229 passed' in python and '# pass 356' in frontend and '# fail 0' in frontend and 'built in' in build
    sources=['agentrader/chart/drawings/actors.py','agentrader/chart/drawings/notes.py','agentrader/chart/drawings/service.py',
             'agentrader/api/drawings.py','agentrader/api/app.py','agentrader/application/settings.py',
             'agentrader/migrations/__init__.py','agentrader/chart/chart_profiles.py','agentrader/chart/chart_context.py',
             'agentrader/chart/chart_queries.py','agentrader/api/ui_sessions.py','agentrader/api/chart_context.py',
             'agentrader/chart/drawings/tool_access.py','frontend/src/DrawingNotes.tsx','frontend/src/DrawingPanel.tsx',
             'frontend/src/drawings.ts','frontend/src/useDrawings.ts','frontend/src/terminal.css',
             'tests/test_drawing_origins_notes.py','frontend/tests/drawingNotes.test.tsx',
             'scripts/integration/check_g7_origins_notes.py','scripts/chart/build_binding_evidence.py',
             'agentrader/binding_evidence.json','agentrader/replay_validation.json',
             'docs/chart/ORIGINS-NOTES-G7.md','scripts/integration/finalize_g7_report.py']
    def hashed(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    validation=dict(schema='chart-interface-g7-validation/1',date='2026-11-15',state='PASS',
         scope='SYNTHETIC_ISOLATED_VERIFIED_ACTOR_HTTP_AND_PRODUCTION_UI_NOT_AUTONOMOUS_BOT_RUNTIME',
         new_backend_tests=13,new_frontend_tests=4,
         python=dict(passed=1229,warnings=1,duration_seconds=float(re.search(r'in ([0-9.]+)s',python).group(1)),log='python-tests.log'),
         frontend=dict(passed=356,log='frontend-tests.log'),replay=dict(passed=36,total=36,log='replay.log'),
         browser=dict(passed=True,checks=19,evidence='browser.json'),
         build=dict(passed=True,log='build.log',warning='Existing main bundle >500 kB'),
         migration=dict(version=13,legacy_origin='manual/legacy',backup_and_v12_restore_tested=True,
                        transactional_failure_rollback_tested=True,user_database_migrated=False),
         manual_protection=dict(server_verified_actor=True,service_transaction_enforced=True,bot_and_strategy_scoped=True,
                                separate_bot_credential_required=True,bot_import_and_private_routes_denied=True),
         linked_notes=dict(all_25_drawing_variants_tested=True,max_code_points=4000,max_utf8_bytes=16000,
                           note_and_target_revision_checked=True,geometry_unchanged=True,archived_target_readonly=True),
         limitations=['Default local mode retains the existing local user trust boundary; separate bot mode requires both credentials',
                      'User credentials and direct database access are outside the restricted bot role',
                      'Notes are versioned and logically archived/deleted; historical content is retained',
                      'G8 real bot adapter and G11 Demo runtime acceptance remain pending'],
         source_sha256={p:hashed(p) for p in sources},
         frontend_build_sha256={p.relative_to(ROOT).as_posix():hashed(p.relative_to(ROOT)) for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()})
    write('validation.json',validation)
    catalog=registry();write('registry.json',catalog)
    variants=[dict(category=t['category'],kind=t['kind'],record_schema=v['record_schema'],features=v['features'],constraints=v['constraints']) for t in catalog['tools'] for v in t['record_variants']]
    write('capability-matrix.json',dict(schema='chart-bot-capability-matrix/5',date='2026-11-15',state='G7_ORIGINS_NOTES_ACCEPTED_NOT_BOT_RUNTIME',scope=validation['scope'],
         record_variants=variants,manual_origin_enforcement='PASS_ISOLATED_VERIFIED_ACTOR_HTTP_AND_SERVICE',
         linked_long_notes='PASS_25_RECORD_VARIANTS_AND_PRODUCTION_UI',
         inherited_evidence=dict(numeric_and_projection='../chart-interface-g5-20261115/README.md',ui_lease='../chart-interface-g6-20261115/README.md',
                                 statement='Earlier numeric/projection and UI TTL browser evidence is inherited, not claimed as rerun G7 browser acceptance'),
         autonomous_bot_adapter='G8_PENDING',demo_runtime='G11_PENDING',order_authority=False))
    write('synthetic-http-example.json',dict(scope='SYNTHETIC_FIXTURE_NOT_LIVE_MARKET_OR_AUTONOMOUS_BOT',
         request='GET /api/workspaces/main/chart-context?symbol=BTCUSDT&interval=15m',response=browser['sample_context'],
         manual_history=browser['manual_history']))
    print(json.dumps(dict(passed=True,python=1229,frontend=356,browser=19,replay=36,build_files=len(validation['frontend_build_sha256']))))


if __name__=='__main__':main()
