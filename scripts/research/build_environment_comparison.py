"""Compare captured public environments and record explicit eligibility boundaries."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/'reports/crypto-bot-research-20261115'
DATA=ROOT/'docs/research/crypto-bot-20261115'


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def canonical(value):
    if isinstance(value,dict):return {k:canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,list):return sorted((canonical(v) for v in value),key=lambda x:json.dumps(x,sort_keys=True))
    if isinstance(value,(str,int,float)) and type(value) is not bool:
        try:
            numeric=Decimal(str(value))
            if numeric.is_finite():return str(numeric.normalize())
        except InvalidOperation:pass
    return value


def compare(name,live,demo):
    a={s['symbol']:s for s in live['symbols']}
    b={s['symbol']:s for s in demo['symbols']}
    common=sorted(a.keys()&b.keys())
    differences=[]
    fields=['filters','orderTypes','timeInForce','status','contractStatus','contractType','quoteAsset','marginAsset','contractSize','permissionSets','allowedSelfTradePreventionModes']
    for symbol in common:
        diff=[f for f in fields if canonical(a[symbol].get(f))!=canonical(b[symbol].get(f))]
        if diff:differences.append(dict(symbol=symbol,different_fields=diff))
    return dict(product=name,live_symbols=len(a),test_symbols=len(b),common_count=len(common),
                live_only=sorted(a.keys()-b.keys()),test_only=sorted(b.keys()-a.keys()),
                symbols_with_metadata_differences=len(differences),field_difference_counts=dict(Counter(f for r in differences for f in r['different_fields'])),differences=differences,
                note='Unordered metadata lists and cosmetic numeric precision normalized. Does not measure liquidity, order acceptance or private-account equivalence.')


def main():
    snap=REPORT/'official-snapshots'
    env=REPORT/'environment-review'
    comparisons=[compare('USD-M',read(env/'USD-M_LIVE.json'),read(env/'USD-M_DEMO.json')),
                 compare('SPOT',read(snap/'spot_info.json'),read(env/'SPOT_TESTNET.json')),
                 compare('COIN-M',read(snap/'coinm_info.json'),read(env/'COIN-M_DEMO.json'))]
    rows=[
        ('USD-M','https://fapi.binance.com','https://demo-fapi.binance.com','DOCUMENTED_AND_PUBLIC_OBSERVED','Private demo execution and every route remain unproven'),
        ('SPOT','https://api.binance.com','https://testnet.binance.vision','DOCUMENTED_AND_PUBLIC_OBSERVED','Only /api on Spot Testnet, periodic resets'),
        ('COIN-M','https://dapi.binance.com','https://demo-dapi.binance.com','DOCUMENTED_AND_PUBLIC_OBSERVED','Algo migration contract gaps remain'),
        ('OPTIONS','https://eapi.binance.com','https://demo-fapi.binance.com','DOCUMENTED_BUT_PUBLIC_PROBE_403','Documented demo host + /eapi/v1/exchangeInfo returned 403. Cause and account suitability unproven'),
        ('MARGIN','https://api.binance.com',None,'NO_VERIFIED_TEST_ENVIRONMENT','Spot Testnet /sapi is unsupported. No alternative test environment verified'),
        ('PORTFOLIO_MARGIN','https://papi.binance.com',None,'PRODUCTION_PUBLIC_PING_ONLY','No test environment verified. Account product eligibility unproven'),
        ('PORTFOLIO_MARGIN_PRO','https://api.binance.com',None,'NO_VERIFIED_TEST_ENVIRONMENT','Pro/SPAN and account access require separate acceptance'),
        ('CONVERT','https://api.binance.com',None,'NO_VERIFIED_TEST_ENVIRONMENT','This is /sapi Convert. USD-M /fapi Convert is a separate catalog family'),
        ('WALLET','https://api.binance.com',None,'NO_VERIFIED_TEST_ENVIRONMENT','/sapi, API permissions, networks and local entity requirements'),
        ('SUB_ACCOUNT','https://api.binance.com',None,'NO_VERIFIED_TEST_ENVIRONMENT','Master/sub/managed/VIP eligibility is operation-specific'),
    ]
    products=[dict(product=p,production_base=live,test_base=test,environment_evidence=state,limitations=note,
                   private_account_acceptance='NOT_RUN',financial_execution_acceptance='NOT_RUN') for p,live,test,state,note in rows]
    output=dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),products=products,comparisons=comparisons,exchange_mutations=0)
    (DATA/'environment-capability-matrix.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(product_count=len(products),comparisons=[{k:v for k,v in x.items() if k not in ('live_only','test_only','differences')} for x in comparisons]),ensure_ascii=False))


if __name__=='__main__':main()
