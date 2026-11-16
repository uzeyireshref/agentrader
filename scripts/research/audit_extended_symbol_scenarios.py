"""Offline symbol, mode, order and parameter coverage with explicit reference gaps."""
from collections import Counter, defaultdict
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from audit_market_contracts import fixtures
from agentrader.bot.order_rules import validate_order

DATA = ROOT / 'docs/research/crypto-bot-20261115'
OUT = ROOT / 'reports/crypto-bot-research-20261115'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true')
    parser.add_argument('--current-contracts', action='store_true',help='Use non-triggered stop fixtures for the current validator contract')
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if args.fresh:
        snapshot = OUT / 'official-snapshots'
        raw = json.loads((snapshot/'usdm_demo_info.json').read_text(encoding='utf-8'))
        selected = [s for s in raw['symbols'] if s['status']=='TRADING' and s['contractType']=='PERPETUAL' and s['quoteAsset']=='USDT']
        universe = dict(count=len(selected),symbols=[dict(symbol=s['symbol'],status=s['status'],filters=s['filters'],order_types=s['orderTypes']) for s in selected])
        prices = {x['symbol']:Decimal(x['markPrice']) for x in json.loads((snapshot/'usdm_demo_marks.json').read_text(encoding='utf-8'))}
        evidence_paths = [snapshot/'usdm_demo_info.json',snapshot/'usdm_demo_marks.json']
    else:
        universe = json.loads((DATA / 'market-universe.json').read_text(encoding='utf-8'))
        prices = {x['symbol']: Decimal(x['mark_price']) for x in json.loads((DATA / 'mark-prices.json').read_text(encoding='utf-8'))['prices']}
        evidence_paths = [DATA/'market-universe.json',DATA/'mark-prices.json']
    results, blocked, shapes = [], [], defaultdict(list)
    for item in universe['symbols']:
        symbol = dict(symbol=item['symbol'], status=item['status'], filters=item['filters'], orderTypes=item['order_types'])
        mark = prices.get(item['symbol'])
        pf = next(x for x in item['filters'] if x['filterType'] == 'PRICE_FILTER')
        if mark is None or not mark.is_finite() or not Decimal(pf['minPrice']) <= mark <= Decimal(pf['maxPrice']):
            blocked.append(dict(symbol=item['symbol'], reason='CAPTURED_MARK_FILTER_CONFLICT', mark=str(mark)))
            continue
        basecases = fixtures(symbol, mark)
        base = basecases[0][1]
        cases = [(n, p, m, op, expected, 'BASELINE_VALIDATOR_CONTRACT') for n,p,m,op,expected in basecases]
        if args.current_contracts:
            tick=Decimal(pf['tickSize'])
            stop_price=Decimal(base['price'])-tick
            cases=[(n,p|dict(triggerPrice=str(stop_price)) if n=='stop_market' else p,m,op,expected,reference)
                   for n,p,m,op,expected,reference in cases]
        for side in ('BUY', 'SELL'):
            for tif in ('GTC', 'IOC', 'FOK', 'GTX', 'GTD'):
                p = base | dict(side=side, timeInForce=tif)
                if tif == 'GTD':
                    p['goodTillDate'] = 2000000
                cases.append((f'{side}_TIF_{tif}',p,'one-way','OPEN',True,'USD_M_LIMIT_CONTRACT'))
            for match in ('OPPONENT','OPPONENT_5','OPPONENT_10','OPPONENT_20','QUEUE','QUEUE_5','QUEUE_10','QUEUE_20'):
                p = {k:v for k,v in base.items() if k != 'price'} | dict(side=side,priceMatch=match)
                cases.append((f'{side}_MATCH_{match}',p,'one-way','OPEN',True,'USD_M_PRICE_MATCH'))
        for stp in ('NONE','EXPIRE_TAKER','EXPIRE_MAKER','EXPIRE_BOTH'):
            cases.append((f'STP_{stp}',base | dict(selfTradePreventionMode=stp),'one-way','OPEN',True,'USD_M_STP'))
        for val in ('0.1','5','7.5','10','20','20.1'):
            p = dict(symbol=item['symbol'],side='SELL',positionSide='BOTH',type='TRAILING_STOP_MARKET',quantity=base['quantity'],reduceOnly='true',callbackRate=val)
            cases.append((f'CALLBACK_{val}',p,'one-way','REDUCE',Decimal(val)<=20,'OFFICIAL_ALGO_RANGE_0_1_TO_20'))
        for response in ('ACK','RESULT'):
            cases.append((f'RESPONSE_{response}',base | dict(newOrderRespType=response),'one-way','OPEN',True,'OFFICIAL_NEW_ORDER_FIELD'))
        for mode, side, pos, op in [('hedge','BUY','LONG','OPEN'),('hedge','SELL','SHORT','OPEN'),('hedge','SELL','LONG','REDUCE'),('hedge','BUY','SHORT','REDUCE')]:
            cases.append((f'{mode}_{side}_{pos}_{op}',base | dict(side=side,positionSide=pos),mode,op,True,'HEDGE_POSITION_SIDE'))
        for bad, value in [('quantity','Infinity'),('quantity','NaN'),('price','Infinity'),('quantity','-1')]:
            cases.append((f'INVALID_{bad}_{value}',base | {bad:value},'one-way','OPEN',False,'FINITE_POSITIVE_DECIMAL'))
        lot = next(x for x in item['filters'] if x['filterType']=='LOT_SIZE')
        shape = (pf['tickSize'],lot['stepSize'],tuple(sorted(item['order_types'])))
        shapes[str(shape)].append(item['symbol'])
        for name, intent, mode, op, expected, reference in cases:
            row = dict(symbol=item['symbol'],case=name,position_mode=mode,operation=op,expected_reference_acceptance=expected,reference=reference,exchange_acceptance='NOT_RUN')
            try:
                proposal = validate_order(intent,symbol,mode,op,str(mark),1000000)
                accepted = True
                row['execution_authorized'] = proposal['execution_authorized']
            except ValueError as exc:
                accepted = False
                row['reason'] = str(exc)
            row.update(actual_local_acceptance=accepted,status='ALIGNED' if accepted==expected else 'REFERENCE_GAP')
            results.append(row)
    report = dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),scope='OFFLINE_VALIDATOR_ONLY',
                  source_symbols=universe['count'],executed_symbols=universe['count']-len(blocked),
                  cases_per_executable_symbol=len(cases),executed_cases=len(results),blocked_symbols=blocked,
                  counts=dict(Counter(x['status'] for x in results)),
                  gaps_by_case=dict(Counter(x['case'] for x in results if x['status']=='REFERENCE_GAP')),
                  symbol_filter_class_count=len(shapes),filter_classes=[dict(signature=k,count=len(v),representatives=v[:3]) for k,v in sorted(shapes.items())],
                  exchange_mutations=0,results=results,
                  evidence_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence_paths+[ROOT/'agentrader/bot/order_rules.py']})
    filename = 'fresh-extended-symbol-scenario-audit.json' if args.fresh else 'extended-symbol-scenario-audit.json'
    output=args.output or OUT/filename
    output.parent.mkdir(parents=True,exist_ok=True)
    report['fixture_contract']='CURRENT_NON_TRIGGERED_STOP' if args.current_contracts else 'HISTORICAL_BASELINE'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','filter_classes','evidence_sha256')},ensure_ascii=False))


if __name__ == '__main__':
    main()
