"""D5 evidence audit; does not rerun browser sessions or test suites."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/chart-performance-gate-20261110.json'

def main():
    result={'date':'2026-11-10','task':'D5','passed':False,'scope':'CONTROLLED_HEADLESS_PERFORMANCE_GATE_NOT_FULL_CHART_RELEASE','checks':[],'full_chart_acceptance':False,'b5_completed':False,'next_task':'E1'}
    def load(name):return json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
    def require(name,condition):
        result['checks'].append({'name':name,'passed':bool(condition)})
        if not condition:raise AssertionError(name)
    try:
        fixture=load('chart-performance-10s-20261110.json');interaction=load('chart-performance-60s-20261110.json');resource=load('chart-resource-lifecycle-browser-20261110.json');soak=load('chart-soak-browser-20261110.json')
        assets=ROOT/'agentrader/web_assets';current={str(p.relative_to(assets)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(assets.rglob('*')) if p.is_file()}
        require('current_production_assets_match_all_four_evidence_runs',all(v['assets']==current for v in [fixture,interaction,resource,soak]))
        require('same_chromium_version',len({v['browser'] for v in [fixture,interaction,resource,soak]})==1)
        require('d1_valid_4000_candle_200_mixed_drawing_fixture',fixture['passed'] and fixture['fixture']['candles']==4000 and fixture['fixture']['drawings']==200 and fixture['fixture']['types']=={k:50 for k in ['horizontal','zone','trend','fibonacci']})
        require('d2_same_fixture_and_three_valid_runs',interaction['passed'] and fixture['fixture']['sha256']==interaction['fixture']['sha256'] and len(interaction['runs'])==3)
        for r in interaction['runs']:
            m=r['measurement'];c=m['cadence']
            require('d2_run_'+str(r['run']),r['valid'] and c['usable'] and c['p95_ms']<=33.34 and m['requested_ms']==60000 and m['duration_ms']>=60000 and len(r['trace'])==30 and not any(m[k] for k in ['errors','viewport_changed','workload_changed','non_live_observed']) and c['interruptions']==0 and c['truncated_samples']==0)
        require('d3_measured_and_diagnostic_cycles',resource['passed'] and resource['fixture']['measured_cycles']==10 and resource['fixture']['diagnostic_extra_cycles']==20)
        initial=resource['samples'][0]
        require('d3_native_resources_return_to_baseline',all(s['dom']==initial['dom'] and s['canvas']==initial['canvas'] and s['series']==[1,1] and s['sockets']['active']==1 and s['server_connections']['active']==1 for s in resource['samples']))
        require('d3_heap_growth_investigated',bool(resource['heap_growth_categories']) and resource['heap_growth_categories']['closure']['count_delta']==0)
        require('d4_actual_30_minutes_and_full_data_checks',soak['passed'] and soak['d4_eligible'] and soak['duration_seconds']>=1800 and len(soak['samples'])>=61 and all(s['canonical_hash_matched'] and s['candles']==4000 and s['drawings']==200 for s in soak['samples']))
        require('d4_two_real_timestamp_rollovers',len(soak['boundaries'])==2 and all(e['new_time']-e['closed_time']==900 for e in soak['boundaries']))
        require('d4_two_reconnections_recovered',len(soak['events'])==2 and all(e['reconnecting_observed'] and e['recovered'] for e in soak['events']))
        gc=[s for s in soak['samples'] if s['forced_gc']];first=gc[0]
        require('d4_post_gc_resource_counts_stable',len(gc)>=7 and all(s['dom']==first['dom'] and s['sockets']['active']==1 and s['server_connections']['active']==1 for s in gc))
        require('d4_no_errors_rejections_or_hidden_page',all(not any(s['monitor'][k] for k in ['errors','rejections','hidden']) for s in soak['samples']) and not soak['page_errors'] and not soak['unexpected_requests'])
        require('d4_heap_within_predeclared_budget',soak['heap_review']['within_budget'] and soak['heap_review']['net_growth_bytes']<=soak['heap_review']['screening_budget_bytes'])
        record=[];maximum=0
        for s in soak['samples']:
            if s['monitor']['max_ms']>maximum:
                record.append({'elapsed_seconds':s['elapsed_seconds'],'max_ms':s['monitor']['max_ms'],'forced_gc_sample':s['forced_gc']});maximum=s['monitor']['max_ms']
        result.update(passed=True,bundle='index-DIUEWtQr.js',assets=current,browser=fixture['browser'],environment=fixture['browser_environment'],hardware=fixture['hardware'],interaction_runs=[{'run':r['run'],'p95_ms':r['measurement']['cadence']['p95_ms'],'max_ms':r['measurement']['cadence']['max_ms'],'long_tasks':r['measurement']['long_tasks'],'long_task_ms':r['measurement']['long_task_ms']} for r in interaction['runs']],heap_review=soak['heap_review'],soak_max_interval_timeline=record,evidence=['reports/chart-performance-10s-20261110.json','reports/chart-performance-60s-20261110.json','reports/chart-resource-lifecycle-browser-20261110.json','reports/chart-soak-browser-20261110.json'],notes=['749.9 ms is first observed in the initial 31-second window containing startup heap snapshot; no precise causal timing trace exists. Do not claim GC is the proven sole cause or that there were no stalls.','D2 interaction p95 threshold applies to separate controlled 60-second runs; D4 observer/GC soak has no maximum-gap acceptance threshold.','Heap net growth 1771904 bytes is below the predeclared 2097152-byte screening budget; last five-minute growth is 14316 bytes. No unlimited-duration plateau or no-leak proof.','D3 uses 200 horizontal drawings; D1/D2/D4 use mixed types. Resource evidence complements workload evidence, not an identical fixture comparison.'],remaining_scope=['Physical trackpad/visible desktop B5 deferred by user','Native touch, screen reader and raster/DPR acceptance remain open','Unlimited-session heap bound and exact 749.9 ms outlier attribution are not established','General G01-G07 release acceptance and bot connection remain open'],suite_execution='This script audits saved measurements and current assets only; frontend tests/build are separately recorded in D5 validation.')
    except Exception as e:result['error']=str(e)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'error':result.get('error'),'report':str(OUT)},ensure_ascii=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
