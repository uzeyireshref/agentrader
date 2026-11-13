"""E1 saved evidence and scope integrity check; no browser retests."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'reports/chart-acceptance-review-20261110.json';d=json.loads(path.read_text(encoding='utf-8'));checks=[]
    def check(name,value):
        checks.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    result={'date':'2026-11-10','task':'E1','passed':False,'checks':checks,'review':'reports/chart-acceptance-review-20261110.json','full_chart_acceptance':False}
    try:
        check('seven_distinct_groups',{g['id'] for g in d['groups']}=={'G0'+str(i) for i in range(1,8)} and len(d['groups'])==7)
        issues={i['id'] for i in d['remaining_items']}
        check('all_remaining_items_exist',all(set(g['remaining'])<=issues and g['evidence'] for g in d['groups']))
        check('all_issues_have_concrete_closure',all(i['closure'] and i['next_owner'] for i in d['remaining_items']))
        check('all_evidence_hashes_match',all(hashlib.sha256((ROOT/e['path']).read_bytes()).hexdigest()==e['sha256'] for e in d['evidence'].values()))
        check('all_group_evidence_registered',all(n in d['evidence'] for g in d['groups'] for n in g['evidence']))
        check('eight_core_sources_unchanged',len(d['core_applicability'])==8 and all(c['unchanged_from_A5'] and hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==c['sha256'] for n,c in d['core_applicability'].items()))
        assets=ROOT/'agentrader/web_assets';current={str(p.relative_to(assets)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(assets.rglob('*')) if p.is_file()}
        check('current_assets_match_review',current==d['assets'])
        check('physical_failure_not_closed',next(c['status'] for c in d['b5_cases'] if c['id']=='D07')=='FAIL' and d['b5_current_physical_retest']=='NOT_COMPLETED')
        check('no_release_or_bot_authorization',d['review_completed'] and not d['full_chart_acceptance'] and not d['bot_integration_authorized'] and d['next_task']=='E2')
        check('central_document_exists',(ROOT/d['document']).is_file())
        result['passed']=True
    except Exception as e:result['error']=str(e)
    (ROOT/'reports/chart-acceptance-review-validation-20261110.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'error':result.get('error')},ensure_ascii=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
