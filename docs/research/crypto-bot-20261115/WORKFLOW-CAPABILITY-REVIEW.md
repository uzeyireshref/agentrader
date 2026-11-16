# Kullanıcı talimatından sonuca bot yeteneği denetimi

15 Kasım 2026. Araştırma 1–5 turu. Kod hashleri ve her REST yolu için referanslar `operation-support-audit.json` içinde. Kaynakta sabit adres bulunması, ilgili kullanıcı talimatını uçtan uca gerçekleştirme kanıtı sayılmadı.

## Normal giriş zincirleri

- Plan: `cli/plan_cli.py` create → PlanService → validate_plan/validate_v2 → onay/etkinleştirme → run_plan/account_runtime → SINGLE/GRID/NEUTRAL yürütücü → journal/rezervasyon → DemoExchange → sorgu/uzlaştırma.
- Ayar: `cli/settings_cli.py` prepare → AccountCommands → apply → tek gönderim → reconcile. İzole teminat ayrı IsolatedMarginCommands zinciridir.
- Amend: `cli/order_cli.py` amend/batch-amend prepare → OrderAmendments → apply → orderAmendment geçmişiyle doğrulama → kayıt.
- Grafik: chart_bot komutları/API onayı mevcut plan ve yönetim servislerine bağlanır. Genel amaçlı bütün ürünlere açık emir giriş servisi değildir.
- Akış: user_stream → normalizasyon → kalıcı recovery barrier → REST uzlaştırma → sahiplik ve risk kontrolü.

## Talimat matrisi

| Kimlik | Kullanıcının istediği işlem | Mevcut durum | Kanıt ve sınır |
|---|---|---|---|
| W01 | USD-M market ile long/short aç | Kısmi ürün desteği | V2 SINGLE, planlı stop/hedef ve demo koşullarıyla mevcut. Bağımsız genel emir komutu değil |
| W02 | USD-M limit ile aç | Kısmi | v2_preflight GTC üretir |
| W03 | IOC/FOK/GTX/GTD seçerek emir ver | Normal giriş açığı | order_rules kabul eder, plan entry şeması bu seçimi sunmaz |
| W04 | priceMatch ile emir ver | Normal giriş açığı | Yardımcı validator kabulü var, standart plan alanı yok |
| W05 | STP seçerek emir ver | Normal giriş açığı | Validator enumu var, plan alanı yok |
| W06 | ACK/RESULT yanıt seç | Parametre açığı | newOrderRespType yerel validator tarafından reddediliyor |
| W07 | Koşullu stop/TP oluştur | Kısmi | Plan koruması ve algo yolu mevcut, her türün bağımsız kullanıcı komutu yok |
| W08 | Borsa trailing stop kullan | Kısmi | Validator .1–5 kabul ediyor. Plan native_stop botun stop yenilemesi, doğrudan aynı emir değil |
| W09 | Callback 7.5/10/20 kullan | Doğrulanmış validator açığı | 527 sembolde her değer reddedildi |
| W10 | Hedge long/short ayrı yönet | Kısmi | V2/neutral modelleri var, kapsam ve sahiplik koşulları sürer |
| W11 | Mevcut pozisyonu keyfi artır | Genel talimat açığı | SINGLE scale-in reddi, GRID artışı plan döngüsüne bağlı |
| W12 | Pozisyonun yönünü çevir | Açık | allow_reverse reddediliyor |
| W13 | Pozisyonu kısmen azalt/tam kapat | Kısmi | Mevcut oturum hedef/stop/grid durdurma akışları var, keyfi dış pozisyon komutu kanıtı yok |
| W14 | Yabancı/manuel pozisyonu devral | Açık kapsam | Sahiplik korumaları var. Keyfi devralma desteği sayılmadı |
| W15 | Seçili bot emrini iptal et | Kısmi | Sahiplik ve kalıcı sonuç sorgusuyla mevcut akışlar |
| W16 | Bütün normal/algo emirleri iptal et | Route açığı | allOpenOrders/algoOpenOrders DELETE genel yolları izin listesinde yok |
| W17 | Süre dolunca otomatik hepsini iptal et | Açık | countdownCancelAll adaptör desteği yok |
| W18 | Fiyat/miktar değiştir | Kısmi | orders amend komutları var, yetkili mevcut oturum ve bütçe koşullarıyla |
| W19 | Toplu emir oluştur | Kısmi | Native batch LIMIT/GTC ve mevcut grid akışına bağlı |
| W20 | Toplu amend/iptal et | Kısmi | Üye bazında teyit ve tekrar göndermeme mevcut |
| W21 | Kaldıracı değiştir | Kısmi | settings mevcut, kodda sabit 125 sınırı |
| W22 | Cross/isolated değiştir | Koşullu demo desteği | settings ve açık pozisyon/emir koşulları |
| W23 | Hedge/multi-assets/fee-burn değiştir | Koşullu demo desteği | settings mevcut. UM/CM ortak etki ayrıca ürün kapsamına alınmalı |
| W24 | İzole teminat ekle/çek | Koşullu demo desteği | margin prepare/apply/reconcile mevcut |
| W25 | Geçmiş/gelir/dolum uzlaştır | Kısmi | history ve history_reconciliation mevcut, bütün tarihsel endpointler yok |
| W26 | Her USD-M sembolünü kullan | Açık kapsam | USDT perpetual preflight sınırı. USDC/teslimli/TradFi kapsamı otomatik desteklenmiyor |
| W27 | Spot emir/SOR ver | Ürün açığı | Normal plan SPOT reddediyor |
| W28 | Spot OCO/OTO/OTOCO/OPO/OPOCO kullan | Ürün ve süreç açığı | Liste kimliği/alt emir/muhasebe adaptörü yok |
| W29 | Spot cancel-replace/keep-priority amend | Ürün açığı | USD-M amend aynı sözleşme değil |
| W30 | Spot iceberg/pegged/trailing emir | Ürün açığı | Spot alan/birim/filtre modeli yok |
| W31 | Margin borrow/repay/auto-borrow | Ürün açığı | Ürün giriş/adaptörü ve borç muhasebesi yok |
| W32 | Cross/isolated Margin yönet | Ürün açığı | USD-M isolated margin işlevi Margin ürünü desteği değil |
| W33 | COIN-M perpetual/teslimli işle | Ürün açığı | Inverse miktar/PnL ve dapi adaptörü yok |
| W34 | Options al/sat/kullanım sonucunu izle | Ürün açığı | Vade/prim/exercise adaptörü yok |
| W35 | Options MMP/block trade kullan | Ürün açığı | Yetki ve ayrı süreç desteği yok |
| W36 | Portfolio Margin/Pro kullan | Ürün açığı | Yerel portfolio risk sınıfı borsanın PM ürünü değil |
| W37 | Convert teklif/limit dönüşüm yap | Ürün açığı | Convert normal komut ve sonuç takibi yok |
| W38 | Cüzdanlar arası transfer yap | Ürün açığı | Transfer niyet/geçmiş/bakiye süreci yok |
| W39 | Yatırma/çekme takibi ve talimatı | Ürün açığı | Ağ, adres, durum ve çekim süreci yok |
| W40 | Dust ve cüzdan ücret/izin yönet | Ürün açığı | Wallet adaptörü yok |
| W41 | Alt hesap transfer/pozisyon taşı | Ürün açığı | Master/sub yetki ve iki hesap uzlaştırması yok |
| W42 | API key izin/IP/ürün etkinleştirme yönet | Ürün açığı | Sub Account yönetim yolları yok |
| W43 | İşlem komutunu WS API ile gönder | Arabirim açığı | Mevcut kullanıcı olay akışı WS emir gönderme API'si değil |

## Sayısal sonuçların doğru yorumu

555 başlangıç işleminde 39 izinli adaptör yolu, 1 başka istemci referansı ve 515 ürün/yol açığı bulundu. 515 sayısı 460 USD-M dışı kayıt ile 55 USD-M yol açığından oluşur. Bu sayılar kullanıcı talimatı başarı oranı değildir. Aynı URL'deki farklı HTTP yöntemleri ayrı işlemdir.

Normal plan şemasına 3720 aktif sembol örneği verildi. 541 USD-M sembolü şema aşamasını geçti, diğer 3179 örnek reddedildi. Şemadan geçmek preflight veya borsa kabulü değildir. USD-M preflight yalnız USDT PERPETUAL kabul eder. Hesap, izin, fiyat, teminat, risk, guardian ve sahiplik sonraki kapılardır.

1262 mevcut test geçti. Bu sonuç mevcut davranışın regresyon kanıtıdır. Yukarıdaki eksik ürünlerin desteklendiği anlamına gelmez. Eski 128 senaryo kataloğunda 64 tanık geçti, 64 satırda bağlı test bulunmuyor. Test metodu indeksinde 1226 statik metot bulunması ile unittest'in 1262 vaka çalıştırması farklı sayım yöntemleridir.

## Kanıt dosyaları

- `operation-support-audit.json`: bütün başlangıç satırları, route izinleri ve kaynak satırları.
- `reports/crypto-bot-research-20261115/existing-test-evidence-index.json`: test metodu/kaynak indeksi.
- `reports/crypto-bot-research-20261115/product-symbol-surface-audit.json`: ürün ve sembol şeması deneyleri.
- `reports/crypto-bot-research-20261115/capability-audit.json`: senaryo-test eşlemesi.
- `reports/crypto-bot-research-20261115/exchange-operation-audit.json`: USD-M route ve parametre deneyleri.
