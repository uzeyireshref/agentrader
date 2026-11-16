# Crypto bot araştırması ve Agentrader yetenek değerlendirmesi

**Geliştirme başladı:** [24 paketlik uygulama planı](../../development/exchange-operations-20261115/PLAN.md) ve [ilerleme kaydı](../../development/exchange-operations-20261115/PROGRESS.md). Aşağıdaki araştırma sonuçları tarihli başlangıç kanıtıdır. G01 ile ACK/RESULT yanıt tercihi normal V2 SINGLE girişine eklendi.

**Güncel kapanış denetimi:** [5–8 araştırma teslimi](RESEARCH-CLOSURE-5-8.md), [birleşik açıklar](FINAL-GAP-REGISTER.md), [repo/skill kararı](REPOSITORY-SELECTION.md). Başlangıç 555 kayda 3 resmi CM ek işlem bulundu. Tam sözleşmesi açık kalan alanlar kapanış raporunda belirtilmiştir.

**Son geniş tur:** [1–5 araştırma teslimi](BROAD-RESEARCH-1-5.md). Bu teslim yeni sözleşme, bot karşılaştırması ve geniş sembol ölçümlerini içerir. Aşağıdaki ilk ölçüm sayıları tarihsel başlangıç kaydıdır.

[Kapsamlı araştırma planı](RESEARCH-PLAN.md) bütün ürünleri, araştırma teslimlerini ve geliştirme planına geçiş koşullarını tanımlar.

**Güncel kapsam 15 Kasım 2026 tarihinde borsa işlem yetenekleri olarak düzeltildi.** Çalışma sırası [araştırma planında](RESEARCH-PLAN.md) kayıtlıdır. Aktif değerlendirme [Borsa işlem kapsamı](EXCHANGE-CAPABILITY-SCOPE.md) ve [95 işlem envanteri](EXCHANGE-OPERATIONS.md) belgelerindedir. Aşağıdaki önceki araştırmanın strateji/backtest önerileri kullanıcının mevcut geliştirme önceliklerini temsil etmez.

15 Kasım 2026. İnceleme mevcut çalışma ağacındaki Python çekirdeğini, bot–grafik entegrasyonunu, testleri, resmi borsa dokümantasyonunu ve GitHub projelerini kapsar. Araştırma sorularını işlem yürütme, strateji araştırması, çoklu coin ölçeği ve geliştirme araçları üzerinden ele aldım. Kaynak evreni sürekli genişlediği için internetin tamamının tarandığına ilişkin bir kapsam iddiası yoktur. İncelenen kaynaklar [kaynak dizininde](sources.md) kayıtlıdır.

## Ölçülen sonuçlar

| Ölçüm | Sonuç | Kanıt |
|---|---|---|
| Mevcut Python regresyon paketi | 1.262 test, 137,326 saniye, OK | [Çalıştırma kaydı](../../../reports/crypto-bot-research-20261115/validation-summary.json) |
| Araştırma senaryo kataloğu | 128 somut senaryo | [Senaryolar](SCENARIOS.md), [JSON katalog](scenario-catalog.json) |
| Kod ve tekil test tanığı eşleştirilen senaryo | 64 senaryonun 64 regresyonu geçti | [Yetenek denetimi](../../../reports/crypto-bot-research-20261115/capability-audit.json) |
| Uçtan uca geliştirme açığı belirlenen senaryo | 64 | CB-065–CB-128 |
| Demo aktif USDT perpetual evreni | 528 sembol | [Sembol ve filtre snapshotı](market-universe.json) |
| Sembol başına emir doğrulama ölçümü | 527 sembolde 8.432 kontrol geçti | [Emir sözleşmesi denetimi](../../../reports/crypto-bot-research-20261115/market-contract-audit.json) |
| Veri nedeniyle tamamlanamayan ölçüm | SXPUSDT için 16 kontrol | Mark fiyatı ile minimum fiyat filtresi uyuşmazlığı |
| İncelenen GitHub deposu | 16 | [Metadata snapshotı](github-repositories.json) |
| Skill değerlendirmesi | ccxt-python kaldırıldı | Mevcut doğrudan Binance adaptörü geliştirme hedefi için gerekli görülmedi |

64 mevcut senaryo bütün yetenek envanterinin sayısı olarak yorumlanmamalıdır. Katalog karşılaştırma için seçilmiş tanıklı örnekler içerir. Benzer şekilde 64 açık, incelenen mevcut üretim yollarında hedeflenen uçtan uca akışın bulunamadığı alanları gösterir. Kodda temel parçalar bulunan alanların tamamlanması için ek çalışmalar vardır. Her iki grup da ölçüm kapsamıyla sınırlıdır.

## Bir crypto botun yapabilmesi gerekenler

### Pazar verisini ve işlem evrenini yönetme

Bot aktif kontratları keşfetmeli, ürün ve fiyat kaynağını ayırt etmeli, tick/lot/minimum nominal kurallarını sembol bazında uygulamalı. Coin seçimi hacim, spread, fiyat hassasiyeti, listeleme yaşı, veri yeterliliği ve volatiliteyi birlikte kullanmalı. Sembol listesinin geçmiş sürümleri saklanmalı. Bu gereksinimlerin ilk grubu Binance sembol sözleşmesinden, seçim filtreleri Freqtrade’in pairlist yapısından çıkarılmıştır. [Binance exchangeInfo](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information), [Freqtrade pairlist ve protections](https://www.freqtrade.io/en/stable/plugins/)

### Emir ve pozisyon yaşam döngüsünü tamamlama

Giriş, kısmi dolum, iptal, değiştirme, stop, hedef, pozisyon azaltma ve kapanış birbiriyle tutarlı olmalı. Yanıt kaybında borsadaki durumu sorgulama, istemci emir kimliğiyle tekilleştirme, yeniden başlatma ve hesap sahipliği kontrolleri gerekli. Borsanın sembol veya hesap bazında desteklediği emirler ayrıca keşfedilmeli. Çoklu stratejiler ortak risk ve bakiye üzerinden koordine edilmeli. [Binance emir sözleşmesi](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order), [Binance genel davranış](https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info), [Nautilus execution](https://nautilustrader.io/docs/latest/concepts/execution/)

### Strateji ve yürütme algoritmalarını geliştirme

Yönlü trend, kırılım, ortalamaya dönüş ve volatilite stratejileri araştırılabilir. Grid ve DCA stok biriktirme davranışı, TWAP zaman dilimlemesi, piyasa yapıcılık envanteri ve arbitraj bacakları için farklı yürütme sözleşmeleri gerekir. Bu aileleri bot kapsamına alma sırası veri ve pazar desteğine göre seçilmeli. Hummingbot’un yürütücü ayrımı bu tasarım için doğrudan inceleme kaynağıdır. [Hummingbot executors](https://hummingbot.org/strategies/v2-strategies/executors/), [TWAP](https://hummingbot.org/strategies/v2-strategies/executors/twapexecutor/), [arbitraj](https://hummingbot.org/strategies/v2-strategies/executors/arbitrage-executor/)

### Strateji başarısını maliyetlerle ölçme

Tarihsel simülasyonda ücret, spread, kayma, funding, kısmi dolum ve sermaye paylaşımı bulunmalı. Veri çözünürlüğünün aynı mumdaki stop/hedef sırasını çözmeye yetmediği durumlar açık bir politikayla sonuçlanmalı. Lookahead ve başlangıç geçmişine bağlı gösterge sapmaları ayrıca sınanmalı. Örnek dışı dönem, walk-forward ve maliyet duyarlılığı bu projeye önerdiğim kabul yöntemleridir. [Freqtrade backtesting](https://www.freqtrade.io/en/stable/backtesting/), [lookahead](https://www.freqtrade.io/en/stable/lookahead-analysis/), [recursive analysis](https://www.freqtrade.io/en/stable/recursive-analysis/)

### Risk ve operasyon sürekliliğini koruma

İşlem başı zarar, hesap geneli zarar, günlük bütçe, nominal, teminat ve pozisyon sayısı birlikte yönetilmeli. Portföy araştırmasına korelasyon kümeleri, drawdown ve stres senaryoları eklenmeli. Süreç, veri ve ağ kesintilerinde rezervasyon ve emir durumları uzlaşmalı. Gerçekçi maker dolum değerlendirmesi için defter kuyruğu ve gecikme modellemesi gerekir. [Nautilus backtesting](https://nautilustrader.io/docs/latest/concepts/backtesting/), [HftBacktest](https://hftbacktest.readthedocs.io/en/latest/)

## Bizde bulunan yetenekler

| Alan | Mevcut karşılık | Doğrulama düzeyi |
|---|---|---|
| Long/short, one-way/hedge | order_rules, plan_v2, v2_runner | Tekil tanıklı regresyonlar geçti |
| Limit/market ve koşullu emir parametreleri | order_rules.validate_order | 527 sembolün güncel filtreleriyle çevrimdışı kontroller geçti |
| Stop, hedef, kademeli çıkış, break-even | v2_runner | İlgili regresyonlar ve tam Python paketi geçti |
| Takip stopu | trailing, grid_trailing, grid_native_stop | Long/short, restart ve yanıt kaybı testleri mevcut |
| Yönlü ve neutral grid | grid_runner, neutral_runner | Çoklu oturum ve kısmi dolum testleri mevcut |
| Ortak risk ve rezervasyon | portfolio, reservations, account_runtime | İki sembol, iki grid, ortak bütçe ve sahiplik testleri geçti |
| Hesap ve kullanıcı akışı | user_stream, history_reconciliation | Olay tekilleştirme ve REST uzlaştırma testleri mevcut |
| Kurtarma | recovery_guardian, watchdog | Bağımsız kilit, koruma ve devralma testleri mevcut |
| Grafik okuma/yazma | ChartBot, chart_context, chart_queries | 64 tanıklı senaryonun grafik grubundaki 8 test geçti |
| Gösterge, alarm ve sinyal köprüsü | indicator_queries, price_alerts, chart_execution | Tam Python regresyon paketine dahil |

Kaynak kodundaki borsa adaptörü Binance USD-M Demo adresine bağlı. Projenin API yetenek kataloğunda 95 belgelenmiş işlem bulunuyor. Katalog tarihi 6 Kasım 2026. Katalogdaki endpoint, adaptör izin listesi, test edilen uygulama akışı ve belirli sembolde borsa kabulü için ayrı kanıt gerekir. Mevcut capabilities modülü de okuma erişimi ve yazma yetkisini ayrı alanlarda taşıyor. [Adaptör](../../../agentrader/shared/exchange.py), [yetenek raporu](../../../agentrader/bot/capabilities.py), [API kataloğu](../../../agentrader/data/usdm_capabilities.json)

DrawingStrategy kapalı mum EMA20 değerini bot çizimine taşır ve kendi sözleşmesinde order_authority=False döndürür. Ayrıca projede grafik sinyalinden onaylı Demo planına giden farklı bir chart_execution akışı bulunur. Strateji araştırmasında her iki giriş noktasının çıktısı ayrı ölçülmelidir. [Çizim stratejisi](../../../agentrader/integration/chart_strategy.py), [sinyal yürütmesi](../../../agentrader/integration/chart_execution.py), [G11 teslimi](../../chart/DEMO-STRATEGY-G11.md)

## Geliştirme açıkları ve öncelikler

| Öncelik | Açık | Mevcut temel | Tamamlanma ölçütü |
|---|---|---|---|
| P1 | Çoklu coin tarayıcı ve sıralama | Sembol verisi, çoklu oturum ve ortak risk | Evren snapshotı, filtre nedenleri, aday puanı, ortak bütçede deterministik seçim |
| P1 | Portföy strateji backtest’i | Mum deposu, replay ve gösterge hesapları | Emir/dolum/nakit defteri, ücret/funding, drawdown ve tekrarlanabilir rapor |
| P1 | Strateji kütüphanesi | Göstergeler, çizim bağları ve onaylı plan yolu | En az üç stratejinin aynı sözleşmeyle örnek dışı karşılaştırması |
| P1 | Lookahead ve recursive değerlendirme | Kapalı mum, warmup ve kaynak doğrulama | Veri kesme ve geçmiş uzunluğu değişiminde otomatik sonuç karşılaştırması |
| P1 | 500+ sembol çalışma kabulü | Ortak feed ve request governor | Bağlantı sayısı, veri yaşı, kuyruk gecikmesi ve bellekle süreli yük raporu |
| P2 | DCA/TWAP/POV yürütücüler | Emir günlüğü ve rezervasyon | Toplam miktar/bütçe sınırı, artık dolum ve restart kabulü |
| P2 | Korelasyon ve drawdown risk katmanı | Nominal, stop, günlük zarar ve marj bütçeleri | Aynı risk altında portföy küme limiti ve equity tepesinden düşüş davranışı |
| P2 | İşlem performansı ve operasyon paneli | Geçmiş uzlaştırma, servis durumları | Net PnL, maliyet, gecikme, veri boşluğu ve koruma ölçümleri |
| P3 | Funding/baz arbitrajı ve market making | USD-M Demo tek pazar çekirdeği | İkinci pazar, bacak riski, hedge ve maliyet sonrası kabul |
| P3 | Spot/COIN-M/opsiyon/DEX/ML | Genel grafik ve araştırma altyapısı | Ürüne özel adaptör, veri, risk ve muhasebe sözleşmeleri |

Tablodaki açıklar kaynak incelemesi ve mevcut bağımlılık/giriş noktalarıyla belirlenmiştir. Chart replay olay ve bağ semantiğini sınar. Portföy PnL, fill queue ve funding simülasyonu için ek defter ve simülasyon katmanı gerekir. DCA’nın grid davranışına benzemesi takvimli DCA kabulünü tamamlamaz. Ayrıntılı koşullar CB-065–CB-128 satırlarında kayıtlıdır. [Senaryo kataloğu](SCENARIOS.md), [mevcut replay](../../../agentrader/chart/chart_replay.py)

## 528 coin üzerinde yapılan ölçüm

Halka açık Demo exchangeInfo yanıtından TRADING, PERPETUAL ve USDT koşullarını sağlayan 528 kontrat seçildi. Ayrı premiumIndex snapshotı fiyat girdisini sağladı. Snapshotlar alındıkları zaman ve kaynak URL ile saklandı. Tüm ölçümler mevcut validate_order fonksiyonuna çağrı yapar. [Evren](market-universe.json), [mark fiyatları](mark-prices.json), [ölçüm kodu](../../../scripts/research/audit_market_contracts.py)

Her uygun sembolde sekiz kabul ve sekiz ret kontrolü uygulandı.

- Kabul kontrolleri long limit, short limit, long market, hedge long, hedge short, reduce market, stop market ve trailing parametrelerini kapsar.
- Ret kontrolleri bozuk tick, bozuk lot, sıfır miktar, NaN fiyat, hedge reduceOnly çakışması, market emrine limit alanı, geçersiz GTD ve callback oranını kapsar.
- 527 sembolde 8.432 kontrol geçti. Dönen önerilerin execution_authorized alanı da denetlendi.
- SXPUSDT snapshotında mark fiyatı 0.00006630, minimum fiyat ve tick 0.0001. Bu nedenle ilgili 16 kontrol veri engeli olarak ayrıldı. Başlangıçta bu durum ölçüm aracında sıfıra bölme üretti. Araç şimdi uyuşmazlığı INPUT_DATA_BLOCKED olarak raporluyor.
- Toplam planlanan 8.448 kontrolün 16’sı bekliyor. Bu kısmi sonuç nedeniyle ölçüm komutu 1 çıkış kodu verir. Çıktıdaki record_count alanı 8.433 rapor satırını sayar. case_count ve executed_case_count 8.432 yürütülen kontrolü, blocked_case_count 16 bekleyen kontrolü gösterir.

Bu turdaki borsa gözlemleri halka açık veri sorgularıdır. Sembol bazında gerçek emir kabulü, dolum kalitesi, strateji getirisi ve 528 eşzamanlı oturum performansı henüz ölçülmedi. Bu alanların kabul durumu raporlarda NOT_RUN olarak tutulur. [Ayrıntılı sonuç](../../../reports/crypto-bot-research-20261115/market-contract-audit.json)

## İşlem fırsatlarını araştırma yöntemi

İlk araştırma evreni mevcut USD-M sembollerinden kurulmalı. Kullanılacak geçmişin hangi gün hangi coinleri içerdiği kaydedilmeli. Üç başlangıç ailesi öneriyorum. EMA trend stratejisi düşük işlem sıklığıyla çekirdeği sınar. Donchian kırılımı hareketli piyasalardaki takip davranışını sınar. RSI/Bollinger dönüşü yatay rejimde farklı bir giriş ailesi sağlar. Her aile long/short, 5m/15m/1h ve yükseliş/düşüş/yatay/yüksek volatilite dönemlerinde ayrı raporlanmalı. Bu seçim proje için yaptığım araştırma tasarımıdır.

Her aday için brüt getiri, ücret, spread/kayma, funding, net getiri, işlem sayısı, maksimum drawdown, pozisyonda kalma süresi ve sermaye ihtiyacı kaydedilmeli. Eğitimde seçilen parametreler örnek dışı testte sabit kalmalı. En iyi birkaç aday aynı olay girdisiyle daha ayrıntılı simülasyona, ardından süreli paper/Demo gözlemine alınmalı. Piyasa yapıcılık ve arbitraj için L2 defter, gecikme ve bacak başarısızlığı veri gereksinimleri eklenmeli. [Freqtrade backtesting](https://www.freqtrade.io/en/stable/backtesting/), [Nautilus backtesting](https://nautilustrader.io/docs/latest/concepts/backtesting/), [HftBacktest](https://hftbacktest.readthedocs.io/en/latest/)

## GitHub kısa listesi

Uygunluk değerlendirmesi mevcut Python mimarisi, kapanacak açık, entegrasyon yükü ve bakım snapshotına dayanır. Son push tarihi deponun bakımına ilişkin tek bir sinyaldir. Tam Python 3.12 ve Windows uyumluluğu için paket kurulumu ve çalışma kabulü ayrıca gerekir. Metadata ve lisans dosyaları 15 Kasım 2026 tarihinde incelendi.

| Repo | Agentrader’a katkı | Kullanım kararı | Lisans bilgisi |
|---|---|---|---|
| [Freqtrade](https://github.com/freqtrade/freqtrade) | Pairlist, backtest, protections ve bias analizi | P1 araştırma akışı için ilk referans | GPL-3.0 |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | Olay tabanlı simülasyon, execution ve çoklu pazar modeli | P1 simülasyon prototipi için güçlü aday | LGPL-3.0 |
| [CCXT](https://github.com/ccxt/ccxt) | Normalize semboller, REST/WS, hata ve borsa yetenekleri | Genel borsa adaptörü rehberi, skill kurulumu kaldırıldı | MIT |
| [Hummingbot](https://github.com/hummingbot/hummingbot) | Grid, DCA, TWAP, arbitraj ve market making yürütücüleri | P2/P3 yürütme mimarisi referansı | Apache-2.0 |
| [Jesse](https://github.com/jesse-ai/jesse) | Python strateji geliştirme ve backtest alternatifi | P1 prototip karşılaştırmasına aday | MIT, ek bileşen kapsamı ayrıca incelenmeli |
| [HftBacktest](https://github.com/nkaz001/hftbacktest) | L2/L3, kuyruk sırası ve latency modeli | Maker stratejilerinde ayrıntılı simülasyon adayı | MIT |
| [LEAN](https://github.com/QuantConnect/Lean) | Portföy ve farklı varlık modelleri | P3 kapsam genişletmesinde referans | Apache-2.0 |
| [vectorbt](https://github.com/polakowo/vectorbt) | Çok sayıda parametre/strateji kombinasyonu | Araştırma prototipi için aday | Apache-2.0 + Commons Clause |
| [Cryptofeed](https://github.com/bmoscon/cryptofeed) | Çoklu borsa WebSocket ve order book veri toplama | P3 veri adaptörü adayı | AGPL-3.0 ve ek atıf şartı |
| [Binance Python connector](https://github.com/binance/binance-connector-python) | Resmi API şeması ve erişim örnekleri | Güncel modüler SDK kapsamını değerlendirme | MIT |
| [Optuna](https://github.com/optuna/optuna) | Parametre optimizasyonu | P2, walk-forward veri ayrımından sonra | MIT |
| [QuantStats](https://github.com/ranaroussi/quantstats) | Performans ve drawdown raporları | Net equity serisi üretildiğinde rapor katmanı | Apache-2.0 |
| [Prometheus Python client](https://github.com/prometheus/client_python) | Operasyon ölçümleri | P2 metrik katmanı | Apache-2.0 |
| [Hypothesis](https://github.com/HypothesisWorks/hypothesis) | Emir ve durum makinesi girdilerinde özellik tabanlı sınama | P2 hata kombinasyonları için aday | MPL-2.0, dosya istisnaları bulunur |
| [TimescaleDB](https://github.com/timescale/timescaledb) | Büyük tarihsel zaman serisi sorguları | Veri hacmi ölçümüne bağlı P3 aday | Apache-2.0 ve Timescale License alanları |
| [Hummingbot skills](https://github.com/hummingbot/skills) | Hazır bot/API/strateji skill’leri | Hummingbot altyapısı kurulursa yeniden değerlendirme | API metadata’sında lisans tanımı bulunamadı |

vectorbt, Cryptofeed, Hypothesis ve TimescaleDB için GitHub’ın genel lisans alanı tek başına yeterli açıklama sağlamadı. Tablodaki bilgiler asıl lisans dosyaları okunarak tamamlandı. Kod taşıma veya dağıtım kararı seçilen dosyanın koşullarıyla değerlendirilmeli. [vectorbt lisansı](https://github.com/polakowo/vectorbt/blob/master/LICENSE.md), [Cryptofeed lisansı](https://github.com/bmoscon/cryptofeed/blob/master/LICENSE), [Hypothesis lisansı](https://github.com/HypothesisWorks/hypothesis/blob/master/LICENSE.txt), [TimescaleDB lisansı](https://github.com/timescale/timescaledb/blob/main/LICENSE)

## Skill değerlendirmesi ve kaldırma

ccxt-python skill’i kullanıcı talebi doğrultusunda 15 Kasım 2026 tarihinde kaldırıldı. Skill, CCXT kütüphanesini kullanarak farklı borsalara bağlanmayı ve emir işlemlerini geliştirmeyi anlatıyor. Mevcut bot doğrudan Binance USD-M Demo adaptörünü kullanıyor. Hedefimiz bu adaptörde Binance işlemlerinin parametrelerini, hesap modlarını ve hata sonrası toparlanmasını eksiksiz desteklemek. Bu nedenle CCXT odaklı skill mevcut geliştirme hedefi için gerekli görülmedi.

Proje kapsamındaki .agents/skills/ccxt-python klasörü ve içindeki üç kurulum dosyası kaldırıldı. Geliştirme dayanağı Binance resmi API sözleşmeleri, mevcut bot kodu ve işlem bazında uçtan uca kabul ölçütleri olarak belirlendi.

## Uygulama sırası ve kabul kapıları

1. **Evren ve aday tarayıcı.** Evren sürümü, filtrelenme nedeni, veri yeterliliği, tazelik ve puan kayıtlarını ekle. Aynı kapanışta farklı sıra ile gelen adaylar aynı seçime ulaşmalı. SXP benzeri filtre/fiyat uyuşmazlığında aday engellenmeli.
2. **Backtest muhasebesi.** Nakit, pozisyon, rezervasyon, ücret ve funding defterini aynı zaman çizgisinde kur. Tek işlem örneklerini elle hesaplanan sonuçlarla eşleştir. Aynı mum stop/hedef politikasını raporla.
3. **Üç strateji ailesi.** EMA trend, Donchian kırılımı ve RSI/Bollinger dönüşünü ortak veri/plan sözleşmesine bağla. Önce birkaç temsilci coin, sonra veri yeterliliği sağlanan tüm evrene genişlet.
4. **Bias ve örnek dışı kabul.** Lookahead, warmup duyarlılığı, walk-forward ve artırılmış maliyet senaryolarını uygula. Strateji seçimini sabit kabul ölçütleriyle kaydet.
5. **Ölçek ve paper kabulü.** 10, 50, 100, 250 ve 500+ sembolde kuyruk, veri yaşı, hata oranı ve bellek ölç. Bu seviyeler önerilen deney basamaklarıdır. Gerçek sınırlar ölçümlerle belirlenmeli.
6. **Demo uçtan uca kabul.** Seçilen planlarda sembol/hesap yeteneği, kısmi dolum, stop/target ve kurtarma kanıtı topla. Strateji PnL ve borsa kabulünü sembol bazında kaydet.
7. **Gelişmiş yürütme ve ürünler.** Önce TWAP/DCA, ardından ihtiyaç doğrulanırsa funding/baz ve market making akışlarını tasarla.

## Yeniden ölçüm

Proje kökünde aşağıdaki komutlar mevcut test tanıklarını ve kaydedilmiş 528 coin verisini kullanır.

```powershell
python scripts/research/audit_bot_capabilities.py
python scripts/research/audit_market_contracts.py
python -m unittest discover -s tests
```

İkinci komutun mevcut snapshotta veri engeli nedeniyle 1 dönmesi beklenir. Yeni snapshotla tekrar ölçüm için market-universe.json ve mark-prices.json kaynak, zaman ve filtre alanları korunarak birlikte güncellenmeli. Sonuçların kaynak SHA-256 değerleri raporlarda saklanır. Sembol başına gerçek yürütme kabulü bu iki denetimin sonraki aşamasıdır.
