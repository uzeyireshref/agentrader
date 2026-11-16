"""Reproducible source-contract comparison, without importing the external SDK."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/research/crypto-bot-20261115'
REPORT = ROOT / 'reports/crypto-bot-research-20261115'
SNAP = REPORT / 'official-snapshots'
PRODUCTS = {
    'Binance Convert API.json': 'convert',
    'Binance Derivatives Trading COIN Futures API.json': 'derivatives_trading_coin_futures',
    'Binance Derivatives Trading Options API.json': 'derivatives_trading_options',
    'Binance Derivatives Trading Portfolio Margin API.json': 'derivatives_trading_portfolio_margin',
    'Binance Derivatives Trading Portfolio Margin Pro API.json': 'derivatives_trading_portfolio_margin_pro',
    'Binance Derivatives Trading USDS Futures API.json': 'derivatives_trading_usds_futures',
    'Binance Margin Trading API.json': 'margin_trading',
    'Binance Spot API.json': 'spot',
    'Binance Sub Account API.json': 'sub_account',
    'Binance Wallet API.json': 'wallet',
}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalize(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return ast.unparse(node)


def extract_sdk():
    manifest = json.loads((SNAP / 'sdk/manifest.json').read_text(encoding='utf-8'))
    result = []
    for src in manifest['files']:
        if '/websocket_streams/' in src['path']:
            continue
        path = SNAP / 'sdk' / src['file']
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name.startswith('_'):
                    continue
                doc = ast.get_docstring(fn) or ''
                route = re.search(r'\b(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)', doc)
                ws = re.search(r'\b(?:Method|method):?\s*[`\"]?([\w.]+)', doc)
                mode = src['path'].split('/')[4]
                kwargs = {}
                for call in ast.walk(fn):
                    if isinstance(call, ast.Call):
                        for kw in call.keywords:
                            if kw.arg in ('method', 'path', 'response_model', 'is_signed', 'is_api_key_required'):
                                kwargs[kw.arg] = literal(kw.value)
                method = kwargs.get('method', route.group(1) if route else None)
                urlpath = kwargs.get('path', route.group(2) if route else None)
                ws_method = None
                if mode != 'rest_api':
                    segment = ast.get_source_segment(text, fn) or ''
                    match = re.search(r'[\"\']method[\"\']:\s*[\"\']/?([^\"\']+)', segment)
                    ws_method = match.group(1) if match else None
                    method, urlpath = None, None
                if mode == 'rest_api' and not urlpath:
                    continue
                args = fn.args.args
                defaults = [None] * (len(args) - len(fn.args.defaults)) + fn.args.defaults
                params = []
                for arg, default in zip(args, defaults):
                    if arg.arg == 'self':
                        continue
                    desc = re.search(r'^[ \t]*' + re.escape(arg.arg) + r'[ \t]*\([^\n]*?\):[ \t]*(.*)$', doc, re.M)
                    params.append(dict(name=arg.arg, type=ast.unparse(arg.annotation) if arg.annotation else None,
                                       required_by_signature=default is None,
                                       default=literal(default) if default is not None else None,
                                       description=desc.group(1) if desc else ''))
                required_guards = sorted(set(re.findall(r'field=[\"\']([^\"\']+)', ast.get_source_segment(text, fn) or '')))
                urls = re.findall(r'https://developers\.binance\.com/[^\s]+', doc)
                rules = doc.split('Args:')[0]
                result.append(dict(product=src['path'].split('/')[1], interface=mode,
                                   method=method, path=urlpath, sdk_method=fn.name,
                                   websocket_method=ws_method,
                                   parameters=params, required_guards=required_guards,
                                   source_rules=rules, documentation=urls,
                                   response_type=ast.unparse(fn.returns) if fn.returns else None,
                                   response_model=kwargs.get('response_model'), signed=kwargs.get('is_signed'),
                                   source_url=src['url'], source_line=fn.lineno,
                                   source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return manifest, result


def model_inventory():
    manifest = json.loads((SNAP / 'models/manifest.json').read_text(encoding='utf-8'))
    models = []
    for src in manifest['files']:
        if src['status'] != 200:
            continue
        p = SNAP / 'models' / src['file']
        tree = ast.parse(p.read_text(encoding='utf-8'))
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef):
                continue
            fields = []
            for n in cls.body:
                if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and not n.target.id.startswith('_'):
                    fields.append(dict(name=n.target.id, type=ast.unparse(n.annotation),
                                       definition=ast.unparse(n.value) if n.value else None))
                elif isinstance(n, ast.Assign):
                    for target in n.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            fields.append(dict(enum=target.id, value=literal(n.value)))
            models.append(dict(product=src['path'].split('/')[1], interface=src['path'].split('/')[4],
                               name=cls.name, fields=fields, source_url=src['url'], source_line=cls.lineno,
                               source_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    return models


def main():
    manifest, sdk = extract_sdk()
    catalog = json.loads((DATA / 'cross-product-operation-catalog.json').read_text(encoding='utf-8'))
    contracts = []
    covered = set()
    for old in catalog['operations']:
        product = PRODUCTS.get(old['product'])
        candidates = [s for s in sdk if s['interface'] == 'rest_api' and s['product'] == product
                      and s['method'] == old['method'] and s['path'] == '/' + old['path'].lstrip('/')]
        row = dict(operation_id=old['id'], product=product, method=old['method'], path=old['path'],
                   name=old['name'], postman_parameters=old['parameters'], postman_source=old['source'])
        if candidates:
            contract = candidates[0]
            covered.add((product, contract['method'], contract['path']))
            oldparams = {normalize(p['name']) for p in old['parameters']} - {'timestamp', 'signature'}
            newparams = {normalize(p['name']) for p in contract['parameters']}
            row.update(comparison='MATCHED_SDK_ROUTE', sdk_contract=contract,
                       postman_only_parameters=sorted(oldparams - newparams),
                       sdk_only_parameters=sorted(newparams - oldparams),
                       evidence_limit='SDK source contract. Official live-page overrides and conditional rules require product review.')
        else:
            row.update(comparison='NO_SDK_ROUTE_MATCH', required_action='Resolve product naming, removed route, or SDK lag against official documentation.')
        contracts.append(row)
    extra = [s for s in sdk if s['interface'] == 'rest_api' and (s['product'], s['method'], s['path']) not in covered]
    models = model_inventory()
    payload = dict(observed_at_utc=datetime.now(timezone.utc).isoformat(), sdk_commit=manifest['commit'],
                   postman_commit=catalog['commit'], baseline_count=len(contracts),
                   comparisons=dict(Counter(x['comparison'] for x in contracts)),
                   sdk_method_count=len(sdk), rest_method_count=sum(s['interface'] == 'rest_api' for s in sdk),
                   websocket_method_count=sum(s['interface'] != 'rest_api' for s in sdk),
                   additional_sdk_rest_count=len(extra), contracts=contracts, additional_sdk_rest=extra,
                   websocket_contracts=[s for s in sdk if s['interface'] != 'rest_api'])
    dump(DATA / 'detailed-operation-contracts.json', payload)
    dump(DATA / 'official-response-models.json', dict(sdk_commit=manifest['commit'], count=len(models), models=models))
    counts = Counter(c['product'] for c in contracts)
    text = '# Sürümlü işlem sözleşmesi karşılaştırması\n\n'
    text += 'Otomatik SDK çıkarımı ile alan ve kaynak karşılaştırmasıdır. Borsa kabulü veya tek başına semantik inceleme tamamlanması değildir.\n\n'
    text += f"SDK commit: `{manifest['commit']}`. Başlangıç {len(contracts)} REST kaydı. Ek SDK REST {len(extra)}. WS/akış metodu {payload['websocket_method_count']}. Yanıt/model sınıfı {len(models)}.\n\n"
    text += '| Ürün | Başlangıç | SDK eşleşmesi | Eşleşmeyen |\n|---|---:|---:|---:|\n'
    for product, count in sorted(counts.items()):
        matched = sum(c['product'] == product and c['comparison'] == 'MATCHED_SDK_ROUTE' for c in contracts)
        text += f'| {product} | {count} | {matched} | {count-matched} |\n'
    text += '\n## Alan farkı veya kaynak uyuşmazlığı olan kayıtlar\n\n'
    text += '| Kimlik | İşlem | Sonuç | Postman tarafında | SDK tarafında |\n|---|---|---|---|---|\n'
    for c in contracts:
        if c['comparison'] != 'MATCHED_SDK_ROUTE' or c.get('postman_only_parameters') or c.get('sdk_only_parameters'):
            text += f"| {c['operation_id']} | {c['method']} {c['path']} | {c['comparison']} | {', '.join(c.get('postman_only_parameters', []))} | {', '.join(c.get('sdk_only_parameters', []))} |\n"
    (DATA / 'DETAILED-CONTRACT-COMPARISON.md').write_text(text, encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k not in ('contracts','additional_sdk_rest','websocket_contracts')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
