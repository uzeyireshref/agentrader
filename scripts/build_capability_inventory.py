"""Build the reviewed Binance USD-M documentation inventory without account/network calls."""
import ast
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/'

# Each row corresponds to an entry in the official USD-M REST navigation reviewed
# 2026-11-06. Paths not separately checked are explicitly marked reference candidates.
GROUPS = {
'account': '''18|Hesap özeti V2|GET|/fapi/v2/account
19|Hesap özeti V3|GET|/fapi/v3/account
20|Bakiye V2|GET|/fapi/v2/balance
21|Bakiye V3|GET|/fapi/v3/balance
22|Hesap yapılandırması|GET|/fapi/v1/accountConfig
23|İşlem kısıtları ve sayısal kurallar|GET|/fapi/v1/apiTradingStatus
24|BNB komisyon indirimi durumunu oku|GET|/fapi/v1/feeBurn
25|BNB komisyon indirimi tercihini değiştir|POST|/fapi/v1/feeBurn
26|Çoklu varlık modunu oku|GET|/fapi/v1/multiAssetsMargin
27|Hedge veya one-way modunu oku|GET|/fapi/v1/positionSide/dual
28|Emir geçmişi indirme işini başlat|GET|/fapi/v1/order/asyn
29|Gerçekleşme geçmişi indirme işini başlat|GET|/fapi/v1/trade/asyn
30|Gelir geçmişi indirme işini başlat|GET|/fapi/v1/income/asyn
31|Emir geçmişi indirme bağlantısını sorgula|GET|/fapi/v1/order/asyn/id
32|Gerçekleşme geçmişi indirme bağlantısını sorgula|GET|/fapi/v1/trade/asyn/id
33|Gelir geçmişi indirme bağlantısını sorgula|GET|/fapi/v1/income/asyn/id
34|Gelir ve komisyon kayıtları|GET|/fapi/v1/income
35|Kaldıraç ve bakım marjı basamakları|GET|/fapi/v1/leverageBracket
36|Kullanıcı istek limitlerini oku|GET|/fapi/v1/rateLimit/order
37|Sembolün kaldıraç ve teminat ayarları|GET|/fapi/v1/symbolConfig
38|Kullanıcı komisyon oranları|GET|/fapi/v1/commissionRate''',
'trade': '''82|Çoklu varlık modunu değiştir|POST|/fapi/v1/multiAssetsMargin
83|Hedge veya one-way modunu değiştir|POST|/fapi/v1/positionSide/dual
84|Hesabın gerçekleşmiş işlemlerini oku|GET|/fapi/v1/userTrades
85|Normal emir geçmişi|GET|/fapi/v1/allOrders
86|Normal emirler için zamanlayıcılı iptal|POST|/fapi/v1/countdownCancelAll
87|Koşullu emir sorgula|GET|/fapi/v1/algoOrder
88|Koşullu emir oluştur|POST|/fapi/v1/algoOrder
89|Tek koşullu emri iptal et|DELETE|/fapi/v1/algoOrder
90|Sembolde tüm koşullu emirleri iptal et|DELETE|/fapi/v1/algoOpenOrders
91|Sembolde tüm normal emirleri iptal et|DELETE|/fapi/v1/allOpenOrders
92|Birden fazla limit emri değiştir|PUT|/fapi/v1/batchOrders
93|Birden fazla emir oluştur|POST|/fapi/v1/batchOrders
94|Birden fazla normal emri iptal et|DELETE|/fapi/v1/batchOrders
95|Normal emir sorgula|GET|/fapi/v1/order
96|Limit emir fiyatı veya miktarı değiştir|PUT|/fapi/v1/order
97|Normal emir oluştur|POST|/fapi/v1/order
98|Tek normal emri iptal et|DELETE|/fapi/v1/order
99|Sembol kaldıraç ayarını değiştir|POST|/fapi/v1/leverage
100|Cross veya isolated teminat modu seç|POST|/fapi/v1/marginType
101|Açık koşullu emirleri oku|GET|/fapi/v1/openAlgoOrders
102|Açık normal emirleri oku|GET|/fapi/v1/openOrders
103|TradFi perpetual sözleşme işlemi|POST|
104|Emir değiştirme geçmişi|GET|/fapi/v1/orderAmendment
105|İzole teminat değişim geçmişi|GET|/fapi/v1/positionMargin/history
106|İzole pozisyon teminatını ekle veya azalt|POST|/fapi/v1/positionMargin
107|Hesaba ait ADL sırası göstergesi|GET|/fapi/v1/adlQuantile
108|Pozisyon bilgisi V2|GET|/fapi/v2/positionRisk
109|Pozisyon bilgisi V3|GET|/fapi/v3/positionRisk
110|Koşullu emir geçmişi|GET|/fapi/v1/allAlgoOrders
111|Tek açık normal emri sorgula|GET|/fapi/v1/openOrder
112|Gerçek emir oluşturmayan emir doğrulama|POST|/fapi/v1/order/test
113|Likidasyon ve zorunlu kapatma kayıtları|GET|/fapi/v1/forceOrders''',
'market-data': '''45|Sembol ADL risk göstergesi|GET|/fapi/v1/symbolAdlRisk
46|Vadeli ve spot fiyat farkı istatistiği|GET|/futures/data/basis
47|Sunucu zamanı|GET|/fapi/v1/time
48|Bileşik endeks bileşenleri|GET|/fapi/v1/indexInfo
49|Birleştirilmiş işlem akışı|GET|/fapi/v1/aggTrades
50|Sürekli vadeli kontrat mumları|GET|/fapi/v1/continuousKlines
51|Sembol ve emir filtreleri|GET|/fapi/v1/exchangeInfo
52|Funding geçmişi|GET|/fapi/v1/fundingRate
53|Funding sözleşme bilgileri|GET|/fapi/v1/fundingInfo
54|Endeks fiyatı mumları|GET|/fapi/v1/indexPriceKlines
55|İşlem fiyatı mumları|GET|/fapi/v1/klines
56|Genel long ve short oranı|GET|/futures/data/globalLongShortAccountRatio
57|Mark fiyatı ve funding görünümü|GET|/fapi/v1/premiumIndex
58|Mark fiyatı mumları|GET|/fapi/v1/markPriceKlines
59|Çoklu varlık değerleme endeksi|GET|/fapi/v1/assetIndex
60|Tarihsel işlem kayıtları|GET|/fapi/v1/historicalTrades
61|Açık pozisyon büyüklüğü|GET|/fapi/v1/openInterest
62|Açık pozisyon istatistik geçmişi|GET|/futures/data/openInterestHist
63|Emir defteri derinliği|GET|/fapi/v1/depth
64|Premium endeks mumları|GET|/fapi/v1/premiumIndexKlines
65|Vadeli kontrat uzlaşma fiyatı|GET|/fapi/v1/deliveryPrice
66|Fiyat endeksinin bileşenlerini sorgula|GET|/fapi/v1/constituents
67|Sigorta fonu bakiye görünümü|GET|/fapi/v1/insuranceBalance
68|Son piyasa işlemleri|GET|/fapi/v1/trades
69|RPI emir defteri|GET|/fapi/v1/rpiDepth
70|En iyi alış ve satış fiyatı|GET|/fapi/v1/ticker/bookTicker
71|Son fiyat V1|GET|/fapi/v1/ticker/price
72|Son fiyat V2|GET|/fapi/v2/ticker/price
73|Taker alış ve satış hacmi|GET|/futures/data/takerlongshortRatio
74|Bağlantı testi|GET|/fapi/v1/ping
75|Son 24 saat fiyat istatistiği|GET|/fapi/v1/ticker/24hr
76|Büyük hesapların long ve short oranı|GET|/futures/data/topLongShortAccountRatio
77|Büyük hesapların pozisyon oranı|GET|/futures/data/topLongShortPositionRatio
78|Sözleşme işlem takvimi|GET|/fapi/v1/tradingSchedule''',
'user-data-streams': '''115|Kullanıcı akışını canlı tut|PUT|/fapi/v1/listenKey
116|Kullanıcı akışı oturumunu başlat|POST|/fapi/v1/listenKey
117|Kullanıcı akışı oturumunu kapat|DELETE|/fapi/v1/listenKey''',
'convert': '''40|Dönüşüm teklifini kabul et|POST|/fapi/v1/convert/acceptQuote
41|Dönüştürülebilir varlık çiftleri|GET|/fapi/v1/convert/exchangeInfo
42|Dönüşüm işlemi durumunu oku|GET|/fapi/v1/convert/orderStatus
43|Dönüşüm fiyat teklifi al|POST|/fapi/v1/convert/getQuote''',
'portfolio-margin-endpoints': '''80|Klasik portföy marjı hesap görünümü|GET|/fapi/v1/pmAccountInfo''',
}


def adapter_allowlist():
    tree = ast.parse((ROOT / 'agentrader/exchange.py').read_text(encoding='utf-8'))
    allowed = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('PUBLIC', 'PRIVATE') for t in node.targets):
            allowed.update(('GET', p) for p in ast.literal_eval(node.value))
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            try: method, path = ast.literal_eval(node)
            except (ValueError, TypeError): continue
            if method in ('GET','POST','PUT','DELETE') and isinstance(path, str) and path.startswith('/'):
                allowed.add((method,path))
    return allowed


def build():
    allowed = adapter_allowlist()
    observed = {('GET', p) for p in ['/fapi/v1/time','/fapi/v1/exchangeInfo','/fapi/v1/premiumIndex',
                '/fapi/v3/account','/fapi/v3/positionRisk','/fapi/v1/order','/fapi/v1/algoOrder',
                '/fapi/v1/openOrders','/fapi/v1/openAlgoOrders','/fapi/v1/positionSide/dual',
                '/fapi/v1/symbolConfig','/fapi/v1/leverageBracket','/fapi/v1/income','/fapi/v1/userTrades']}
    observed |= {('POST','/fapi/v1/order'),('POST','/fapi/v1/algoOrder'),
                 ('DELETE','/fapi/v1/order'),('DELETE','/fapi/v1/algoOrder')}
    rows = []
    for group, lines in GROUPS.items():
        for line in lines.splitlines():
            nav_id, name, method, path = line.split('|')
            if group == 'user-data-streams': security = 'API_KEY_SESSION_RECHECK_REQUIRED'
            elif group == 'market-data': security = 'PUBLIC_OR_MARKET_DATA_KEY_RECHECK_REQUIRED'
            else: security = 'SIGNED_OR_ACCOUNT_PERMISSION_RECHECK_REQUIRED'
            existing = (method,path) in allowed
            rows.append({'id': f'UM-{int(nav_id):03d}', 'name_tr': name, 'category': group,
                'method': method, 'reference_path': path or None,
                'route_status': 'BOT_ALLOWLIST_PRESENT' if existing else 'RECHECK_BEFORE_IMPLEMENTATION',
                'documented_in_official_navigation': True, 'source_navigation_id': int(nav_id),
                'source_url': BASE + group, 'security': security,
                'affects_orders_or_configuration': method != 'GET',
                'adapter_allowed': existing, 'historical_demo_evidence': (method,path) in observed,
                'historical_evidence_note': 'Repository records; not re-probed for this inventory.',
                'demo_availability': 'NEEDS_PER_ENDPOINT_CONFIRMATION',
                'current_account_permission': 'NOT_PROBED_IN_THIS_REVIEW',
                'production_workflow_ready': False,
                'validation_required': ['schema_and_filters','offline_tests','permission_check',
                                        'authorized_demo_scenario','restart_and_reconciliation']})
    assert len(rows) == 95 and len({r['id'] for r in rows}) == 95
    assert all(r['method'] in ('GET','POST','PUT','DELETE') for r in rows)
    return {'schema_version':1,'review_date':'2026-11-06','timezone':'Asia/Baku',
            'scope':'USD-M REST documentation snapshot; not proof that all endpoints work in demo',
            'mutations_performed':0,'account_probes_performed':0,
            'availability_rule':'Official docs say MOST endpoints are available on demo; verify each capability.',
            'counts':dict(Counter(r['category'] for r in rows)),
            'adapter_allowlist_total_method_path_pairs':len(allowed),
            'catalog_adapter_allowed':sum(r['adapter_allowed'] for r in rows),
            'operations':rows}


if __name__ == '__main__':
    report = build()
    target = ROOT / 'reports/binance-demo-capabilities-20261106.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# USD M API işlem envanteri', '', 'İnceleme tarihi: 6 Kasım 2026.', '',
           '95 belgelenmiş REST operasyonu. Liste, hepsinin demo hesabında çalıştığı iddiası değildir.',
           'Adresler uygulama öncesi yeniden kontrol edilir; araştırma sırasında API izinleri genişletilmedi.', '',
           'Adaptör izni kullanıcıya hazır iş akışı demek değildir. Gerçek hesap izni bu incelemede sorgulanmadı.', '']
    for category in GROUPS:
        lines += ['## '+category, '', '| Kimlik | İşlem | Yöntem ve referans adres | Adaptör | Önceki demo kanıtı |',
                  '|---|---|---|---|---|']
        for r in report['operations']:
            lines.append(f"| {r['id']} | {r['name_tr']} | {r['method']} {r['reference_path'] or 'Adres ayrıca doğrulanacak'} | {'İzinli' if r['adapter_allowed'] else 'Eksik'} | {'Var, bu incelemede tekrarlanmadı' if r['historical_demo_evidence'] else 'Doğrulanmadı'} |")
        lines += ['', 'Kaynak: '+BASE+category, '']
    (ROOT/'reports/binance-demo-api-islem-listesi-20261106.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'operations':len(report['operations']),'groups':report['counts'],
                      'adapter_allowed':report['catalog_adapter_allowed'],'output':str(target)},ensure_ascii=True))
