"""Attach explicit lifecycle and acceptance requirements to every baseline operation."""
from collections import Counter
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/research/crypto-bot-20261115'

PROFILES={
    'READ': dict(effect='Read-only snapshot/history',confirmation='Validate identity, schema, freshness and complete pagination',uncertain='Bounded retry of read, preserve incomplete-result state',scenarios=['valid_read','wrong_scope','invalid_parameter','window_boundary','partial_or_delayed_response']),
    'ORDER': dict(effect='Normal/conditional/list/batch order',confirmation='Correlate command, parent/list/algo and child identities, fills and account effects',uncertain='Query by original identities, never blind-repost',scenarios=['accepted','definitive_rejection','lost_response','partial_fill','cancel_fill_race','restart','duplicate_command']),
    'CANCEL': dict(effect='Cancel selected order/list/order scope',confirmation='Verify every affected identity and residual fills or positions',uncertain='Read status of original selection before any further mutation',scenarios=['cancel_success','already_filled','partial_fill_during_cancel','lost_response','foreign_identity','restart']),
    'AMEND': dict(effect='Revise order quantity/price or list state',confirmation='Check old revision, execution quantity, new identity/revision and change history',uncertain='Reconcile revision/history without a second unproven change',scenarios=['valid_amend','fill_during_amend','budget_change','lost_response','revision_mismatch','restart']),
    'MOVEMENT': dict(effect='Transfer/deposit/withdraw/dust/conversion or debt movement',confirmation='Correlate transaction history, amount, fee, asset, account and both ledger effects',uncertain='Query movement and balances, do not infer rejection from timeout',scenarios=['accepted_pending','completed','failed','lost_response','fee_difference','one_ledger_leg_delayed','restart','duplicate_command']),
    'STREAM': dict(effect='Stream/token subscription lifetime',confirmation='Validate key/token lifetime, active subscription and recovery barrier',uncertain='Recover stream and reconcile snapshots before resuming',scenarios=['created','renewed','expired','disconnect','duplicate_or_out_of_order_event','restart']),
    'SETTING': dict(effect='Account/product/permission/protection configuration',confirmation='Read current configuration and verify scope, eligibility and requested value',uncertain='Read back configuration, preserve unresolved state',scenarios=['valid_change','precondition_changed','permission_denied','lost_response','already_set','restart']),
    'DRY_RUN': dict(effect='Validate order without creating a live order',confirmation='Validate response and absence of unintended mutation',uncertain='Report validation result unavailable, do not substitute a live order',scenarios=['valid_order_test','invalid_parameter','permission_denied','lost_response']),
}


def classify(c):
    p=c['path'].lower()
    name=c['name'].lower()
    m=c['method']
    if m=='GET': return 'READ'
    if 'listen' in p: return 'STREAM'
    if 'test' in p: return 'DRY_RUN'
    if any(t in p for t in ('borrow','repay','transfer','withdraw','deposit','convert','dust','exchange')) or 'move-position' in p:
        return 'MOVEMENT'
    if 'order' in p or 'block' in p:
        if m=='DELETE' or 'cancel' in name: return 'CANCEL'
        if m=='PUT' or 'modify' in name or 'amend' in name: return 'AMEND'
        return 'ORDER'
    return 'SETTING'


def main():
    source=json.loads((DATA/'detailed-operation-contracts.json').read_text(encoding='utf-8'))
    support=json.loads((DATA/'operation-support-audit.json').read_text(encoding='utf-8'))
    mapping={r['operation_id']:r for r in support['operations']}
    rows=[]
    for c in source['contracts']:
        profile=classify(c)
        s=c['sdk_contract']
        rows.append(dict(id=c['operation_id'],product=c['product'],method=c['method'],path=c['path'],user_intent=c['name'],
                         lifecycle_profile=profile,requirements=PROFILES[profile],
                         product_rules='PRODUCT-CONTRACT-DECISIONS.md',
                         field_contract=c['operation_id']+' in detailed-operation-contracts.json',
                         source_specific_rules=s['source_rules'],response_model=s['response_model'],
                         signed=s['signed'],source_url=s['source_url'],source_line=s['source_line'],
                         bot_support=mapping[c['operation_id']]['support'],
                         source_references=mapping[c['operation_id']]['source_references'],
                         test_status='ACCEPTANCE_DESIGN_ONLY_FOR_THIS_OPERATION',exchange_acceptance='NOT_RUN',
                         classification_method='Heuristic lifecycle grouping. Source-specific rules and product review take precedence.'))
    (DATA/'operation-lifecycle-requirements.json').write_text(json.dumps(dict(count=len(rows),profiles=PROFILES,
        profile_counts=dict(Counter(x['lifecycle_profile'] for x in rows)),operations=rows),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(count=len(rows),profiles=dict(Counter(x['lifecycle_profile'] for x in rows)))))


if __name__=='__main__':main()
