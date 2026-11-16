"""Assemble G9 evidence: distinct projection, 26 real adapter variants, native clipboard."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.chart.drawings.contracts import registry,capability
from scripts.integration.chart_tool_matrix_cases import drawing_cases


def main():
    out=ROOT/'reports/chart-interface-g9-20261115'
    def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    def hashed(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    shared_api=read('shared-api-matrix/p1-api.json');assert shared_api['passed'] and len(shared_api['cases'])==26
    matrix=read('adapter-matrix.json');browsers=[read('browser-dpr1.json'),read('browser-dpr2.json')];replay=read('replay.log')
    assert matrix['passed'] and len(matrix['cases'])==26 and len(matrix['checks'])==20 and all(c['passed'] for c in matrix['checks'])
    assert sum(c['numeric_state']=='READY' for c in matrix['cases'])==23
    assert sum(c['numeric_state']=='UNSUPPORTED_OPERATION' for c in matrix['cases'])==3
    assert 65536<matrix['large_package_utf8_bytes']<=524288
    assert all(b['passed'] and len(b['checks'])==21 and all(c['passed'] for c in b['checks']) and not b['page_errors'] and not b['unexpected_requests'] and b['linear_max_css_px']<=1 and b['log_max_css_px']<=1 for b in browsers)
    assert replay['passed'] and replay['count']==replay['total']==36
    python=(out/'python-tests.log').read_text(encoding='utf-8-sig');frontend=(out/'frontend-tests.log').read_text(encoding='utf-8-sig');build=(out/'build.log').read_text(encoding='utf-8-sig')
    assert '1252 passed' in python and '# pass 360' in frontend and '# fail 0' in frontend and 'built in' in build
    evidence=json.loads((ROOT/'agentrader/binding_evidence.json').read_text(encoding='utf-8'))
    assert all(hashed(row['path'])==row['sha256'] for row in evidence['runtime_sources'])
    sources=['agentrader/chart/drawings/projection.py','agentrader/chart/drawings/packages.py','agentrader/chart/drawings/service.py',
             'agentrader/chart/drawings/notes.py','agentrader/chart/drawings/calculations.py','agentrader/chart/drawings/contracts.py',
             'agentrader/chart/drawings/scale_policy.py','agentrader/chart/drawings/tool_access.py','agentrader/api/drawings.py',
             'agentrader/api/app.py','agentrader/chart/chart_profiles.py','agentrader/integration/chart_bot.py','agentrader/cli/chart_bot_cli.py',
             'frontend/src/fibonacci.ts','frontend/src/drawings.ts','frontend/src/chartCommands.ts',
             'frontend/src/creationPreview.ts','frontend/src/App.tsx','frontend/src/DrawingPanel.tsx',
             'frontend/src/FibonacciReadout.tsx','frontend/src/DrawingLayer.tsx','frontend/src/viewScale.ts',
             'frontend/src/chartProfiles.ts','frontend/src/useDrawings.ts','frontend/src/drawingPackage.ts',
             'frontend/src/DrawingClipboard.tsx','frontend/src/terminal.css','frontend/tests/projectionPackage.test.ts',
             'frontend/tests/fixtures/projection-g9.json','tests/test_projection_packages.py','tests/test_chart_bot.py',
             'tests/test_chart_tool_access.py','tests/test_configurable_fibonacci.py','tests/test_drawing_api.py',
             'tests/test_ruler.py','tests/test_view_scale.py','scripts/integration/chart_tool_matrix_cases.py',
             'scripts/integration/check_all_tool_api_roundtrip.py','scripts/integration/check_all_tool_browser_projection.py','scripts/integration/check_g9_adapter_matrix.py','scripts/integration/check_g9_projection_browser.py','scripts/chart/build_binding_evidence.py',
             'agentrader/binding_evidence.json','agentrader/replay_validation.json','docs/chart/PROJECTION-CLIPBOARD-G9.md','scripts/integration/finalize_g9_report.py']
    scope='DISTINCT_THREE_ANCHOR_PROJECTION_AND_CLIPBOARD_PRODUCTION_ADAPTER_HTTP_UI_SYNTHETIC_NOT_LIVE_DEMO'
    validation=dict(schema='chart-interface-g9-validation/1',date='2026-11-15',state='PASS',scope=scope,
         new_backend_tests=8,new_frontend_tests=4,shared_api_matrix=dict(passed=True,variants=26,evidence='shared-api-matrix/p1-api.json'),shared_browser_matrix=dict(defined_cases=52,full_run='G10_PENDING'),
         python=dict(passed=1252,warnings=1,duration_seconds=float(re.search(r'in ([0-9.]+)s',python).group(1)),log='python-tests.log'),
         frontend=dict(passed=360,log='frontend-tests.log'),replay=dict(passed=36,total=36,log='replay.log'),
         build=dict(passed=True,log='build.log',warning='Existing main bundle >500 kB'),
         projection=dict(schema='chart-fibonacci-projection/1',basis='PRICE_DELTA',anchor_count=3,formula='C + ratio * (B - A)',wire_format=10,
                         alias_of_extension=False,independent_vectors=6,http_scales=['LINEAR','LOG'],binding_activation=False),
         packages=dict(schema='chart-drawing-package/1',variants=26,max_items=20,max_utf8_bytes=524288,
                       large_package_utf8_bytes=matrix['large_package_utf8_bytes'],actor_verified_new_identity=True,linked_notes_preserved=True,atomic_and_idempotent=True),
         adapter_matrix=dict(passed=True,variants=26,math_ready=23,expected_annotation_blocks=3,checks=20,evidence='adapter-matrix.json'),
         browser=dict(passed=True,groups=2,checks=42,groups_evidence=[dict(dpr=b['dpr'],checks=len(b['checks']),linear_max_css_px=b['linear_max_css_px'],log_max_css_px=b['log_max_css_px']) for b in browsers]),
         limitations=['Synthetic public market fixtures; no live Demo account/order/runtime acceptance',
                      'Projection retains arithmetic PRICE_DELTA semantics in LOG view; no logarithmic ratio model or automatic rule activation',
                      'Package market mismatch is rejected; no automatic symbol/interval price conversion',
                      'Pasted locks/visibility are preserved and existing lock/owner enforcement remains in force',
                      'G10 common broad regression and G11 Demo runtime acceptance remain pending'],
         runtime_manifest_verified=True,source_sha256={p:hashed(p) for p in sources},
         frontend_build_sha256={p.relative_to(ROOT).as_posix():hashed(p.relative_to(ROOT)) for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()})
    write('validation.json',validation);write('registry.json',registry())
    rows=[];geometries={case['case_id']:case['geometry'] for case in drawing_cases(include_projection=True)}
    for case in matrix['cases']:
        kind=geometries[case['case_id']]['kind']
        category='annotation' if kind in ('text','note','price_label') else 'plan' if kind in ('long_plan','short_plan') else 'drawing'
        tool=capability(category,kind,record_schema=case['record_schema'])
        rows.append(dict(case_id=case['case_id'],record_schema=case['record_schema'],adapter_roundtrip=case['create_note_fresh_read_edit'],numeric_state=case['numeric_state'],package_roundtrip='PASS_REAL_ADAPTER',features=tool['features'],projection_browser='PASS_DPR1_DPR2' if case['case_id']=='fib-projection' else 'EARLIER_EVIDENCE_INHERITED'))
    write('capability-matrix.json',dict(schema='chart-bot-capability-matrix/7',date='2026-11-15',state='G9_PROJECTION_CLIPBOARD_ACCEPTED',scope=scope,
          drawing_variants=rows,variant_count=26,manual_origin_enforcement='PASS_CURRENT_G7_G8_REGRESSION_AND_G9_PACKAGES',
          general_clipboard='PASS_NATIVE_UI_AND_REAL_ADAPTER',projection='PASS_DISTINCT_THREE_ANCHOR_EXACT_MODEL',
          inherited_evidence=dict(previous_shapes='../chart-interface-g8-20261115/README.md',previous_pixel_matrix='../chart-interface-g5-20261115/README.md'),
          common_regression='G10_PENDING',demo_runtime='G11_PENDING',order_authority=False))
    projection_case=next(c for c in matrix['cases'] if c['case_id']=='fib-projection')
    write('synthetic-projection-example.json',dict(scope=scope,case=projection_case,note='All identities and prices are isolated acceptance fixtures, not live signals'))
    print(json.dumps(dict(passed=True,python=1252,frontend=360,variants=26,browser_checks=42,adapter_checks=20,replay=36,build_files=len(validation['frontend_build_sha256']))))


if __name__=='__main__':main()
