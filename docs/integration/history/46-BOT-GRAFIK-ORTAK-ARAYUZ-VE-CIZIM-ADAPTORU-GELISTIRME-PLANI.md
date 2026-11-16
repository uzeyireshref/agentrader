# Bot–grafik ortak arayüzü ve çizim adaptörü geliştirme planı

Durum: **TAMAMLANDI — G0–G11 kabulden geçti**. Güncelleme: 15 Kasım 2026.

Dayanak: [44 — kabul planı](44-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-PLANI.md), [45 — araç bazında sonuçlar](45-TUM-GRAFIK-ARACLARI-BOT-YAZMA-OKUMA-TEST-SONUCLARI.md) ve `reports/all-chart-tools-20261114/capability-matrix.json`. Başlangıç regresyonu: 1163 Python, 343 frontend testi; bu sayılar yeni özelliklerin tamamlandığı anlamına gelmez.

## 1. Hedef ve çalışma sınırı

Bot, grafikteki nesneleri ve notları okuyabilmeli; seçilen veri bağlamında çizim/gösterge değerlerini HTTP üzerinden sorgulayabilmeli; verinin hesaplama için hazır olup olmadığını anlayabilmeli. Ardından kendi nesnelerini oluşturup düzenleyebilmeli, manuel çizimleri korumalı. API testi, gerçek bot adaptörü ve otonom strateji ayrı kabul aşamalarından geçmeli.

Geliştirme Binance Demo veri bağlamında sürer. Gerçek Binance bağlantısı açılmaz. Grafik ve bot aynı kaynak, ürün, fiyat türü, sembol ve zaman dilimini kullanır. İlk kabul aşamaları izole depolarda ve açıkça sentetik olarak işaretlenmiş verilerle yapılır; ardından salt okunur gerçek Demo veri gözlemi gelir. Bu planı uygulamak otomatik emir üretimini başlatmaz; hesaplama desteği emir yetkisi değildir. Mevcut işlem korumaları değiştirilmez. Nihai Demo işlem kabulü ayrı ve somut senaryoyla değerlendirilir.

## 2. Kapanacak eksikler

| No | Mevcut eksik | Hedef sonuç | Paket |
|---|---|---|---|
| E01 | Nesne/veri/hesaplama hazırlığı parçalı | Sürümlü ortak grafik bağlamı ve tutarlılık kontrolü | G1–G2 |
| E02 | Genel HTTP çizim hesaplama sorgusu yok | Tekil ve sınırlı toplu sayısal sorgu | G3 |
| E03 | 8 yeni kanal/pitchfork varyantında backend matematiği yok | Frontend ile aynı anlamda backend hesapları | G4 |
| E04 | Regresyon ara UTC çapalarında çizim kayboluyor | Belirli mum aralığı seçimi; açık hazırlık durumu; ara UTC desteği | G4 |
| E05 | Gösterge hesaplanmış serileri bot API'sinde yok | Parametre/sürüm ve warmup ile seri/son değer | G5 |
| E06 | İmleç/seçim/viewport vb. yalnız tarayıcıda | Sekme kimlikli, süreli UI bağlamı | G6 |
| E07 | Her nesnede uzun not ve not ilişkisi yok | Çizime bağlı, botça okunur/yazılır açıklamalar | G7 |
| E08 | Manuel/bot nesne kökeni ve koruması yok | Sunucunun uyguladığı köken/aktör ayrımı | G7–G8 |
| E09 | Genel bot çizim adaptörü yok | Aynı resmi API'yi kullanan kalıcı bot okuma/yazma adaptörü | G8 |
| E10 | Katalog bayrakları erişim katmanlarını anlatmıyor | Şema ve işlem bazında doğru yetenek keşfi | G1, G3–G5 |
| E11 | Fibonacci projection katalogda var, uygulanmamış | Anlamı tanımlanmış, çizilebilir/hesaplanabilir gerçek araç | G9 |
| E12 | Genel clipboard yapıştırma yok | Şemalı kopyala/yapıştır; Duplicate ile ayrım | G9 |
| E13 | Eski testlerde güncel olmayan beklentiler var | Güncel, uyumluluk ve arşiv testlerinin ayrılması | G0, G10 |
| E14 | API erişimi otonom kullanım sanılabiliyor | Gerçek bot adaptörüyle uçtan uca çiz/oku/hesapla senaryoları | G10–G11 |

Metin/not nesnelerine anlamsız matematik işlemleri eklenmez: içerik, ilişki ve fiyat/zaman konumu sorgulanır. Kanal gibi matematiksel araçlardaki eksik hesaplar ise geliştirilir; kalıcı olarak “görsel” etiketiyle kapatılmaz.

## 3. Ortak sözleşme

### 3.1 Grafik bağlamı

Önerilen uç noktalar mevcut route düzeniyle G1'de kesinleştirilecek; aşağıdakiler henüz uygulanmış API değildir:

| Yöntem/yol | Amaç |
|---|---|
| `GET /api/workspaces/{workspace_id}/chart-context` | Nesneler, ayarlar, veri hazırlığı ve isteğe bağlı UI oturumu |
| `POST /api/workspaces/{workspace_id}/chart-queries` | Aynı bağlamda sınırlı toplu çizim/gösterge hesapları |
| `POST /api/drawings/{drawing_id}/queries` | Nesne revizyonuna bağlı tekil matematik sorgusu |
| `POST /api/workspaces/{workspace_id}/indicator-queries` | Hesaplanmış gösterge serileri/son değer |
| `PUT /api/workspaces/{workspace_id}/ui-sessions/{ui_session_id}` | Tarayıcının kendi anlık durumunu yayımlaması |
| `GET /api/workspaces/{workspace_id}/ui-sessions` | Aynı kullanıcıya ait oturumların güncellik bilgisi |

Çizim CRUD işlemleri mevcut `/drawings` ve `/drawing-operations` üzerinden sürer; ikinci, farklı kuralları olan bir yazma yolu kurulmaz. Bot adaptörü bunları kullanır. Büyük veri/seri sorgularına sayfalama, çıktı ve süre sınırı konur; varsayılan snapshot bütün geçmişi indirmez.

Her yanıt şu ayrımları taşır:

- `schema_version`, `context_id`, sunucu UTC zamanı, hesap sürümü.
- Demo kaynak/ortam, ürün, fiyat türü, sembol, interval, veri epoch/generation/sequence ve mevcut kanıt özeti.
- Nesne ID/revizyonları; gösterge ayar revizyonu; tüketilen mum aralığı ve veri özeti/hash'i.
- Ham nesne, türetilmiş hesap, kalıcı görünüm ayarı ve geçici UI durumu ayrı alanlarda.
- Veri sayısı, gereken veri sayısı, warmup, eksik aralıklar, son kapalı mum, açık mum kullanımı, kaynak saatinin güvenilirliği ve stale durumu.
- `READY`, `WARMUP`, `WAITING_FOR_DATA`, `STALE`, `SOURCE_MISMATCH`, `INVALID_INPUT`, `UNSUPPORTED_OPERATION`, `UI_UNAVAILABLE` gibi belgelenmiş durumlar. Durumun kapsamı belirtilir: geometri hesabına hazır olmak işlem için uygun olmak değildir.

Tek snapshot'ın farklı depolardan atomik okunduğu varsayılmaz. Okuma öncesi/sonrası revizyon ve veri kimliği denetlenir; değişim varsa sınırlı tekrar veya `CONTEXT_CHANGED` sonucu döner. İstemci eski snapshot üzerine yeni değerleri sessizce birleştiremez. Nesne değişiminde 409; erişim/sahip sınırları mevcut politikayla korunur.

### 3.2 Sayı ve zaman anlamı

Fiyatlar decimal metin olarak taşınır; uygun sonuçlarda tam kesir korunur. İrrasyonel/istatistiksel sonuçlarda açık hassasiyet ve tolerans kullanılır. NaN/Infinity/null ile sessiz başarı yoktur. UTC saniye ile milisaniye karışıklığı reddedilir. Fiyatı tick'e uyarlama yalnız açık politika ile yapılır; görüntü yuvarlaması ham sayıyı değiştirmez.

Sorgu, işlem türünü ve gereken girdileri açıkça ister: örneğin `priceAt`, `boundsAt`, `level`, `contains`, `distance`, `measurement`, `riskReward`. Her araç her işlemi desteklemez. Doğrusal/log ölçek anlamı frontend ile eşleştirilir; matematik tanımı olmayan birleşim gerekçeli hata verir. Aynı nesne farklı eski/yeni şemadaysa şema kimliği sonucun parçasıdır.

## 4. Sıralı geliştirme paketleri

### G0 — Başlangıç kaydı ve eski test temizliği

Mevcut 22 tür/25 varyant, 9 gösterge yapılandırması ve UI özellikleri satır satır envanterlenir. Güncel kaynak ve derleme kimlikleri kaydedilir. Önceki değişiklikler korunur.

`check_chart_t06.py` güncel toolbar akışına uygun teste dönüştürülür; eski `chart-channel/1` kayıtlarının okunması/çizilmesi ayrı uyumluluk testine alınır. `check_chart_bot_contract.py` içindeki güncel üretim davranışını sınayan kısımlar korunur, eski tasarım örnekleri arşive taşınır ve güncel kabul listesinden çıkarılır. Gerçekten başka/eski grafiğe ait dosya varsa import/komut/doküman referansları araştırılıp kaldırılır. Mevcut kullanıcı kayıtlarının kullandığı şema yalnız “eski” adı nedeniyle silinmez.

Kabul: normal test komutları güncel davranışları sınar; eski sözleşme örneği güncel bot kabulü gibi raporlanmaz; taşınan/kaldırılan her dosyanın gerekçesi listelenir.

### G1 — Katalog ve sözleşmenin kesinleştirilmesi

Tek `readable` yerine `metadata_read`, `text_read`, `geometry_query`, `indicator_series`, `ui_state_read`, `create`, `edit`, `delete`, desteklenen işlemler/ölçekler/veri gereksinimleri ayrı tanımlanır. Yeteneğin uygulanmış olup olmadığı ve kayıt şeması açık yayımlanır. Fibonacci projection bu aşamada açıkça `NOT_IMPLEMENTED` kalır; G9 sonrası yetenek açılır.

Kabul: katalogdaki uygulanmış her özellik için test ve gerçek handler vardır. Bot gereksiz deneme/422 zinciri olmadan hangi işlemi çağıracağını keşfedebilir.

### G2 — Ortak salt okunur grafik bağlamı

Nesne deposu, gösterge ayarları ve mevcut Demo veri/kanıt hizmetlerinden ortak okuma servisi kurulur. Kullanıcı/çalışma alanı sınırı, revision ve bağlam değişimi kontrol edilir. UI olmadan da kalıcı nesneler ve veri durumu okunur.

Kabul: farklı sembol/interval/kaynak verisi karışmaz; veri kesilince stale görünür; eksik geçmiş ve açık mum ayırt edilir; eşzamanlı düzenlemede tutarsız başarı verilmez. Kullanıcı çizimlerinde veya emir kayıtlarında yazma olmaz.

### G3 — Genel HTTP hesaplama arayüzü

Mevcut 14 varyantın Python hesapları resmi HTTP sorgularına bağlanır. Tekil/toplu sorgu aynı servis ve hata sözlüğünü kullanır. İstenen tarih/fiyat/oran ile kullanılan nesne/veri revizyonu yanıtta bulunur. Toplu yanıtta nesne bazında başarısızlık görünür, sınırlar uygulanır.

Kabul: Fibonacci seviyeleri, çizgi fiyatı/mesafesi, bölge içerme, eski kanal sınırları, cetvel ve risk/ödül için bağımsız sayısal referanslar HTTP üzerinden doğrulanır; desteklenmeyen işlem gerekçeli döner. İzinsiz nesneye hesap yoluyla erişilemez.

### G4 — Yeni kanal matematiği ve regresyon düzeltmesi

Parallel, flat, disjoint, regression, pitchfork, Schiff, modified Schiff ve inside pitchfork için backend model/hesap geliştirilir. Frontend modelinin yalnız ekran pikseli çıktısı yerine veri koordinatlarındaki anlamı esas alınır. Sınırlar, orta çizgi, tanımlı seviyeler, eğim ve sorgu tarihindeki değerler araç bazında belgelenir. Türetilmiş tutamaç ile ham çapa ayrılır.

Regresyon ara zaman politikası: kullanıcı çapaları aynen saklanır; her zaman mevcut intervalde **içinde bulunduğu gerçek muma** eşlenir ve kullanılan etkin mum başlangıçları ayrıca gösterilir. Eşleme en yakın muma gizli yuvarlama yapmaz; boşlukta/gelecekte sahte mum yaratmaz. İki çapa aynı muma düşerse yetersiz örnek durumu döner. Kayıp/geçmişi yüklenmemiş mumda veri beklenir; veri geldiğinde ham çapalar kaymadan tekrar hesaplanır. Hesaba giren fiyat alanı, açık mum politikası, en az örnek sayısı, sapma/bant tanımı ve lineer/log davranışı tek sözleşmede belirlenir. Frontend ve backend aynı seçili mumlarla çalışır.

Kabul: mevcut 2 ara-UTC engel senaryosu gerçek veri geldikten sonra başarılı hesap/çizim senaryosuna dönüşür. Mum sınırı, aralık içi, ters çapa, aynı mum, veri boşluğu, gelecek, yeni mum, reload ve log örnekleri sınanır. Diğer 7 aile aracı sayısal HTTP ve tarayıcı paritesini geçer. “Beklenen engel” etiketi bu eksiğin kapanışı yerine kullanılmaz.

### G5 — Gösterge hesap ve seri erişimi

EMA iki örneği, RSI, SMA, ATR, MACD, BB, session ve anchored VWAP mevcut davranışlarıyla sunucu hesap hizmetine alınır. Parametre, kaynak fiyat alanı, timezone/session sınırı, anchor UTC, warmup ve açık/kapalı mum seçimi yanıtta bulunur. MACD/BB gibi çok çıktılı göstergeler alan bazında döner. Son değer ile istenen tarih/seri aynı hesap yolunu kullanır.

Kabul: mevcut üç sayısal tarayıcı grubunun referansları HTTP sonuçlarını da doğrular. Eksik geçmiş, sıfır hacim, reconnect, anchor öncesi veri, farklı timezone ve ayar değişimi test edilir. Yetersiz veri sıfır değer gibi sunulmaz.

### G6 — Geçici ekran durumu köprüsü

Frontend her sekme için ayrı UI oturumu yayımlar: seçili sembol/interval, viewport/zaman-fiyat aralığı, ölçek, seçili nesneler/araç, crosshair/hover mumu, magnet, görünür paneller/göstergeler, tema, favoriler ve yerel bildirim tercihleri. Undo/redo için yığın içeriği yerine kullanılabilirlik ve ilgili revizyon özeti verilir. Kaydedilmiş profil/şablon ayrı tutulur. Gönderimler değişime bağlı ve hız sınırlıdır; pointer hareketi sunucuyu her pikselde yüklemez.

UI oturumu sahipli ve TTL'lidir. Bot açık oturum kimliği seçer; iki sekmenin durumu birleşmez. Tarayıcı kapalıysa, bağlantı kopmuşsa veya TTL dolmuşsa `UI_UNAVAILABLE`/stale döner. İstemcinin bildirdiği ekran durumu güvenilir piyasa kanıtı veya emir yetkisi sayılmaz. Bot işlemleri için hover varsayılan sorgu zamanı yapılmaz.

Kabul: iki sekme, kapanma/yeniden açılma, kopma, eski paket, seçim silinmesi ve profil–ekran farkı test edilir. Gizli/başka kullanıcı oturumu okunamaz. Bot arayüzü üzerinden anlık durum gerçekten alınır.

### G7 — Nesne kökeni, manuel koruma ve bağlı notlar

Eski nesneler güvenli biçimde `manual/legacy` kabul edilir. Bot kökeni istemcinin serbest JSON alanıyla taklit edilemez; sunucunun doğruladığı aktöre bağlanır. Mevcut yerel kullanıcı doğrulama modeli incelenerek kullanıcı ve bot yetkisi ayrılır. Nesnede origin, bot/strategy kimliği, oluşturulma/değişim bilgisi ve revizyon izi bulunur.

Tüm çizimlere uzun not bağlanabilir: ayrı not kaydı + hedef nesne ilişkisi, revizyon, Unicode/çok satır ve içerik sınırı. Mevcut text/note/channel text kayıpsız korunur; geometri şemasına tanımsız alan doldurulmaz. Snapshot ve sorgulardan ilişkili notlar okunur. Silinen hedefte notun arşiv/ilişki durumu açık tanımlanır.

Kabul: bot manuel nesneyi okuyabilir; normal bot yazma akışında onu değiştiremez, silemez veya bot kökenine çeviremez. Kilit, bulk, Duplicate, import ve undo/redo yoluyla koruma aşılamaz. Not düzenleme yetkileri de aynı sınırı izler. Mevcut kayıtlar için yedekli migration ve geri alma yolu doğrulanır.

### G8 — Gerçek bot okuma/yazma adaptörü

Botun kullanacağı arayüz, resmi HTTP servisleri üzerinden keşfet/bağlam oku/hesapla/çiz/not ekle/güncelle/sil işlemlerini sunar. Her yazma expected revision, request ID ve bot namespace taşır. Aynı isteğin timeout sonrası tekrarı ikinci çizim üretmez; aynı anahtarla farklı içerik reddedilir. Yeniden başlatmada bot kendi nesnelerini bulur. Yetkiler sunucuda zorlanır; yalnız adaptör içi kontrolle bırakılmaz.

Bot sadece kendi nesnelerini yönetir. Manuel çizimi değiştirme bu sürümde varsayılan dışıdır; ileride ayrı, açık yetkilendirilmiş bir özellik olarak ele alınabilir. Bot yazımı kullanıcı undo geçmişini veya kaydedilmiş profilini sessizce yeniden yazmaz; çatışma ve eşzamanlı kullanıcı düzenlemesi açık sonuç üretir.

Kabul: test istemcisi yerine gerçek bot adaptörü kullanılarak 25 varyant oluşturulur, not yazılır, fresh snapshot'tan okunur, sayısal sorgulanır ve yalnız bot nesneleri temizlenir. Restart, timeout, yarış, kilit, eski revizyon ve kaynak uyuşmazlığı test edilir; manuel nesne/notlar birebir korunur.

### G9 — Eksik araç ve etkileşimlerin tamamlanması

Fibonacci projection için önce ürün anlamı kesinleştirilir: mevcut Fibonacci extension ile farkı, çapa sayısı/rolleri, oranlar ve uzatma davranışı belgelenir. Ardından şema, toolbar, renderer, ayarlar, backend hesapları, HTTP sorguları, bot adaptörü ve katalog birlikte geliştirilir. Eğer aynı aracın mükerrer adı olduğu kanıtlanırsa iki farklı araç gibi gösterilmez; açık alias/migration uygulanır ve gerekçesi kaydedilir.

Genel kopyala/yapıştır, sürümlü ve doğrulanan nesne paketiyle eklenir. Geometri, not ilişkisi ve desteklenen stil korunur; ID/revizyon/köken kopyalanmaz. Elle yapıştırılan nesne manuel, botun çoğalttığı nesne bot kökenlidir. Kaynak sembol/interval uyumsuzluğu açıkça ele alınır; otomatik fiyat ölçekleme yapılmaz. Duplicate mevcut ayrı işlem olarak korunur.

Kabul: yeni/alias araç katalogda gerçeği anlatır; desteklenen tüm katmanlarda test edilir. Clipboard bozuk şema, farklı sembol, uzun not ve tekrar yapıştırmayı kapsar; manuel koruma delinmez. Yeni araç gerçek varyant sayısına eklenerek matris yeniden üretilir.

### G10 — Ortak kabul ve regresyon

Paket başına anlamlı testler çalıştırılır; son aşamada tüm güncel Python/frontend, browser kabulü ve derleme tamamlanır. Backend ve frontend aynı bağımsız fixture vektörlerine karşı doğrulanır; yalnız birbirinin aynı hatalı sonucunu üretmeleri başarı sayılmaz. Tam kesir/decimal sonuçlar birebir; istatistiksel/log sonuçlar gerekçelendirilmiş hata toleransıyla ölçülür. Görsel çapa toleransı en çok 1 CSS px korunur.

Her araç satırında ham okuma, metin/not, HTTP matematik, veri hazırlığı, render, UI bağlamı, gerçek bot adaptörü ve manuel koruma ayrı sonuçlanır. Eski/yeni şema, kesirli UTC, gelecek veri, linear/log, reload, iki sekme, DPR ve hata koşulları kapsanır. Mevcut toplam test sayıları hedef kota olarak kullanılmaz; yeni özelliklerin anlamlı davranışları sınanır.

Kabul: destekleneceği kararlaştırılan matematiksel aracın hesabı eksik kalıp yeşil sonuç verilmez. Metin için anlamsız matematik reddi ise doğru davranıştır. Üretim kaynak/derleme kimlikleri, test kanıtları, migration ve açık kalan maddeler raporlanır.

### G11 — Demo üzerinde bot kullanımının gözlemi

Önce salt okunur gerçek Demo veri akışıyla bağlam ve hesaplar gözlenir. Ardından ayrı çalışma alanında, manuel sentinel nesneleri yanında gerçek bot adaptörü belirli zaman/fiyatlarda çizim üretir, ilgili notu yazar ve aynı nesneyi HTTP hesaplarıyla tekrar okur. Bu, adaptörün çalışan runtime'a bağlandığını kanıtlar.

Sonra küçük, deterministik bir çizim stratejisiyle otonom kullanım sınanır: hangi kapalı mum/veri snapshot'ından hangi araç ve çapaların seçildiği, neden güncellendiği not/kanıt kaydında bulunur. Araç erişim kabulü için kârlılık iddiası veya bütün araçları tek stratejide kullanma şartı konmaz. Yanlış veri/stale durumda yeni strateji kararı durur. Emir gönderimi bu kabulün koşulu değildir.

Kabul: süreç yeniden başlasa da aynı veri ikinci nesne üretmez; manuel nesneler korunur; botun gerçekten yaptığı çağrılar ve kullandığı hesaplar kanıtlanır. Yalnız örnek JSON veya test istemcisi bu aşamanın yerine geçmez.

## 5. Bağımlılıklar ve teslim sırası

Uygulama sırası: **G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8 → G9 → G10 → G11**. Paket içinde gerekli küçük migration veya yardımcı servis ilgili paketin parçasıdır; tamamlanmamış temelin üzerine kabul etiketi verilmez.

İlk kullanılabilir teslim G2 ile salt okunur bağlam; ikinci teslim G3–G5 ile sayısal HTTP erişimi; üçüncü G6 ile UI okuması; dördüncü G7–G8 ile korumalı bot yazımı; son teslim G9–G11 ile eksik araçlar ve gerçek runtime kabulüdür. Her pakette yapılanlar, testler, kalanlar ve sonraki paket kaydedilir. Önce bütün sistemi bitirip en sonda test etme yöntemi uygulanmaz.

Başlıca değişim alanları: `agentrader/api/`, `agentrader/drawings/`, veri/kanıt ve gösterge hizmetleri, migration/aktör doğrulama, `frontend/src/channelFamily.ts`, grafik durum/etkileşim bileşenleri, bot runtime adaptörü, `tests/`, `frontend/tests/`, güncel browser scriptleri. Kesin dosya ayrımı ilgili pakette mevcut mimariye göre yapılır.

## 6. Planın tamamlanma ölçütü

- Bot desteklenen bütün çizimleri/notları resmi arayüzden okuyup kendi alanında yazabiliyor.
- Matematiksel araçların belgelenmiş hesapları ve gösterge serileri HTTP üzerinden kaynak/revizyon/hazırlık bilgisiyle alınabiliyor.
- Ara UTC regresyon hatası giderilmiş; eksik veri doğru ve görünür durum üretiyor.
- Geçici UI durumu oturum kimliği ve güncelliğiyle okunabiliyor; tarayıcısız çalışma açık davranıyor.
- Manuel nesneler, notlar ve kilitler botun bütün yazma yollarında korunuyor.
- Katalog, uygulanmış araçlar ve test listesi birbiriyle uyumlu; eski prototipler güncel kabul diye sunulmuyor.
- Gerçek bot adaptörü ve deterministik çizim stratejisi Demo bağlamında kanıtlanmış; otomatik işlem yetkisi ayrı tutulmuş.

G0 uygulama ve doğrulama kaydı: [G0 teslimi](../../../reports/chart-interface-g0-20261115/README.md). G1 uygulama ve doğrulama kaydı: [G1 teslimi](../../../reports/chart-interface-g1-20261115/README.md). G2 uygulama ve doğrulama kaydı: [G2 teslimi](../../../reports/chart-interface-g2-20261115/README.md). G3 uygulama ve doğrulama kaydı: [G3 teslimi](../../../reports/chart-interface-g3-20261115/README.md). G4 uygulama ve doğrulama kaydı: [G4 teslimi](../../../reports/chart-interface-g4-20261115/README.md). G5 uygulama ve doğrulama kaydı: [G5 teslimi](../../../reports/chart-interface-g5-20261115/README.md). G6 uygulama ve doğrulama kaydı: [G6 teslimi](../../../reports/chart-interface-g6-20261115/README.md). G7 uygulama ve doğrulama kaydı: [G7 teslimi](../../../reports/chart-interface-g7-20261115/README.md). G8 uygulama ve doğrulama kaydı: [G8 teslimi](../../../reports/chart-interface-g8-20261115/README.md). G9 uygulama ve doğrulama kaydı: [G9 teslimi](../../../reports/chart-interface-g9-20261115/README.md). G10 uygulama ve doğrulama kaydı: [G10 teslimi](../../../reports/chart-interface-g10-20261115/README.md). G11 uygulama ve gerçek Demo runtime doğrulama kaydı: [G11 teslimi](../../../reports/chart-interface-g11-20261115/README.md). Planın G0–G11 paketleri tamamlanmıştır; emir gönderimi ve kârlılık iddiası bu kabulün koşulu değildir.
