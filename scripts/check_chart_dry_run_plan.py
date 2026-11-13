"""E4 plan integrity/arithmetic audit, not an executed strategy test suite."""
import ast,hashlib,json,re
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=ROOT/'docs/chart/contracts/chart-dry-run-v1.json';plan=json.loads(p.read_text(encoding='utf-8'));contract_path=ROOT/'docs/chart/contracts/chart-bot-input-v1.json';contract=json.loads(contract_path.read_text(encoding='utf-8'))
    result={'date':'2026-11-10','task':'E4','passed':False,'checks':[],'case_count':len(plan['cases']),'executed_scenario_count':0,'plan':'docs/chart/DRY-RUN-PLAN.md','spec':'docs/chart/contracts/chart-dry-run-v1.json','plan_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'production_changed':False,'runtime_implemented':False,'bot_connected':False,'external_messages_sent':0,'full_chart_acceptance':False,'scope':'Static plan linkage/coverage + exact synthetic arithmetic only; DR cases specified, not executed.'}
    def check(name,value):
        result['checks'].append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    try:
        cases=plan['cases'];coverage={tag for c in cases for tag in c['coverage']}
        check('e3_version_and_hash_match',plan['contract_version']==contract['contract_version'] and plan['contract_sha256']==hashlib.sha256(contract_path.read_bytes()).hexdigest())
        check('36_unique_specified_cases',len(cases)==36 and len({c['id'] for c in cases})==36 and all(c['execution_status']=='SPECIFIED_NOT_EXECUTED' for c in cases))
        check('all_cases_have_given_steps_expected',all(c['given'] and c['steps'] and c['expected'] and c['coverage'] for c in cases))
        check('all_e3_block_reasons_covered',set(contract['blocked_reasons'])<=coverage)
        check('core_workflows_covered',{'approach','touch','close','zone','trend','fibonacci','replay','restart','dedup','atomicity','delivery_unknown','expiry','no_orders','state'}<=coverage)
        check('closed_candle_and_touch_priority',plan['synthetic_profile']['evaluation_mode']=='CLOSED_CANDLE' and plan['synthetic_profile']['priority']==['TOUCH','APPROACH'])
        cfg=plan['synthetic_profile'];g=plan['synthetic_golden_values'];level=Decimal(cfg['level']);tick=Decimal(cfg['tick_size'])
        check('exact_tolerance_examples',tick*cfg['approach_ticks']==Decimal(g['approach_distance']) and [level-tick*cfg['touch_ticks'],level+tick*cfg['touch_ticks']]==list(map(Decimal,g['touch_band'])) and level-tick*cfg['rearm_ticks']==Decimal(g['from_below_rearm_high_max']))
        check('reverse_fibonacci_example',Decimal('110')+(Decimal('100')-Decimal('110'))*Decimal('0.618')==Decimal(g['reverse_fibonacci_0618']))
        encoded=json.dumps([g['event_components'][k] for k in contract['event_identity_template']],ensure_ascii=False,separators=(',',':'))
        check('semantic_event_golden_hash',encoded==g['event_canonical_json'] and hashlib.sha256(encoded.encode()).hexdigest()==g['event_id'] and len(g['event_id'])==64)
        check('replay_cannot_send_or_write_live_namespace',not plan['replay_policy']['live_namespace_writes'] and not plan['replay_policy']['external_sends'] and plan['replay_policy']['preserve_domain_event_identity'])
        source=(ROOT/'agentrader/notifications.py').read_text(encoding='utf-8');literals={node.value for node in ast.walk(ast.parse(source)) if isinstance(node,ast.Constant) and isinstance(node.value,str)}
        check('existing_delivery_states_not_confused_with_proposed',all(re.search(r'\b'+state+r'\b',source) for state in plan['existing_notification_states']) and not set(plan['proposed_additional_delivery_states'])&literals)
        check('unknown_delivery_not_exactly_once',next(c['expected'] for c in cases if c['id']=='DR32')['exactly_once_delivery_claim'] is False)
        check('no_runtime_or_delivery_authorization',plan['status']=='DESIGN_ONLY_NOT_IMPLEMENTED' and not any(plan[k] for k in ['runtime_enabled','integration_authorized','external_delivery_authorized']))
        receipt=json.loads((ROOT/'reports/chart-candidate-manifest-20261110.json').read_text(encoding='utf-8'));check('pinned_candidate_unchanged',hashlib.sha256((ROOT/receipt['archive']).read_bytes()).hexdigest()==receipt['archive_sha256'])
        result.update(passed=True,next_task='E5',notification_source_sha256=hashlib.sha256((ROOT/'agentrader/notifications.py').read_bytes()).hexdigest())
    except Exception as e:result['error']=str(e)
    (ROOT/'reports/chart-dry-run-plan-validation-20261110.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'plan_checks':len(result['checks']),'specified_cases':len(plan['cases']),'executed_scenarios':0,'error':result.get('error')},ensure_ascii=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
