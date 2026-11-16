"""Probe observed dynamic-price and immediate-trigger validation boundaries offline."""
from collections import Counter
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).parent))
from audit_market_contracts import fixtures
from agentrader.bot.order_rules import validate_order


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    folder=ROOT/'reports/crypto-bot-research-20261115'
    snap=folder/'official-snapshots'
    info=json.loads((snap/'usdm_demo_info.json').read_text(encoding='utf-8'))
    marks={x['symbol']:Decimal(x['markPrice']) for x in json.loads((snap/'usdm_demo_marks.json').read_text(encoding='utf-8'))}
    rows=[]
    for s in info['symbols']:
        if not(s['status']=='TRADING' and s['contractType']=='PERPETUAL' and s['quoteAsset']=='USDT'):
            continue
        mark=marks[s['symbol']]
        filters={f['filterType']:f for f in s['filters']}
        pf=filters['PRICE_FILTER']
        if not Decimal(pf['minPrice'])<=mark<=Decimal(pf['maxPrice']):
            continue
        tick=Decimal(pf['tickSize'])
        base=fixtures(s,mark)[0][1]
        upper=((mark*(Decimal(filters['PERCENT_PRICE']['multiplierUp'])+Decimal('.01')))/tick).to_integral_value(rounding=ROUND_CEILING)*tick
        low=((mark-tick)/tick).to_integral_value(rounding=ROUND_FLOOR)*tick
        probes=[]
        if Decimal(pf['minPrice'])<=upper<=Decimal(pf['maxPrice']):
            probes.append(('PRICE_ABOVE_CAPTURED_PERCENT_BAND',base|dict(price=str(upper))))
        if Decimal(pf['minPrice'])<=low<=Decimal(pf['maxPrice']):
            probes.append(('BUY_STOP_ALREADY_TRIGGERED',dict(symbol=s['symbol'],side='BUY',positionSide='BOTH',type='STOP_MARKET',quantity=base['quantity'],triggerPrice=str(low),workingType='MARK_PRICE')))
        for name,intent in probes:
            try:
                validate_order(intent,s,'one-way','OPEN',str(mark),1000000)
                state='LOCAL_ACCEPTS_REFERENCE_VIOLATION'
                reason=None
            except ValueError as exc:
                state='LOCAL_REJECTS'
                reason=str(exc)
            rows.append(dict(symbol=s['symbol'],case=name,result=state,reason=reason,mark_price=str(mark),intent=intent,exchange_acceptance='NOT_RUN'))
    report=dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),scope='Captured public filter boundaries and existing validator, no network mutation',
                count=len(rows),counts=dict(Counter(x['result'] for x in rows)),
                by_case={name:dict(Counter(x['result'] for x in rows if x['case']==name)) for name in sorted(set(x['case'] for x in rows))},results=rows)
    output=args.output or folder/'filter-boundary-audit.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'}))


if __name__=='__main__':
    main()
