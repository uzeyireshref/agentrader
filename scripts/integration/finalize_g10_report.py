"""Fail-closed assembly of current-build G10 evidence, with separate per-tool dimensions."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.integration.chart_tool_matrix_cases import drawing_cases
OUT=ROOT/'reports/chart-interface-g10-20261115'

def main():
    def read(p):return json.loads((OUT/p).read_text(encoding='utf-8-sig'))
    def write(p,v):(OUT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    assert read('g9-preflight.json')['state']=='PASS'
    api=read('shared-api/p1-api.json');adapter=read('adapter/adapter-matrix.json');manual=read('manual-matrix.json')
    for group in (api,adapter,manual):assert group['passed'] and len(group['cases'])==26
    assert len(adapter['checks'])==20 and all(c['passed'] for c in adapter['checks'])
    renders={}
    for folder,fractional in [('render-baseline',False),('render-fractional-dpr1',True),('render-baseline-dpr2',False),('render-fractional-dpr2',True),('render-fractional-dpr125',True)]:
        result=read(folder+('/p2-browser-fractional.json' if fractional else '/p2-browser.json'))
        assert result['passed'] and len(result['cases'])==52 and not result['page_errors'] and not result['unexpected_requests']
        assert result['account_requests']==result['order_requests']==0
        for row in result['cases']:
            assert row['state']=='PASS' and row['ui_context_read']=='PASS_CLIENT_REPORTED' and not row['ui_order_authority']
            assert row.get('max_anchor_error_css_px',0)<=1 and row['reload']=='PASS' and row['candle_count_not_synthesized']
        assert next(r for r in result['cases'] if r['case_id'].endswith('future-family-regression_channel'))['before_source_bars']=='WAITING_FOR_DATA_NO_FABRICATED_FIT'
        renders[folder]=result
    ui=read('common-ui/g10_ui-browser-suite.json');indicator_browser=read('indicator-browser/p3-browser-suite.json')
    assert ui['passed'] and len(ui['checks'])==25 and all(c['state']=='PASS' for c in ui['checks'])
    assert indicator_browser['passed'] and sum(c['checks'] for c in indicator_browser['checks'])==62
    indicators=read('indicators/p3-indicator-api.json');assert indicators['passed'] and len(indicators['indicators'])==9
    checks={}
    for path,count in [('ui-sessions/browser.json',21),('origins-notes/browser.json',19),('projection/browser-dpr1.json',21),('projection/browser-dpr2.json',21),('channel-linear/result.json',10),('channel-log/result.json',10),('channel-dpr2/result.json',10)]:
        body=read(path);assert body['passed'] and len(body['checks'])==count,(path,len(body['checks']))
        assert not body.get('page_errors',[]) and not body.get('unexpected_requests',[]) and not body.get('errors',[])
        checks[path]=count
    replay=read('replay.log');assert replay['passed'] and replay['count']==replay['total']==36
    python=(OUT/'python-tests.log').read_text(encoding='utf-8-sig');front=(OUT/'frontend-tests.log').read_text(encoding='utf-8-sig');build=(OUT/'build.log').read_text(encoding='utf-8-sig')
    assert '1252 passed' in python and '# pass 360' in front and '# fail 0' in front and 'built in' in build
    runtime=json.loads((ROOT/'agentrader/binding_evidence.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in runtime['runtime_sources'])
    prior=json.loads((ROOT/'reports/chart-interface-g9-20261115/validation.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/p)==h for p,h in prior['frontend_build_sha256'].items()),'Browser evidence must use unchanged production build'
    matrix=[]
    for case in drawing_cases(include_projection=True):
        cid=case['case_id'];a=next(c for c in adapter['cases'] if c['case_id']==cid);m=next(c for c in manual['cases'] if c['case_id']==cid)
        expected='UNSUPPORTED_OPERATION' if case['geometry']['kind'] in ('text','note','price_label') else 'READY'
        assert a['numeric_state']==expected and m['adapter_protection_checks']==m['server_http_403_checks']==5 and m['manual_unchanged']=='PASS'
        rows={}
        # Exact suffix matching must not accidentally include legacy/new sibling variants.
        for folder,result in renders.items():
            prefix='fractional-' if 'fractional' in folder else ''
            rows[folder]=[next(r for r in result['cases'] if r['case_id']==prefix+mode+'-'+cid) for mode in ('loaded','future')]
        matrix.append(dict(case_id=cid,kind=case['geometry']['kind'],record_schema=a['record_schema'],raw_read='PASS_REAL_HTTP',text_note_read=m['text_note_read'],http_math=expected,
            data_readiness=dict(scope=a['query'].get('scope','DISPLAY_ONLY_MATH_UNSUPPORTED'),data_consumed=a['query'].get('data_consumed'),future_regression='WAITING_THEN_READY' if case['geometry']['kind']=='regression_channel' else 'GEOMETRY_OR_DISPLAY_NO_FUTURE_BARS_FABRICATED'),
            render=dict(state='PASS',cases=10,loaded_log=rows['render-baseline'][0].get('log'),evidence=rows),ui_context='PASS_CLIENT_REPORTED_NOT_MARKET_EVIDENCE',
            production_bot_adapter='PASS_CREATE_NOTE_READ_MATH_EDIT_PACKAGE_CLEANUP',manual_protection=dict(adapter_rejections=5,server_http_403=5,unchanged=True),order_authority=False))
    write('acceptance-matrix.json',dict(schema='chart-common-acceptance/1',passed=True,variants=26,rows=matrix))
    source_paths=set()
    for folder in ('agentrader','frontend/src','frontend/tests','tests'):
        source_paths.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.ts','.tsx','.css','.json'))
    source_paths.update((ROOT/'scripts').glob('*.py'));source_paths.update((ROOT/'scripts').glob('*.mts'))
    source_paths.update([ROOT/'scripts/integration/finalize_g10_report.py',ROOT/'docs/chart/COMMON-ACCEPTANCE-G10.md',ROOT/'docs/integration/history/46-BOT-GRAFIK-ORTAK-ARAYUZ-VE-CIZIM-ADAPTORU-GELISTIRME-PLANI.md'])
    report=dict(schema='chart-interface-g10-validation/1',date='2026-11-15',state='PASS',scope='CURRENT_PRODUCTION_BUILD_ISOLATED_HTTP_AND_BROWSER_SYNTHETIC_NOT_LIVE_DEMO',
        python=dict(passed=1252,log='python-tests.log'),frontend=dict(passed=360,log='frontend-tests.log'),replay=dict(passed=36,log='replay.log'),build=dict(passed=True,existing_warning='main bundle >500 kB'),
        drawings=dict(variants=26,math_ready=23,annotation_math_rejected=3,render_cases=260,css_pixel_tolerance=1,dpr=[1,1.25,2],matrix='acceptance-matrix.json'),
        protection=dict(variants=26,adapter_rejections=130,server_http_403=130),common_ui=dict(groups=25,passed=True),indicators=dict(configurations=9,browser_checks=62),additional_browser_checks=checks,
        migration=dict(current=13,new_migration=False,backup_and_legacy_origin_tests='tests/test_drawing_origins_notes.py'),
        runtime_manifest_verified=True,production_build_matches_g9=True,
        limitations=['G11 real Demo feed and autonomous strategy runtime acceptance remains pending.','Client-reported UI snapshots do not confer market or order authority.','Legacy straight slope tools remain explicitly blocked in LOG; supported family tools use their declared scale policy.','Approval UI uses an explicitly injected synthetic acceptance dependency; production missing-evidence gate remains tested closed.','No physical touch/trackpad or real exchange outage observation claimed.'],
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(source_paths)},frontend_build_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()},
        evidence_sha256={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='validation.json'})
    write('validation.json',report)
    print(json.dumps(dict(state='PASS',variants=26,render_cases=260,python=1252,frontend=360,source_files=len(source_paths),evidence_files=len(report['evidence_sha256']))))

if __name__=='__main__':main()
