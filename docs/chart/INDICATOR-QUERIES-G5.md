# G5 — Gösterge seri ve son değer HTTP sözleşmesi

15 Kasım 2026. POST /api/workspaces/{workspace_id}/indicator-queries. İstek schema_version=indicator-query-request/1; yanıt schema_version=indicator-query-response/1, calculation_version=chart-indicator-http/1.

## Kapsam ve istek

Dokuz kaydedilmiş yapılandırma: ema-fast, ema-slow, rsi-main, sma-main, atr-main, macd-main, bb-main, session-vwap, anchored-vwap. Aynı owner/workspace ayarları, period/source/params, revision ve calculation_version kullanılır. İstek parametreleri kaydedilmiş göstergeyi değiştirmez; enabled=false olan gösterge açık hesap isteğiyle okunabilir, açılmaz veya grafiğe eklenmez.

~~~json
{
  "schema_version":"indicator-query-request/1",
  "context":{"symbol":"BTCUSDT","interval":"15m"},
  "queries":[{
    "query_id":"ema-last",
    "indicator_id":"ema-fast",
    "expected_revision":0,
    "operation":"latest",
    "inputs":{}
  }]
}
~~~

context, G2/G3 ile aynı kaynak/sembol/interval, include_open, required_closed_bars ve expected_context_id alanlarını kabul eder. symbol/interval zorunlu; mevcut Demo kaynak kimliğiyle uyuşmalıdır. Mumlar ve kanıt istemciden alınmaz. Salt okuma mevcut sunucu aboneliğini kullanır; yeni feed veya geçmiş indirme başlatmaz. Tarayıcı kapalıyken başka mevcut tüketici varsa veri okunabilir; aktif feed yoksa WAITING_FOR_DATA döner.

Her sorguda query_id (benzersiz ASCII 1–64 karakter), indicator_id, expected_revision (0 dahil tam sayı), operation ve inputs zorunlu. İsteğe bağlı outputs, alan adlarından oluşan benzersiz liste; timezone yalnız mevcut ürün davranışı olan UTC olabilir. Parametre override, serbest ayar/seri, tick veya geometri kabul edilmez. Değişiklik gerekiyorsa mevcut revizyonlu gösterge ayar API'si kullanılır.

## İşlemler ve zaman anlamı

- latest: inputs={}. Seçilen açık/kapalı mum politikasının en son kaynak mumundaki alanlar.
- at: inputs={time:<UTC saniye>}. İçinde bulunduğu gerçek mum bulunur; effective_time ayrıca döner. En yakın geçmiş değere sessiz geri dönüş yoktur. Mum yoksa CANDLE_NOT_LOADED; yalnız açık mum dışlandığı için yoksa OPEN_CANDLE_EXCLUDED.
- series: inputs içinde isteğe bağlı start_time/end_time (kaynak mum başlangıçları için dahil sınırlar), limit (varsayılan 100, en çok 200) ve offset (0–499). Aralık ters olamaz. Devam sayfasında context.expected_context_id zorunludur.

UTC saniye tam sayı olmalı; milisaniye, ondalıklı saniye ve geçersiz aralıklar reddedilir. Görünüm log ölçeği gösterge hesabını değiştirmez. BB için time kaynak mum zamanıdır; display_time saklanan offset kadar kaydırılmış çizim zamanıdır. Pozitif ofset geleceğe ait yeni piyasa değeri anlamına gelmez. at/latest de kaynak zamanını esas alır.

Tam yüklü input üzerinde tek hesap yapılır; çıktı filtresi/sayfalama seed'i yeniden başlatmaz. EMA/ATR/RSI/MACD'nin başlangıcı görünür filtreye göre kaydırılmaz. Aynı snapshot/config için series, latest ve at aynı değeri verir. İlk yüklü kayıttan önceki seed geçmişi uydurulmaz.

## Yanıt ve hazırlık

Üst yanıtta context_id, server_utc, market, epoch/generation/sequence/data_revision, gösterge workspace ayar revizyonu ve G2 readiness vardır. Sonuçlarda kullanılan config/revision/calculation_version, source_price_field, timezone, seans/anchor provenance, warmup, open_candle_used, source tüketim aralığı/hash'i, sorgunun nedensel input aralığı/hash'i ve alan bazlı outputs bulunur. order_authority=false.

Tek çıktılı araçlar value; MACD macd/signal/histogram; BB basis/upper/lower alanları verir. Her noktada source time, state ve o zamana kadar yüklü input sayısı vardır. READY noktada value ve display_time bulunur; kullanılamayan noktada value alanı eklenmez, reason döner. Sıfır hacim veya yetersiz geçmiş sıfır değer gibi sunulmaz.

available_input_count, sorgunun son dönen kaynak zamanına kadar olan yüklü prefix sayısıdır. loaded_input_count bütün seçili input sayısıdır; eski tarih sorgusunda sonradan gelen mumlar warmup varmış gibi sayılmaz. calculation_input_range/hash bu prefix'i kapsar. consumed_range/hash G2'nin tüm seçili kaynak snapshot'ını tanımlar. VWAP'ın gerçek accumulator başlangıcı ve aralık kanıtı ayrıca ready_segments içindedir.

Bir series sayfasında baştaki warmup/bekleme noktalarıyla sonraki hazır değerler birlikte olabilir. Alan state'i en az bir hazır nokta varsa READY olur; partial, hazır olmayan noktaları belirtir. MACD'de istenen alanlardan biri henüz ısınmadıysa sorgu WARMUP olur; hazır macd alanı yine görünür. İstenirse outputs=["macd"] ile yalnız bu alan sorgulanabilir. Hiç mum olmayan aralık WAITING_FOR_DATA'dır.

## Warmup ve algoritma

- EMA, SMA ve ATR: period input. EMA SMA seed; ATR ilk yüklü mumun high−low true range'iyle mevcut Wilder seed davranışı.
- RSI: period+1 input; Wilder smoothing. Mevcut calculation_version=1 düz seride 50, version=2 düz seride 100 verir; sürüm saklanır ve yanıtta görünür.
- MACD: macd için slow period; signal/histogram için slow period+signal period−1. Saklanan EMA/SMA oscillator ve signal seçenekleri korunur.
- BB: period input; saklanan SMA/EMA basis, population sapma ve display offset korunur.
- VWAP: en az bir input yanında gerçek seans/anchor başlangıcı ve pozitif kümülatif hacim gerekir; yalnız sayının yeterli olması hazır olma kanıtı değildir.

G2'nin source hazırlık koruması ve required_closed_bars tercihi ayrıca geçerlidir (varsayılan 2). Açık muma izin vermek include_open=true ile açıkça istenir. Source snapshot en çok 499 yüklü mumla sınırlıdır; bundan fazla warmup gerektiren ayar yeterli veri yoksa WARMUP kalır. Bu uç otomatik tüm geçmiş indirmez.

## VWAP, hacim ve aralık kanıtı

Mevcut UTC 00:00 seansı, anchored UTC/symbol, BAR_PRICE_VOLUME ve EXACT_QUOTE_BASE davranışları kullanılır. Aktif ayar şemasında farklı timezone/seans ayarı yoktur: UTC açık yayımlanır; Europe/Istanbul gibi farklı timezone isteği UNSUPPORTED_TIMEZONE ile reddedilir, sessizce UTC gibi hesaplanmaz. UTC dışı saat dilimi dönüşümü bu API'de ilan edilmez.

BEFORE_ANCHOR, ANCHOR_UNSET, ANCHOR_NOT_ON_GRID, ANCHOR_SYMBOL_MISMATCH, ANCHOR_HISTORY_MISSING, SESSION_START_MISSING, GRID_GAP, ZERO_CUMULATIVE_VOLUME ve EXACT_VOLUME_UNPROVEN ayrı nedenlerdir. Seans bir sonraki tam başlangıçta toparlanabilir; anchored hesap gap/kanıt kaybını sessizce atlamaz. Sıfır hacim sonrası pozitif accumulator varsa değer korunabilir; baştan beri toplam hacim sıfırsa değer yoktur.

Bir eski boşluk veya kayıp kesin hacim kanıtı, sonraki eksiksiz seansın hesabını engellemek zorunda değildir. Bu istisna yalnız VWAP içinde uygulanır: identity/hash/grid şekli, taze saat ve transport kontrolünden sonra mevcut VWAP state makinesi çalışır. Başarılı her accumulator aralığı ayrıca gerçek input alt kümesinden DataEvidence ile doğrulanır; yalnız VERIFIED aralıkların değerleri yayımlanır. Her READY nokta segment_id taşır ve ilgili ready_segments kaydı input_first_time/input_count/proof içerir.

Tüm source proof BLOCKED ise aynı şekilde BLOCKED kalır; üst G2 readiness READY'ye çevrilmez. data_proof_scope=VWAP_VALIDATED_SEGMENTS_WHOLE_SOURCE_STILL_BLOCKED ayrımı açıklar. EMA/RSI/SMA/ATR/MACD/BB bu istisnayı kullanmaz; kesintili/unproven inputta yeni sonuç vermez. Genel source mismatch, bozuk snapshot/hash veya stale saat bu yolla aşılamaz.

EXACT_QUOTE_BASE değerleri native decimal hacimlerden tam numerator/denominator ile korunur; sonlu decimal mümkünse ayrıca verilir. Devreden kesirde decimal=null, tam kesir geçerlidir. Diğer hesaplar FLOAT64'ten 17 basamak decimal metne çevrilir; precision_digits=16, mutlak 1e−8 ve göreli 1e−10 tolerans beyan edilir. NaN/Infinity başarılı sonuç değildir. Fiyatı tick'e uyarlama veya gösterim yuvarlaması yapılmaz; trade_vwap_claim ve order_authority mevcut false davranışını korur.

## Tutarlılık, hata ve sınırlar

İstek en çok 65536 byte; 1–9 sorgu, seri sayfası en çok 200 kaynak mumu, yanıt en çok 524288 UTF-8 byte, toplam süre bütçesi 2 saniye. Süre/çıktı/gövde sınırları uygulanır. Ortak hesap HTTP event loop dışında çalışır; request cache/deadline istekler arasında paylaşılmaz.

Toplu HTTP 200 içinde her sonuç state/http_status taşır. Hatalar: INVALID_INPUT/UNSUPPORTED_OPERATION/WAITING_FOR_DATA/WARMUP/STALE/SOURCE_MISMATCH (422); INDICATOR_NOT_FOUND (404); INDICATOR_REVISION_CONFLICT (409). Alan bazlı warmup/volume/boundary nedenleri outputs/points içindedir. Yapısal istek hatası INVALID_INDICATOR_QUERY; çıktı limiti INDICATOR_QUERY_OUTPUT_LIMIT (413), süre CONTEXT_READ_TIME_LIMIT (503).

G2 snapshot/config revizyonları hesap öncesi ve sonrası kontrol edilir. Eski context_id veya hesap sırasında source/settings değişimi bütün yanıtı CONTEXT_CHANGED (409) ile reddeder. Başka owner ayarları okunmaz; mevcut local host/origin sınırı sürer. GET chart-context, seri indirmeden yalnız kullanılabilir uç bilgisini taşır; büyük hesaplar orada otomatik yapılmaz. Gösterge/çizim/emir deposuna yazma, subscription veya borsa isteği yoktur.

## Kabul kanıtı

Mevcut üç sayısal tarayıcı referans grubu HTTP üzerinde de sınandı: 29 temel, 70 MACD/BB, 33 VWAP vektörü. Dokuz slot için bağımsız küçük el hesabı; RSI iki sürüm; eksik geçmiş, kısmi MACD, BB ofseti, sıfır/eksik hacim, anchor öncesi veri, UTC dışı istek reddi, source gap ve aralık kanıtı, reconnect, ayar değişimi, readonly hash, paralel çağrı ve limitler ayrıca sınandı. Üç mevcut gerçek tarayıcı paketi yeniden çalıştırıldı. Bu izole sentetik G5 kabulüdür; gerçek bot adaptörü ve Demo runtime kabulü G8/G11 kapsamındadır.
