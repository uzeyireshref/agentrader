# T09 — kalıcı ayarlanabilir gösterge modeli

12 Kasım 2026. Tamamlandı; plan 18/27. Sıradaki T10: SMA ve ATR; ayarlı EMA/RSI hesap kabulü.

## Kullanım ve kapsam

Göstergeler → Gösterge ayarları. Hızlı EMA, yavaş EMA ve RSI için bağımsız görünürlük, 1–500 periyot ve OPEN/HIGH/LOW/CLOSE/HL2/HLC3/OHLC4 fiyat kaynağı seçilir. Kaydet başarılı olunca seri ve veri penceresi birlikte güncellenir. Vazgeç/Escape kayıt yapmaz. Menü ve RSI paneli gizleme düğmesi de aynı kalıcı modele yazar. Ayarlar bu çalışma alanında bütün coin ve zaman dilimlerinde kullanılır; sembole göre ayrı config oluşturulmaz. Eski varsayılan 20/50/14, CLOSE ve başlangıçta kapalı durum korunur.

Her nesnenin sabit indicator_id ve bağımsız revision'ı; workspace kaydının ayrıca revision'ı vardır. Smoothing, anchor, pane ve calculation_version açık ve doğrulanmış alanlardır. Bu sürüm EMA için SMA-seed EMA, RSI için SMA-seed Wilder; yüklü geçmiş başlangıcı ve fiyat/ayrı RSI pane yerleşimini destekler. Desteklenmeyen seçenekler sunulmaz, API'de reddedilir. Alternatif smoothing, keyfi panel/anchor ve yeni gösterge türleri bu teslimde yoktur.

## Hesap sözleşmesi

EMA ilk `period` örneğinin aritmetik ortalamasından başlar; ilk çıktı indeksi period−1. RSI ilk `period` değişimin ortalama gain/loss seed'ini kullanır; ilk çıktı indeksi period. Yetersiz geçmiş boş sonuçtur, sayısal sıfır değildir. Düz RSI v1 sonucu 50 olarak korunur; T10'daki sürümlü 100 hedefi/migration işi kapanmaz.

Kaynak dönüşümleri OHLC üzerinden yapılır. Çizgi ve veri penceresi aynı seçimi kullanır. Açık temel mumdaki çıktı güncellenebilirdir. History genişleyince yüklü geçmiş başından yeniden hesaplanır; origin seed sabitliği veya TradingView exact paritesi iddia edilmez. Bu sınırlama ayar formunda görünür. EMA ayarı değişmesi RSI'nin mevcut manuel ölçeğini veya bağımsız volume pane'ini yeniden oluşturmaz. Gösterge konfigürasyonu bot aktivasyonu/emir yetkisi vermez; sayısal referans Python/TS float görüntü hesabıdır, kesin bot fiyatı değildir.

## Kayıt ve hata davranışı

GET/PUT `/api/workspaces/{workspace_id}/indicators`; chart-indicators/1. Migration 4 yeni `app_indicator_configs` tablosunu ekler; mevcut migration digest'leri değiştirilmez. Mevcut uygulama DB'si yükseltilirken standart migration yedeği alınır. Eski symbol/interval tercihi ve çizim kaydı ayrı kalır. Owner/workspace kapsamı korunur.

BEGIN IMMEDIATE, expected_revision ve request_id/digest ile atomik/idempotent kayıt yapılır. Değişen nesnenin revision'ı artar; aynı kalan nesne korunur. İstemci sunucudan doğrulanmış yanıt gelmeden grafiği değiştirmez. Kayıp onay yanıtında aynı taslak aynı request_id ile tekrar gönderilir; ikinci revision oluşmaz. 409 durumunda eski değer gösterilir, son kaydı yükleme açık eylemdir. Hata menü kapalıyken de grafiğin üstünde görünür. Yanıtın tüm ayar alanları ve revision ilerlemesi istekle eşleşmelidir. Yükleme hatası varsayılanları sunucuya yazmaz; kontrollere erişim doğrulanmış yüklemeden sonra açılır.

## Kabul

- **794 Python testi** geçti. Altı yeni grup: schema/limit/semantik reddi; idempotency/revision/owner/workspace ayrımı; bağımsız analysis.py ile tüm çıktılarda seed/warmup eşleşmesi; elle hesaplanmış EMA ve düz RSI; gerçek HTTP kayıt/çakışma/restart; paylaşılan fixture güncelliği.
- **227 frontend testi** geçti. Altı yeni test: strict config şeması; 21 fixture ile yedi kaynak/üç gösterge; varsayılan sonuç/kimlik korunması; warmup ve periyot 1; bileşik kaynak/düz RSI; kayıt yanıtının ayar/revision eşleşmesi. Veri penceresi etiket testleri kaynak adını içerir.
- TypeScript ve üretim Vite derlemesi geçti. Ana JS 544.01 kB, gzip 173.13 kB. Mevcut 500 kB uyarısı ve QA01 performans kabulü açık kalır.
- **14 yeni production App tarayıcı kontrolü** geçti: form/defaults, bütün çizgi noktalarında Python eşleşmesi, Data window, geçersiz form/cancel, kayıp onayda idempotent retry, eşzamanlı config çakışması ve görünür reload düğmesi, tekil görünürlük/uzun warmup, geri yüklemede artık veri olmaması, **50 gerçek kalıcı RSI pane aç/kapa döngüsü**, timeframe/coin/reload, 1024px açık/koyu modal ve sunucu restart.
- G02/G03/T08 için **39 ilgili regresyon tarayıcı kontrolü** geçti. G03 kaynak etiketleri ve asenkron kayıt tamamlanması testte güncellendi. G02 EMA açılırken RSI manuel ölçeğini korudu. İzole SQLite ve sentetik public market kullanıldı; kullanıcı hesabına test kaydı, hesap/emir çağrısı ve page error yok. Fiziksel GPU/touch veya canlı borsa/vendor hesap paritesi kabulü değildir.

Kanıt: `reports/chart-t09-validation-20261112.json`, `reports/t09-*.log`, açık/koyu PNG'ler ve SHA256 manifesti `reports/chart-t09-delivery-20261112.json`. Sözleşme: [indicators-v1.json](contracts/indicators-v1.json).
