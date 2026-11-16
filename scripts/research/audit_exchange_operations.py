"""Inspect exchange route evidence and reproduce order-surface limitations offline."""
import ast
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agentrader.shared.exchange import allowed_requests
from agentrader.bot.order_rules import validate_order


def main():
    directory = ROOT / 'docs/research/crypto-bot-20261115'
    catalog = json.loads((ROOT / 'agentrader/data/usdm_capabilities.json').read_text(encoding='utf-8'))
    allowed = allowed_requests()
    references = {}
    for source in sorted((ROOT / 'agentrader').rglob('*.py')):
        if source.name == 'capabilities.py' or source.name == 'exchange.py':
            continue
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith(('/fapi/', '/futures/')):
                references.setdefault(node.value, []).append(dict(file=source.relative_to(ROOT).as_posix(), line=node.lineno))
    operations = []
    for item in catalog['operations']:
        route = item['reference_path']
        if item['id'] == 'UM-103':
            route = '/fapi/v1/stock/contract'
        refs = references.get(route, [])
        enabled = (item['method'], route) in allowed
        state = 'ADAPTER_ROUTE_PRESENT' if enabled else ('OTHER_SOURCE_REFERENCE' if refs else 'ROUTE_IMPLEMENTATION_NOT_FOUND')
        operations.append(dict(id=item['id'], name=item['name_tr'], category=item['category'],
                               method=item['method'], path=route, source_url=item['source_url'],
                               adapter_allowed=enabled, source_references=refs, route_assessment=state,
                               normal_command_acceptance='REQUIRES_WORKFLOW_EVIDENCE',
                               per_symbol_exchange_acceptance='NOT_RUN'))
    symbol = dict(symbol='BTCUSDT', status='TRADING',
                  orderTypes=['LIMIT', 'MARKET', 'STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET', 'TRAILING_STOP_MARKET'],
                  filters=[dict(filterType='PRICE_FILTER', minPrice='0.1', maxPrice='1000000', tickSize='0.1'),
                           dict(filterType='LOT_SIZE', minQty='0.001', maxQty='1000', stepSize='0.001'),
                           dict(filterType='MARKET_LOT_SIZE', minQty='0.001', maxQty='1000', stepSize='0.001'),
                           dict(filterType='MIN_NOTIONAL', notional='5')])
    base = dict(symbol='BTCUSDT', side='BUY', positionSide='BOTH', type='LIMIT',
                quantity='0.001', price='75000', timeInForce='GTC')
    samples = []
    for tif in ('GTC', 'IOC', 'FOK', 'GTX', 'GTD'):
        intent = base | dict(timeInForce=tif)
        if tif == 'GTD':
            intent['goodTillDate'] = 2000000
        samples.append(('time_in_force_' + tif, intent, 'OPEN', 'SUPPORTED_BY_LOCAL_VALIDATOR'))
    samples.append(('response_type_ACK', base | dict(newOrderRespType='ACK'), 'OPEN', 'DOCUMENTED_FIELD'))
    samples.append(('response_type_RESULT', base | dict(newOrderRespType='RESULT'), 'OPEN', 'DOCUMENTED_FIELD'))
    for value in ('0.1', '5', '7.5', '10', '20'):
        intent = dict(symbol='BTCUSDT', side='SELL', positionSide='BOTH', type='TRAILING_STOP_MARKET',
                      quantity='0.001', reduceOnly='true', callbackRate=value)
        samples.append(('callback_rate_' + value, intent, 'REDUCE', 'OFFICIAL_SCHEMA_RANGE_0_1_TO_20'))
    probes = []
    for name, intent, operation, reference in samples:
        row = dict(name=name, intent=intent, reference=reference,
                   exchange_acceptance='NOT_RUN', fixture='SYNTHETIC_BTC_CONTRACT')
        try:
            proposal = validate_order(intent, symbol, 'one-way', operation, '75000', 1000000)
            row.update(local_validator='ACCEPTED', execution_authorized=proposal['execution_authorized'])
        except ValueError as error:
            row.update(local_validator='REJECTED', reason=str(error))
        probes.append(row)
    report = dict(schema_version=1, observed_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope='USD-M REST route inventory and offline order validator evidence',
                  source_catalog_review_date=catalog['review_date'],
                  route_counts=dict(Counter(row['route_assessment'] for row in operations)),
                  operation_count=len(operations), operations=operations, parameter_probes=probes,
                  evidence_sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                   for name in ('agentrader/shared/exchange.py', 'agentrader/bot/order_rules.py',
                                                'agentrader/bot/plan_v2.py', 'agentrader/bot/v2_preflight.py',
                                                'agentrader/cli/order_cli.py')})
    output = ROOT / 'reports/crypto-bot-research-20261115/exchange-operation-audit.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    markdown = '# USD-M REST işlem envanteri\n\n'
    markdown += '95 işlem için güncel adaptör izinleri ve kaynak referansları. Kaynakta adresin bulunması komuttan uçtan uca kabulü kanıtlamaz. Aynı adresin GET ve POST işlemleri ayrı satırlardadır.\n\n'
    markdown += '| Kimlik | İşlem | Yöntem ve yol | Adaptör | Kaynak referansı |\n|---|---|---|---|---|\n'
    for row in operations:
        refs = row['source_references']
        evidence = ', '.join(ref['file'] + '#' + str(ref['line']) for ref in refs[:3]) or 'İşlem referansı bulunamadı'
        markdown += '| ' + row['id'] + ' | ' + row['name'] + ' | ' + row['method'] + ' ' + str(row['path']) + ' | ' + ('İzinli' if row['adapter_allowed'] else 'İzin listesinde yok') + ' | ' + evidence + ' |\n'
    (directory / 'EXCHANGE-OPERATIONS.md').write_text(markdown, encoding='utf-8')
    print(json.dumps(dict(operation_count=len(operations), route_counts=report['route_counts'],
                          probes=[dict(name=row['name'], local_validator=row['local_validator']) for row in probes]),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
