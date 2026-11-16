"""Historical 2026-11-14 evidence assembler; not a current G4 acceptance command."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/all-chart-tools-20261114'


def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    names = ['p1-api.json', 'p2-browser.json', 'p2-browser-fractional.json',
             'p3-indicator-api.json', 'p3-browser-suite.json', 'p4-browser-suite.json']
    evidence = {n: read(n) for n in names}
    assert all(v['passed'] for v in evidence.values())
    assert 'Ran 1163 tests' in (OUT / 'python-tests.log').read_text()
    assert '\nOK' in (OUT / 'python-tests.log').read_text()
    assert '# pass 343' in (OUT / 'frontend-tests.log').read_text()
    assert '# fail 0' in (OUT / 'frontend-tests.log').read_text()
    assert 'built in' in (OUT / 'frontend-build.log').read_text()
    rows = []
    for case in evidence['p1-api.json']['cases']:
        projections = [c for n in ['p2-browser.json', 'p2-browser-fractional.json']
                       for c in evidence[n]['cases']
                       if c['case_id'].endswith('-' + case['case_id'])]
        assert len(projections) == 4, (case['case_id'], len(projections))
        rows.append({
            'case_id': case['case_id'], 'kind': case['kind'], 'schema': case['schema'],
            'api_create_read_edit_delete': case['state'], 'notes': case['note_access'],
            'python_calculation': case['computation'],
            'computed_http_query': 'NOT_EXPOSED_TO_BOT',
            'autonomous_bot_writer_strategy': 'NOT_IMPLEMENTED',
            'projection_cases': projections,
        })
    counts = Counter(c['state'] for r in rows for c in r['projection_cases'])
    assert len(rows) == 25 and counts == {'PASS': 98, 'EXPECTED_BLOCK': 2}
    assert len(evidence['p4-browser-suite.json']['checks']) == 25
    assert all(c['state'] == 'PASS' for c in evidence['p4-browser-suite.json']['checks'])
    result = {
        'schema': 'chart-bot-capability-matrix/1', 'date': '2026-11-14',
        'state': 'AUDIT_COMPLETE_WITH_ACCESS_GAPS', 'drawing_variants': rows,
        'projection_counts': dict(counts),
        'indicator_configs': evidence['p3-indicator-api.json']['indicators'],
        'indicator_series_http': 'NOT_EXPOSED_TO_BOT',
        'volatile_ui_state_http': 'NOT_EXPOSED_TO_BOT',
        'registry_only_fibonacci_projection': 'NOT_IMPLEMENTED_CREATE_REJECTED_422',
        'scope': 'Isolated synthetic Demo-context data and stores; no account, credential or order access. API clients emulate bot calls; no autonomous strategy acceptance.',
        'regression': {'python': 1163, 'frontend': 343, 'build': 'PASS',
                       'browser_feature_groups': len(evidence['p4-browser-suite.json']['checks'])},
    }
    write('capability-matrix.json', result)
    write('p5-regression.json', {'package': 'P5', 'passed': True, **result['regression'],
                               'logs': ['python-tests.log', 'frontend-tests.log', 'frontend-build.log'],
                               'build_warning': 'Bundle chunk larger than 500 kB; non-failing.'})
    plan = read('plan.json')
    plan['state'] = result['state']
    for package in plan['packages']:
        package['state'] = 'COMPLETE'
    plan['packages'][-2]['evidence'] = ['p4-browser-suite.json']
    plan['packages'][-1]['evidence'] = ['p5-regression.json', 'capability-matrix.json']
    plan['clarification'] = 'Copy acceptance covers Duplicate; generic clipboard paste is not implemented. Package completion does not close bot access gaps.'
    write('plan.json', plan)
    header = '''# Tüm grafik araçları: bot yazma/okuma kabul sonuçları

14 Kasım 2026. Plan 44 önce yazıldı; P0–P5 sırasıyla tamamlandı. Sonuç: **denetim tamamlandı, bot erişim eksikleri açık**. Testler izole depolarda ve sentetik Demo bağlamında çalıştı; hesap/anahtar erişimi ve emir gönderimi yapılmadı. Mevcut kullanıcı çizimleri değiştirilmedi.

## Kanıtlanan davranış

- 22 araç türünün 25 şema varyantında API ile oluşturma, tam UTC/fiyat geri okuma, revizyonlu düzenleme, silme, kalıcılık, sahip/çalışma alanı ayrımı, kilit ve görünürlük geçti.
- 100 tarayıcı koordinat senaryosunun 98'i geçti; 2 regresyon senaryosu beklenen veri gereksinimi nedeniyle engelli. Desteklenen çizimlerde hata en çok 1 CSS piksel; veri sonrası tarih, yeniden yükleme, lineer/log ve sonradan gelen mumlar kontrol edildi.
- 9 gösterge yapılandırması API üzerinden yazılıp okundu. Üç sayısal tarayıcı paketi EMA/RSI/SMA/ATR/MACD/BB/session VWAP/anchored VWAP sonuçlarını bağımsız referanslarla doğruladı.
- 25 güncel etkileşim paketi geçti: düzenleme, kanal ailesi, Fib, magnet, ölçek/görünüm, iki sekme, veri toparlanması, profil/şablon, gölge/önizleme/onay ve alarm ayarları dahil.
- Tam regresyon: **1163 Python + 343 frontend testi geçti**, üretim derlemesi başarılı. Derlemede 500 kB üstü paket uyarısı var.

## Botun gerçekten erişebildiği katmanlar

API test istemcisi botun çağrılarını taklit etti. Bu sonuç, çalışan işlem botunun kendi kendine araç seçip çizim stratejisi yürüttüğünü kanıtlamaz; genel otonom çizim adaptörü/stratejisi henüz yoktur.

Ham koordinatlar, etiketler, desteklenen metinler, seçenekler, stiller ve nesne sözleşmeleri API'den okunabilir. 8 kanal ailesi + 3 açıklama varyantında tam metin alanı vardır; diğer araçlarda kısa etiket kullanılabilir, uzun not için ayrı Note nesnesi gerekir. Desteklenmeyen metin alanı 422 ile reddedildi.

14 varyant için Python kütüphanesinde sayısal çıktı doğrulandı; 11 varyant görsel/metin amaçlıdır ve hesaplama talebi açıkça engellenir. Genel HTTP hesaplama sorgusu yoktur. Ham yatay çizgi fiyatı gibi doğrudan alanlar ayrıca okunabilir. Gösterge ayarları okunur, hesaplanmış gösterge serileri için bot HTTP uç noktası yoktur. Katalogdaki readable bayrağı tek başına bütün bu katmanları anlatmaz.

Regresyon kanalı gerçek mumları kullanır, tıklanan fiyatları fit girdisi saymaz. Mum başlangıcına denk gelmeyen zamanları ham kayıt kabul etse de çizim hesaplanamaz; API hazır olma durumunu henüz bildirmez. Diğer kanallarda türetilen sınır tutamacı ham üçüncü çapa ile aynı uç nokta olmak zorunda değildir. Fibonacci projection yalnız katalog kaydıdır; oluşturma 422 ile reddedilir.

Kaydedilmiş profil/şablon ile anlık ekran aynı şey değildir. İmleç/hover, seçili araç/nesne, zoom/viewport, magnet, undo geçmişi, favoriler, yerel bildirim tercihleri ve anlık tema genel bot API'sinde yayımlanmaz. Tarayıcı testinin bunları görebilmesi sunucu botuna erişim sağlamaz. Duplicate test edildi; genel pano yapıştırma özelliği uygulanmış değildir.

## Sonraki geliştirme sırası

1. Bot için salt okunur ortak grafik bağlamı: nesneler, kaynak/UTC/revizyon, hesaplama hazır olma durumu; kalıcı ve anlık durum açık ayrılmalı.
2. Türetilmiş çizim değerleri ve gösterge serileri için kaynak kanıtı/warmup içeren sorgular. Görsel araçlara yalnız bayrak değiştirerek işlem yetkisi verilmemeli.
3. Genel bot çizim adaptörü: bot kökeni/nesne alanı, idempotency ve manuel çizimleri koruma. Aynı yerel sahip içinde manuel/bot kökeni henüz ayrılmıyor.
4. Katalog/şema keşfini ve regresyon giriş koşullarını tutarlı hale getirme; ardından ayrı otonom strateji kabulü.

## Araç bazında sonuçlar

API sütunu oluşturma/okuma/düzenleme/silmeyi kapsar. Sayısal sütun Python kütüphanesidir; HTTP hesaplama erişimi bütün satırlarda eksiktir.

| Varyant | API | Not erişimi | Python sayısal işlem | Tarayıcı senaryoları |
|---|---|---|---|---|
'''
    for row in rows:
        status = ', '.join(f'{k}: {v}' for k, v in Counter(c['state'] for c in row['projection_cases']).items())
        header += f"| {row['case_id']} | PASS | {row['notes']} | {row['python_calculation']['state']} | {status} |\n"
    header += '''
## Kanıt dosyaları ve kapsam sınırı

[Makine okunur matris](reports/all-chart-tools-20261114/capability-matrix.json), [plan](44-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-PLANI.md), P1/P2/P3/P4/P5 raporları ve ekran görüntüleri `reports/all-chart-tools-20261114/` altındadır. Eski E3 tasarım prototipi ve eski toolbar kanal yolu güncel kabul yerine kullanılmadı; ham sonuçları korundu, yerlerine güncel sözleşme ve eski/yeni şema testleri kondu. Bu, eski prototiplerin geçtiği iddiası değildir. Test fikstürleri güncel Demo veri zarfına uyarlandı; eksik hassasiyet veya açık bozuk kanıt güvenilir seviyeye yükseltilmedi. Bu tur üretim uygulama kodu değiştirilmedi.
'''
    (ROOT / 'docs/integration/history/45-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-SONUCLARI.md').write_text(header, encoding='utf-8')
    notice = '> 14 Kasım 2026 — [Tüm araçların bot yazma/okuma denetimi tamamlandı](45-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-SONUCLARI.md): 25 çizim varyantı, 9 gösterge ayarı, 25 tarayıcı grubu; 1163 Python ve 343 frontend testi geçti. 100 koordinat senaryosunda 98 başarı / 2 beklenen regresyon engeli var. Ham API erişimi doğrulandı; sayısal HTTP sorguları, anlık UI okuması ve otonom çizim adaptörü eksik. Emir gönderilmedi.\n\n'
    for name in ['docs/project/DEVELOPMENT-HISTORY.md', 'docs/project/history/07-GELISTIRME-DURUMU.md', 'docs/integration/history/26-DEMO-VERI-VE-GRAFIK-BOT-ENTEGRASYON-PLANI.md']:
        path = ROOT / name
        old = path.read_text(encoding='utf-8')
        if notice not in old:
            path.write_text(notice + old, encoding='utf-8')
    path = ROOT / 'docs/integration/history/44-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-PLANI.md'
    old = path.read_text(encoding='utf-8')
    closure = '\n\n## Güncel kapanış\n\nP0–P5 tamamlandı. [Araç bazında sonuçlar ve açık erişim eksikleri](45-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-SONUCLARI.md). Tamamlanan denetim, eksik bot arayüzlerinin uygulandığı anlamına gelmez. Kopyalama kapsamı Duplicate işlemidir; genel pano yapıştırma yoktur.\n'
    if '## Güncel kapanış' not in old:
        path.write_text(old + closure, encoding='utf-8')
    paths = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'delivery-hashes.json']
    paths += [script_path(n) for n in ['chart_tool_matrix_cases.py', 'check_all_tool_api_roundtrip.py', 'check_all_tool_browser_projection.py', 'check_all_indicator_bot_readback.py', 'chart_control_cases.py', 'demo_browser_fixture.py', 'demo_browser_fixture.mts', 'run_chart_acceptance_packages.py', 'finalize_chart_tool_acceptance.py']]
    paths += [ROOT / 'tests/test_demo_browser_fixture.py', ROOT / 'docs/integration/history/45-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-SONUCLARI.md']
    paths += [script_path(c['script']) for name in ['p3-browser-suite.json', 'p4-browser-suite.json'] for c in evidence[name]['checks']]
    paths += [p for p in (ROOT / 'agentrader/web_assets').rglob('*') if p.is_file()]
    paths += [ROOT / 'frontend/vite.config.ts']
    write('delivery-hashes.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)})
    print(json.dumps({'state': result['state'], 'variants': len(rows), 'projections': dict(counts), **result['regression']}))


if __name__ == '__main__':
    main()
