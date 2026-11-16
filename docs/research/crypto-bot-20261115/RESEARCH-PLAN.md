# Binance işlem yetenekleri kapsamlı araştırma planı

Güncel değerlendirme: [5–8 geniş turu ve kapanış denetimi](RESEARCH-CLOSURE-5-8.md). Ortam matrisi, 20 repo/skill kararı ve 34 bulgu ailesi teslim edildi. Başlangıç 555 işleme 3 resmi CM ek yol kaydedildi. Tam alan/koşul sözleşmesi açık kalan kayıtlar nedeniyle aşağıdaki bütün kapanış kutuları tamamlandı olarak işaretlenmedi. Geliştirme uygulaması başlamadı.

15 Kasım 2026. Durum PLAN HAZIR, ARAŞTIRMA DEVAM EDİYOR. Kullanıcı tarafından belirlenen sıra önce bütün araştırmanın tamamlanması, ardından bulgulardan geliştirme planının çıkarılmasıdır.

Güncel teslim: [1–5 geniş araştırma turu](BROAD-RESEARCH-1-5.md). 555 başlangıç REST işlemi için sürümlü SDK sözleşmesi ve bot durumu, 83 WS API komutu, ürün kararları, hata/toparlanma ve geniş sembol ölçümleri teslim edildi. Bu tur kullanıcıya sunulan beş başlığı kapsar. Aşağıdaki R0–R11 numaralarıyla bire bir aynı sıra değildir. Belirli kaynak çelişkileri ve hesap kabul sınırları açık kayıtlarında tutuluyor. R9 araç seçimi ve nihai araştırma kapanışı henüz yapılmadı.

## 1. Amaç ve nihai teslim

Botun kullanıcı tarafından istenen borsa işlemlerini doğru ürün, hesap, sembol, emir ve miktar kapsamında gerçekleştirebilmesi için gereken yetenekleri belirlemek. Araştırma, resmi işlem sözleşmelerini mevcut uygulama ve mevcut kanıtlarla eşleştirir. Hedeflenen sonuç her talimatın koşullarının, destek düzeyinin, yazılım açığının ve kabul yönteminin açıklanmasıdır.

Araştırma sonunda ürünler arası yetenek matrisi, kaynaklı işlem sözleşmeleri, kullanıcı talimatları kataloğu, parametre kombinasyonları, mevcut bot karşılaştırması, hata ve toparlanma senaryoları, ortam farkları ve açık sorular teslim edilir. Geliştirme planı bu teslimlerden türetilir. Paketlerin uygulama sırası, bağımlılıkları, normal giriş noktaları ve kabul testleri ancak bulgular birleştirildikten sonra kesinleştirilir.

Strateji seçimi ve getiri optimizasyonu kullanıcı tarafından sonraki aşamada belirlenecek. Araştırmada pozisyon artırma, yön değiştirme, dilimleme veya bağlı emir gibi yürütme ihtiyaçları işlem davranışı olarak incelenir. Bunlara sinyal veya yatırım kararı atanmaz.

## 2. Araştırma çalışma biçimi

- Resmi belgeleri incele, mevcut kodu oku, mevcut test ve teslim kayıtlarını değerlendir.
- Gereken davranış ölçümlerini izole kayıtlarla ve hesap üzerinde değişiklik oluşturmayan yerel deneylerle yap.
- Araştırma araçları ve belgeleri kanıt toplamak için eklenebilir. Üretim yetenek değişiklikleri geliştirme aşamasında yapılır.
- Borsadaki okuma gözlemlerinde kaynak, ortam, gözlem zamanı ve kapsam kaydedilir.
- Yeni emir, hesap ayarı, borçlanma, transfer veya başka finansal işlem kabulü gerektiğinde somut senaryo ve gerekli yetki ayrıca belirlenir. Genel araştırma talebi bu işlemlerin yürütme yetkisi olarak yorumlanmaz.
- Mevcut çalışma ağacındaki kullanıcı değişiklikleri kanıtın kaynak sürümüyle birlikte dikkate alınır.
- Hazır repo veya skill seçimi teknik katkı üzerinden değerlendirilir. Kurulum ve mimari bağımlılık kararı araştırma bulgularıyla gerekçelendirilir.

## 3. Ürün kapsamı ve araştırma sırası

| Paket | Kapsam | Tamamlandığında elde edilecek çıktı |
|---|---|---|
| R0 | Başlangıç kaydı ve kaynak haritası | Güncel kapsam, kaynak sürümleri, mevcut bot girişleri, kanıt envanteri |
| R1 | USD-M Futures | Ayrıntılı işlem, hesap, parametre, sorgu ve toparlanma karşılaştırması |
| R2 | Spot | Emirler, emir listeleri, bakiye, dolum, filtre ve iptal/değiştirme karşılaştırması |
| R3 | Margin | Cross/isolated, borç, geri ödeme, faiz, teminat ve emir ilişkileri |
| R4 | COIN-M Futures | Kontrat miktarı, coin teminatı, emirler, pozisyon ve uzlaşma |
| R5 | Options | Opsiyon emirleri, vade, pozisyon, prim, kullanım/uzlaşma ve hesap işlemleri |
| R6 | Cüzdan, Convert, Portfolio Margin ve hesap hareketleri | Transfer ve dönüşüm yaşam döngüleri, bakiye ve geçmiş uzlaştırması |
| R7 | Ürünler arası ortak altyapı | Kimlik, limit, saat, WS, tutarlılık, tekrar güvenliği ve eşzamanlılık analizi |
| R8 | Sembol çeşitliliği ve senaryo kapsamı | Temsilci sınıflar, sınır örnekleri, kombinasyon kapsamı ve ölçüm sonuçları |
| R9 | GitHub ve geliştirme araçları | Somut açığa bağlı repo/araç/skill uygunluk değerlendirmesi |
| R10 | Birleştirme ve araştırma kapanışı | Açıklar, belirsizlikler, kapsam hesabı ve kaynak güncellik kontrolü |
| R11 | Araştırmaya dayalı geliştirme planı | Bulgulara izlenebilir geliştirme paketleri ve kabul planı |

R1–R6 ürün incelemesi sıralıdır. R7 ve R8 ölçütleri her ürün paketinde uygulanır, ürünler tamamlandıktan sonra ortak sonuçları birleştirilir. R9 adayları araştırma boyunca toplanır ve R10 öncesinde değerlendirilir. R11, R10 kabulünden sonra hazırlanır.

Binance dışındaki borsalar bu planın mevcut envanter kapsamına eklenmez. Başka bir borsanın örneği teknik sorun çözümü için kullanılırsa Binance kabul kanıtıyla karıştırılmadan referans olarak kaydedilir.

## 4. Kaynak araştırması

### 4.1 Birincil kaynaklar

Her ürün için resmi REST ve WebSocket API belgeleri, kullanıcı veri akışları, genel bilgiler, filtreler, hata kodları, işlem kuralları, changelog, ortam açıklamaları ve resmi destek sayfaları taranır. Ürünün API ile desteklenen işlemleri ile arayüzde görülen işlemler eşleştirilir. Arayüzdeki bir davranışın API karşılığı bulunamazsa belirsizlik kaydı açılır.

Başlangıç kaynakları aşağıdadır. Her ürün paketinde güncel adres ve içerik doğrulanır. Yönlendirme, boş sayfa ve kaldırılan belge kontrol edilir.

| Kaynak | Araştırmadaki işlevi |
|---|---|
| [Binance Developer Docs](https://developers.binance.com/) | Ürün, işlem ve altyapı kaynak haritası |
| [USD-M REST trade](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade) | Mevcut botun işlem sözleşmelerinin başlangıç kaynağı |
| [Spot resmi belgeleri](https://github.com/binance/binance-spot-api-docs) | Sürümlenebilir API, filtre, emir listesi ve olay açıklamaları |
| [Resmi Python connector](https://github.com/binance/binance-connector-python) | Ürün modelleri, parametreler ve örnek uygulama karşılaştırması |
| [Resmi Postman koleksiyonları](https://github.com/binance/binance-api-postman) | İstek örnekleri ve endpoint karşılaştırması |
| [Resmi Binance CLI](https://github.com/binance/binance-cli) | Kullanıcı komutu ve argüman kapsamı karşılaştırması |
| [Resmi Skills Hub](https://github.com/binance/binance-skills-hub) | Resmi ürün referanslarının geliştirme iş akışına uygunluğu |

### 4.2 İkincil araştırma ve uyuşmazlık çözümü

Resmi depoların issue, PR, release ve testleri taranır. Benzer botların adaptör ve durum yönetimi kodları incelenir. Bir hata bildirimi, raporlandığı sürüm ve doğrulama durumuyla kaydedilir. Topluluk anlatımı tek başına işlem sözleşmesi kabulü sağlamaz.

Belge, SDK ve gözlem uyuşmazlığında üç kanıt da saklanır. Tarih, API sürümü, ortam ve ürün karşılaştırılır. Çözülemeyen konu için hangi davranışın belirsiz olduğu, olası uygulama etkisi ve çözmek için gereken deney tanımlanır. Arama sonucundaki kısa özet yerine ilgili kaynak içeriği okunur.

### 4.3 Kaynak kayıt alanları

Kaynak kimliği, URL, başlık, yayın/güncelleme bilgisi mevcutsa bu tarihler, erişim zamanı, ürün, API sürümü, repo commit’i veya release’i, desteklediği işlem kimlikleri, içerik özeti/hash’i ve güncellik durumu kaydedilir. Belge kopyaları gerektiği kadar saklanır ve kaynak atfı korunur.

## 5. Her işlem için doldurulacak sözleşme

| Alan | Kaydedilecek ayrıntı |
|---|---|
| Kimlik | Kalıcı işlem kimliği, ürün ve işlem ailesi |
| Kullanıcı amacı | Talimatın doğal dil örneği ve hedef sonucu |
| Kapsam | Hesap, alt hesap, sembol, pozisyon tarafı, oturum ve emir kümesi |
| Arabirim | REST yöntemi/yolu, varsa WS yöntemi ve sürüm |
| Yetki | İmzalama, izin, hesap türü ve ürün uygunluğu |
| Önkoşullar | Bakiye, açık emir/pozisyon, mod, kontrat durumu ve işlem zamanı |
| Parametreler | Tür, birim, hassasiyet, zorunluluk, varsayılan, alt/üst sınır |
| Kombinasyonlar | Birlikte zorunlu, birlikte yasak, moda/ürüne bağlı alanlar |
| Filtreler | Fiyat, miktar, nominal, açık emir sayısı ve pozisyon limitleri |
| Kimlikler | Kullanıcı komutu, client ID, exchange ID ve algo/child ilişkileri |
| Sonuç | ACK, ara durum, terminal durum ve beklenen değişiklik |
| Olaylar | İlgili WS olayları ve REST teyit yolu |
| Hatalar | Ret, geçici hata, bilinmeyen sonuç ve yeniden sorgu koşulları |
| Tekrar | Tekilleştirme, tekrar gönderme güvenliği ve uzlaştırma |
| Ortam | Demo/Testnet/gerçek ortam destek bilgisi ve doğrulama tarihi |
| Bot karşılığı | Normal giriş, doğrulayıcı, yürütücü, kayıt ve toparlanma kodu |
| Kanıt | Kaynak, kod satırı/hash, test, gözlem ve tarih |
| Açık | Eksik veya kısmi davranış, etkisi ve kabul senaryosu |

Eski ve yeni API sürümleri ayrı adreslerle kaydedilir. Aynı kullanıcı amacını karşılayan alternatifler birbirine bağlanır. Endpoint sayısı, kullanıcı talimatı sayısı ve parametre senaryosu sayısı ayrı hesaplanır.

## 6. R0 başlangıç kaydı

- Mevcut 95 USD-M işlem kataloğunu, önceki 39 adaptör yolu/1 diğer istemci/55 adres bulunamadı sonucunu başlangıç kanıtı olarak al.
- Bu sayıları güncel belgeyle yeniden karşılaştır. Kaynakta adres bulunmasının normal komut kabulünü tamamlamadığını kayıt şemasında görünür tut.
- Bot CLI, HTTP API, uygulama servisleri, plan şemaları, doğrudan adaptörler ve kalıcı kayıtları envanterle.
- Üretim girişleri ile deney/yardımcı script girişlerinin çağırdığı yolları belirle.
- Test adlarını, gerçek davranış iddialarını, fixture türünü ve son çalışma kaydını eşleştir.
- Önceki araştırmadan strateji önerilerini bu planın yetenek kararlarına otomatik taşımadan tarihsel bağlam olarak tut.

Kabul, mevcut envanter dosyalarının kaynakları, kapsamları ve eksik kanıtlarının açık olmasıdır.

## 7. R1 USD-M Futures ayrıntıları

### Emir oluşturma ve emir davranışı

Market ve limit açılış/azaltma, BUY/SELL, long/short, one-way/hedge, positionSide, reduceOnly, closePosition, fiyat/miktar, GTC/IOC/FOK/GTX/GTD ve belgede bulunan diğer süre türleri incelenir. priceMatch, self-trade prevention, yanıt türü, istemci kimliği ve fiyat korumasının geçerli koşulları çıkarılır. Hesap veya programa özgü türler uygunluk koşullarıyla kaydedilir.

STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET ve TRAILING_STOP_MARKET için normal/algo endpoint ayrımı, trigger/activation alanları, callback sınırı, mark/contract tetikleyici, triggerProtect, child emir ve terminal durumlar incelenir.

Tek/batch oluşturma, fiyat/miktar değiştirme, tek/seçili/tüm normal/tüm algo iptali, zamanlayıcılı iptal ve emir sorguları ayrı kullanıcı işlemleri olarak çıkarılır. Batch içinde kısmi başarı, sıra, limitler ve her alt emrin uzlaştırılması tanımlanır.

### Pozisyon ve hesap

Açılış, artırma, kısmi azaltma, tam kapatma, açık talimatla yön değiştirme ve hedge bacaklarının ayrı yönetimi incelenir. Aynı sembolde birden fazla yerel oturumun borsadaki tek pozisyona etkisi ve manuel işlemlerle sahiplik ilişkisi çıkarılır.

Kaldıraç, nominal/bakım marjı basamakları, cross/isolated, isolated teminat ekleme/azaltma, one-way/hedge, multi-assets, komisyon tercihi, bakiye, kullanılabilir teminat ve hesap yapılandırması incelenir. Ayar değişikliğinin açık emir/pozisyon varken koşulları kaydedilir.

### Sorgular ve olaylar

Normal/algo emir geçmişi, açık emirler, dolumlar, gelir, funding/komisyon, zorunlu işlemler, ADL, teminat ve amend geçmişi, indirme görevleri, saklama ve sayfalama sınırları incelenir. Kullanıcı akışı kurulumu, canlı tutma, rotasyon ve olay türleri eşleştirilir.

Mum, mark/index/contract fiyatı, funding bilgisi, defter, işlemler, kontrat durumu ve istatistikler için bot talimatını yürütmeye gereken veri ile genel veri sorgu yetenekleri kaydedilir.

Önceki somut bulgular yeniden kontrol edilir. GTC’ye sabitlenmiş limit planı, callback desteği, newOrderRespType, native trailing akışı, SINGLE artırma/reverse ve countdown iptal bu pakette kanıtlarıyla sonuçlandırılır.

## 8. R2 Spot ayrıntıları

- Market/limit ve belgelenmiş koşullu emir türleri, maker davranışı, miktar/quote miktarı, fiyat ve nominal filtreleri.
- Emir süreleri, iceberg, trailing, pegged ve STP gibi özelliklerin güncel ürün ve sembol koşulları.
- OCO/OTO/OTOCO ve belgelenmiş diğer emir listelerinde working/pending bacak, tetiklenme, aktivasyon ve iptal ilişkileri.
- Cancel-replace ve amend işlemlerinde eski emrin durumu, yeni emrin reddi, kısmi sonuç ve sıra önceliği.
- Serbest/kilitli bakiye, komisyon varlığı, dolum sonrası envanter ve küçük artıklar.
- Açık/terminal emir, emir listesi, işlem geçmişi ve kullanıcı veri olayları.

Kabul, Spot talimatlarıyla mevcut USD-M modelinin hangi anlamlarda uyumlu/eksik olduğunun açık sözleşme karşılaştırmasıdır.

## 9. R3 Margin ayrıntıları

- Cross ve isolated hesap kapsamı, sembol ve varlık uygunluğu.
- Borç alma, geri ödeme, maksimum borç, mevcut borç stoku, faiz, borç/geri ödeme geçmişi.
- Normal, otomatik borçlanma ve otomatik geri ödeme seçeneklerinin emir davranışıyla ilişkisi.
- Hesaplar arası teminat hareketi, transfer edilebilir tutar, risk oranları ve tasfiye koşulları.
- Emir, borç ve transfer adımlarından biri başarısız olduğunda gerçek borç/bakiye durumunun bulunması.
- Aynı varlıkta eşzamanlı komutlar ve tekrarlanan borç/geri ödeme talimatı.

Kabul, finansal yan etkilerin ve her adımın teyit yolunun tanımlanmasıdır.

## 10. R4 COIN-M Futures ayrıntıları

Kontrat adedi, contractSize, coin teminatı, ters fiyat ve PnL/komisyon birimleri belgelenir. Perpetual ve teslimli kontratların vade, settlement ve işlem durumu incelenir. Emir, hedge, azaltma, teminat, kaldıraç, geçmiş ve olay akışları USD-M ile alan alan karşılaştırılır. Aynı isimli parametrelerin farklı birimleri vurgulanır. USD-M örneğini COIN-M’e taşımak için gereken dönüşümler ve mevcut kodun açık reddettiği girdiler bulunur.

## 11. R5 Options ayrıntıları

Güncel API ürün ailesi ve ortam desteği önce doğrulanır. Sembol yapısı, underlying, call/put, kullanım fiyatı, vade, miktar çarpanı, prim ve settlement birimleri çıkarılır. Desteklenen alış/satış, açma/kapama, emir süreleri, batch/amend/cancel, pozisyon ve hesap sorguları envanterlenir. Kullanım, vade sonu, otomatik uzlaşma, teminat ve hak/yükümlülük olayları incelenir. Hesap uygunluğu ve ürün kısıtları kaynaklı kaydedilir. Greeks gibi sunulan risk verileri sorgu yeteneği olarak incelenir.

## 12. R6 cüzdan, Convert ve hesap hareketleri

Ürün hesapları arası ve desteklenen alt hesap transferleri, yön/tür alanları, transfer edilebilir bakiye, komisyon ve geçmiş çıkarılır. Convert teklif alma, teklif süresi, kabul, sonuç ve durum sorgulama incelenir. Transfer ve dönüşümde ağ kesilmesinden sonra tekrar işlem oluşturma riski tanımlanır.

Yatırma/çekme ile ilgili resmi API yetenekleri kapsam haritasında görünür tutulur. Ağ, adres/tag, ücret, limit ve durum sorguları araştırılır. Bu işlemler için kaynak incelemesi ve işlem tasarımı yapılır, gerçek hareket kabulü ayrıca yetkilendirilecek deney olarak kaydedilir. Earn, staking, kredi, copy trading ve diğer ürünlerle ilgili yeni gereksinim bulunursa kapsam kararına eklenir, henüz desteklenen işlem olarak gösterilmez.

### Portfolio Margin ve birleşik hesap modeli

Classic/Pro veya belgelerde bulunan güncel hesap modelleri ayrı incelenir. Hesap uygunluğu, teminat iskontoları, birleşik bakiye, margin gereksinimleri, desteklenen ürünler, emir/pozisyon sorguları ve tasfiye olayları çıkarılır. Mevcut USD-M portföy risk hesabıyla anlam farkları kaydedilir. Normal hesaptaki endpoint adlarının aynı davranışı sağladığı varsayılmaz.

## 13. R7 ortak altyapı ve hata araştırması

| Alan | İncelenecek sorular |
|---|---|
| İmzalama ve yetki | Anahtar türleri, izinler, IP koşulları, hesap/ürün erişimi nasıl doğrulanıyor? |
| Saat | Timestamp, recvWindow, ms/s hassasiyeti ve saat kayması nasıl ele alınıyor? |
| Limitler | IP, hesap, emir ve WS limitleri, Retry-After ve kalıcı cooldown nasıl uygulanmalı? |
| Ağ hatası | Gönderilmedi, kesin ret ve sonucu bilinmeyen işlem nasıl ayrılıyor? |
| Tekilleştirme | Komut ve client ID ömrü, tekrar kullanılma koşulu ve tekrar talimat anlamı nedir? |
| WS | Snapshot/delta, sıra, kopya, geç olay, sessiz kopma, reconnect ve REST uzlaştırma nasıl yapılır? |
| Kalıcılık | Niyet, gönderim, ACK, dolum ve terminal durum arasında çökme olursa hangi kayıt kalır? |
| Eşzamanlılık | İptal sırasında dolum, amend sırasında dolum, iki yönetici ve ortak bütçe nasıl uzlaştırılır? |
| Sahiplik | Manuel emir, başka oturum ve başka hesap nasıl tanınır? |
| Sürümler | Eski kayıt, şema değişikliği, API kaldırılması ve SDK farkları nasıl ele alınır? |
| Muhasebe | Brüt/net miktar, ücret varlığı, funding, faiz ve transfer kayıtları nasıl eşleşir? |
| Gözlenebilirlik | Kullanıcıya işlem durumunu kanıtlayan hangi özet ve denetim kaydı sunulur? |

Borsa tarafından reddedilmesi gereken talimat ile botta eksik destek yüzünden yürütülemeyen talimatın neden kodları ve kullanıcı açıklamaları ayrı kaydedilir. Geçici erişim engeli, ürün uygunluğu ve test ortamı eksikliği geliştirme açığından ayırt edilir.

## 14. R8 senaryo ve coin çeşitliliği

Senaryo seçimi ürün × işlem ailesi × yön × hesap modu × emir türü × süre × dolum durumu × hata noktası × sembol filtresi boyutlarını kapsar. Geçerli kombinasyonların tümü listelenir. Anlamsız birleşimler gerekçesiyle elenir. Kritik sınırlar ve finansal yan etkiler ayrıntılı ele alınır, büyük kombinasyon alanları için ikili/üçlü etkileşim kapsamı gerekçelendirilir.

Temsilci sınıflar yüksek/düşük fiyat, küçük/büyük tick, küçük/büyük lot, farklı minimum nominal, farklı maksimum miktar, farklı kontrat çarpanı, yeni/delist durumundaki sembol ve ürüne özgü özellik desteği üzerinden seçilir. Tarihli sembol snapshotı kullanılır. Sabit 528 sayısı kapsam sınırı kabul edilmez. Tüm uygun semboller için otomatik yerel sözleşme taraması ve temsilci sınıflar için derin yaşam döngüsü senaryoları planlanır.

| Senaryo grubu | Örnek |
|---|---|
| Normal başarı | Geçerli talimat, doğru parametre, beklenen sonuç |
| Sınır | Tick/lot sınırı, minimum nominal, vade ve callback alt/üst sınırı |
| Geçersiz birleşim | Hedge ile uygunsuz reduceOnly, close-all ile miktar çakışması |
| Kısmi dolum | Kalan miktarı iptal/değiştirme, korumayı gerçek miktara uyarlama |
| Yanıt kaybı | Borsa kabul etti fakat ACK gelmedi, sorguyla sonuca ulaşma |
| Çökme | Rezervasyon/gönderim/dolum adımları arasında restart |
| Yarış | İptal sırasında dolum, paralel talimat ve manuel değişiklik |
| Toplu işlem | Bazı alt emirler kabul, bazıları ret veya belirsiz |
| Veri sorunu | Eski fiyat, filtre değişimi, boşluk veya farklı kaynak |
| Ortam farkı | Belgede var fakat Demo’da erişim doğrulanamıyor |

Her senaryo başlangıç durumu, talimat, girdiler, beklenen borsa etkisi, beklenen yerel kayıt, hata enjeksiyon noktası, teyit sorgusu ve başarı ölçütü içerir. Geçen yerel doğrulama, geçen izole yürütme ve borsada kabul edilmiş işlem ayrı kanıt alanlarında saklanır.

## 15. Mevcut botu ölçme yöntemi

Talimatın CLI/HTTP girişinden plan, doğrulama, risk, rezervasyon, gönderim, journal, uzlaştırma ve kullanıcı sonucuna kadar çağrı yolu çıkarılır. Doğrudan yardımcı fonksiyonun desteklediği ama normal komutun sunmadığı seçenek kısmi destek olarak kaydedilir. Deney script’iyle yapılan işlem için normal giriş desteği ayrıca gösterilir.

| Boyut | Kullanılacak değerlendirmeler |
|---|---|
| Resmi sözleşme | Belgeli, kaldırılmış, uygunluğa bağlı, çelişkili |
| Üretim desteği | Tam, kısmi, bulunamadı, başka yolla eşdeğer |
| Normal komut | Kullanılabilir, sınırlı, iç fonksiyonda, bulunamadı |
| Yerel kanıt | Geçti, başarısız, çalıştırılmadı, geçerliliği eskidi |
| Borsa kanıtı | Tarihli kabul, ret, erişim engeli, gözlenmedi |
| Toparlanma | Kanıtlı, kısmi, bilinmiyor |

Tek yüzdeyle bütün yeteneklerin hazır olduğu sonucu verilmez. Kanıtlar kaynak hash’i, test kimliği, fixture/ortam ve tarih taşır. İlgili kaynak değiştiğinde kanıtın geçerliliği yeniden değerlendirilir. Yeni ölçüm yalnız gerekli belirsizliği çözmek için yapılır, mevcut testin adı başarı varsayımı olarak kullanılmaz.

## 16. R9 GitHub, repo ve skill incelemesi

Her aday somut işlem açığına bağlanır. Resmi sağlayıcı, hedef ürün/ortam kapsamı, testleri, API güncelliği, Windows/Python uyumu, bağımlılık yükü, lisans ve bakım durumu incelenir. Hazır botlarda özellikle emir durumları, batch sonuçları, hedge/teminat ve recovery uygulamaları araştırılır.

Çıktıda repo, commit/release, kapanacak açık, incelenen dosya, yeniden kullanım biçimi, entegrasyon maliyeti ve karar bulunur. Skill adayında SKILL.md ve yardımcı script’ler okunur. Kurulumun mevcut bot mimarisine katkısı açıkça gösterilir. Önceden kaldırılan ccxt-python tekrar kurulu kabul edilmez. Bu paketin tamamlanması kurulum sayısına bağlı değildir.

## 17. Araştırma teslim dosyaları

Dosyalar paket ilerledikçe oluşturulur. Aşağıdaki liste hedef teslim yapısıdır.

| Teslim | İçerik |
|---|---|
| Kaynak kayıtları | Kaynak sürümü, erişim tarihi, ilgili işlem ve uyuşmazlıklar |
| Ürün işlem katalogları | İşlemler, parametreler, koşullar ve ürün kapsamı |
| Kullanıcı talimat kataloğu | Doğal dil talimatları, hedef nesneler ve beklenen sonuç |
| Yetenek matrisi | Talimat–normal giriş–kod–test–borsa kanıtı eşlemesi |
| Senaryo kataloğu | Başarı, sınır, ret, yarış, kesinti ve restart örnekleri |
| Ortam karşılaştırması | Demo/Testnet/gerçek ortam desteği ve erişim belirsizlikleri |
| Eksik listesi | Somut açık, etki, kaynak, gereken değişiklik ve kabul |
| Belirsizlik kaydı | Çelişki, çözüm yöntemi, mevcut sonuç ve etkisi |
| Repo değerlendirmesi | Somut ihtiyaca bağlı adaylar ve karar gerekçeleri |
| Araştırma sonuç raporu | Kapsam hesabı, doğrulanmış bulgular ve kalan deneyler |
| Geliştirme planı | Sonuçlara bağlı paketler ve kabul kapıları |

Mevcut [kapsam düzeltmesi](EXCHANGE-CAPABILITY-SCOPE.md), [95 işlem envanteri](EXCHANGE-OPERATIONS.md), [önceki senaryolar](SCENARIOS.md) ve [kanıt raporu](../../../reports/crypto-bot-research-20261115/exchange-operation-audit.json) başlangıç girdileridir. Her biri yeni ürün kapsamı ve yeni ölçümlerle güncellenir veya sürümlü teslimlere bağlanır.

## 18. Paket kapanış ve araştırma tamamlanma ölçütleri

Bir ürün paketi için resmi kaynak gezinmesindeki işlem grupları envanterle karşılaştırılır. Her işlem kayıt altındadır, eski/eşdeğer/uygunluğa bağlı olanlar gerekçelidir. Parametre ve kombinasyon tablosu, kullanıcı talimatları, mevcut bot eşlemesi ve kabul senaryoları tamamlanmıştır. Kritik uyuşmazlıkların sonucu veya belirli çözüm deneyi kayıtlıdır.

R10 kabul listesi aşağıdadır.

- [ ] R0–R6 kapsamındaki bütün ürün ve işlem gruplarının kaynak haritası kapatıldı.
- [ ] Her işlem için parametre, önkoşul, yanıt ve hata sözleşmesi tamamlandı.
- [ ] Her kullanıcı talimatı mevcut bot desteği veya somut eksikle eşleşti.
- [ ] Kısmi destek ve normal komuttan erişilemeyen özellikler görünür kaydedildi.
- [ ] R7 ortak davranışları bütün ilgili işlem ailelerine uygulandı.
- [ ] R8 sembol sınıfları ve senaryo kombinasyon kapsamı hesaplandı.
- [ ] Ortam erişimi ve borsa yürütme kabulü için kalan deneyler tanımlandı.
- [ ] SDK/belge/gözlem çelişkilerinin etkisi çözüldü veya belirli sınırla kaydedildi.
- [ ] R9 adayları somut açıklar üzerinden değerlendirildi.
- [ ] Kaynak bağlantıları, sürümleri ve iddiaların kanıtları denetlendi.
- [ ] Bütün açıklar için geliştirme ihtiyacı, erişim koşulu veya kapsam kararı belirlendi.
- [ ] Toplam kapsam ve tamamlanma hesabında işlenmemiş işlem satırı kalmadı.

Araştırma tamamlandı ifadesi API ve kaynak incelemesinin bu kabul listesini karşıladığı anlamında kullanılır. Eksik özelliklerin geliştirme sonrası borsa kabulü ayrı teslimdir. Karar vermeyi etkileyen kritik bilinmeyenler sürüyorsa araştırma kısmi olarak raporlanır, son plan o bilinmeyeni çözme adımına bağlı tutulur.

## 19. R11 geliştirme planına dönüşüm

Her geliştirme maddesi araştırmadaki açık kimliklerine ve talimat kimliklerine bağlanır. Paketler mevcut davranışı ve eski kayıtları dikkate alır. Ortak sözleşme ve ürün bağımlılıkları, ardından kullanıcıya kullanılabilir uçtan uca işlemler sıralanır. Öncelik sırf endpoint sayısına göre belirlenmez. Eksik temel işlem, mevcut yanlış kabul, finansal durum tutarsızlığı ve başka paketleri açan bağımlılıklar birlikte değerlendirilir.

Her geliştirme paketi aşağıdaki alanları taşır.

1. Çözülecek talimatlar ve araştırma bulguları.
2. Mevcut davranış ve hedef davranışın somut örneği.
3. Değişecek normal giriş, şema, servis, adaptör ve kalıcı kayıtlar.
4. Ürün/ortam ve hesap uygunluğu koşulları.
5. Önkoşul paketleri ve yeniden kullanılacak mevcut kod.
6. Kısmi başarısızlık, tekrar, eşzamanlılık ve restart tasarımı.
7. Eski kayıt uyumluluğu ve gerekiyorsa migration.
8. Yerel, entegrasyon ve borsa kabul senaryoları.
9. Kullanıcıya sunulan sonuç/hata durumları.
10. Tamamlanma ölçütü, efor aralığı ve kalan belirsizlikler.

R11 tesliminde nihai kapsam matrisi ile geliştirme paketleri çapraz denetlenir. Her geliştirilmesi gereken açık bir pakete bağlıdır. Her paket gerçek bir araştırma ihtiyacına dayanır. Araştırma sonunda ürün öncelikleri ve beklenen kullanıcı komutlarıyla birlikte review edilebilir plan sunulur.

## 20. İlerleme raporlama ve ilk adım

| Paket | Başlangıç durumu |
|---|---|
| R0 | Önceki envanter ve ölçümler mevcut, kapsam kaydı tamamlanacak |
| R1 | Kısmi, 95 işlem ve bazı parametre açıkları incelendi |
| R2–R6 | Ayrıntılı araştırma bekliyor |
| R7–R8 | Ön örnekler mevcut, tüm ürünlere uygulanacak |
| R9 | Ön repo araştırması mevcut, işlem hedeflerine göre yeniden değerlendirilecek |
| R10–R11 | Önceki paketlerin teslimlerine bağlı |

Her paket sonunda incelenen işlem/parametre kapsamı, yeni doğrulanmış açıklar, çözülmemiş sorular ve sonraki inceleme bildirilir. Tamamlanma sayıları sabit bir hedef sayıya ulaşmak için büyütülmez. İlk uygulama adımı R0 kaynak ve bot giriş kayıtlarını tamamlamak, ardından R1 normal/algo emir oluşturma ve değişiklik/iptal sözleşmelerini ayrıntılı incelemektir.

## 21. Önceki planın başlangıç notları

Aşağıdaki metin önceki kısa plandan korunmuştur. İçindeki tarihli bulguların kaynakları R0/R1 kapsamında yeniden doğrulanacak. Bu ek, yeni bir doğrulama çalışması olarak sayılmaz.

# Borsa işlem yetenekleri araştırma çalışma planı

Başlangıç tarihi 15 Kasım 2026. Araştırma devam ediyor. Hedef, kullanıcının verdiği borsa talimatının doğru parametrelerle uygulanması ve sonucun doğrulanması için gerekli işlem desteğini belirlemek.

Başlangıç ürünü mevcut çekirdeğin Binance USD-M Futures kapsamıdır. Mevcut 95 REST satırı ilk girdi olarak kullanılacak. WebSocket API işlem komutları, kullanıcı olayları ve piyasa akışları ayrıca envanterlenecek. Sonraki ürünler Spot, Margin, COIN-M, Options, Portfolio Margin ve hesap/cüzdan hareketleridir.

| Sıra | Araştırma paketi | Çıktı | Tamamlanma ölçütü | Durum |
|---|---|---|---|---|
| 1 | USD-M kaynak ve sürüm denetimi | Resmi referanslar, değişiklik tarihleri, eski/yeni parametre farkları | REST, WebSocket API, olaylar, filtreler, hata kodları ve ortam belgeleri kayıtlı | Başladı |
| 2 | USD-M işlem sözleşmeleri | Her işlemin parametreleri, koşulları, yanıtları, kısıtları | 95 REST girdisi güncellenmiş, yeni veya kaldırılan işlemler açıklanmış, WS kapsamı eklenmiş | Kısmi REST envanteri mevcut |
| 3 | Kullanıcı talimatı eşlemesi | Komut/API → doğrulama → yürütme → sorgu → kayıt ilişkisi | Her talimatın kullanılabilir giriş yolu veya somut eksiği bulunmuş | Kısmi |
| 4 | Yaşam döngüsü ve hata senaryoları | Kısmi dolum, iptal/değiştirme yarışı, yanıt kaybı, restart, tekrar ve eşzamanlılık | Her işlem için uygulanabilir senaryolar ve beklenen son durum belirlenmiş | Bekliyor |
| 5 | Sembol ve hesap koşulları | Tick/lot/nominal, ürün, hesap modu, teminat, limit ve yetki farkları | Geçerli/geçersiz kombinasyonların ölçüm planı hazır | Kısmi yerel ölçüm mevcut |
| 6 | Mevcut bot davranışının doğrulanması | Kaynak kanıtı, mevcut test tanığı, yerel örnek sonucu | Destek iddiaları ilgili komut ve sonuçla ilişkilendirilmiş | Kısmi |
| 7 | Ortam farkları | Demo/test ortamı/gerçek ortam destek tablosu | Her destek iddiası için kanıt veya bekleyen doğrulama koşulu kayıtlı | Bekliyor |
| 8 | Diğer ürünler | Spot, Margin, COIN-M, Options, Portfolio Margin, transfer envanterleri | Ürünlerin işlem ve hesap modelleri ayrı değerlendirilmiş | Bekliyor |
| 9 | Uygulama kaynakları | Resmi SDK/Postman/CLI ve uygun diğer repo karşılaştırması | Her repo kapanacak açık, sürüm, lisans ve entegrasyon yüküyle ilişkilendirilmiş | Ön liste mevcut |
| 10 | Araştırmanın kapanışı | Eksik analizi, bağımlılık sırası, geliştirme paketleri ve kabul senaryoları | Kapsamdaki her talimatın durumu ve yapılacak iş somutlaştırılmış | Bekliyor |

Her işlem kaydı kimlik, ürün, kullanıcı talimatı, resmi kaynak, inceleme ve yürürlük tarihi, yöntem/yol veya WS komutu, parametreler, hesap koşulları, sembol filtreleri, yanıt/olaylar, hata davranışı, bot giriş noktası, ilgili kod, test kanıtı, açıklar ve kabul ölçütlerini taşıyacak.

Araştırma sırasında mevcut davranışın incelenmesi ve yerel ölçümü yapılır. Geliştirme başlangıç ölçütü, işlem sözleşmeleri ve eksik analizinin tamamlanmasıyla somut uygulama planının çıkmasıdır. Dış ortamda kanıt toplanamayan durumlar bekleyen kabul koşuluyla kaydedilir. Borsa yürütme kabulü gereken noktalar geliştirme planında açıkça yer alır.

İlk kaynak paketi aşağıdadır.

| Kaynak | Araştırma amacı |
|---|---|
| [USD-M REST Trade](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade) | Emir, pozisyon, kaldıraç, teminat ve iptal işlemleri |
| [USD-M REST Account](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account) | Hesap, bakiye, komisyon, geçmiş ve hesap kısıtları |
| [USD-M Market Data](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) | Sembol kuralları, fiyat, defter ve destekleyici veriler |
| [General Info](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info) | Ortam, imza, zaman, limit ve belirsiz yanıt davranışı |
| [Change Log](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/change-log) | Yürürlük tarihli değişiklikler |
| [Error Codes](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/error-code) | Yazılımın ele alması gereken hata sonuçları |

Başlangıç incelemesinden elde edilen bulgular aşağıdadır.

| Bulgu | Resmi dayanak | Kod kanıtı | Durum |
|---|---|---|---|
| Kaldıraç için sabit 125 üst sınırı var | 9 Ekim 2026 değişikliği üst sınırın sembolün leverageBracket değerinden alınmasını açıklıyor | account_commands.py satır 18, plan_v2.py satır 35, portfolio.py satır 51, capabilities.py satır 135 | Destek sınırı doğrulandı. Hesap/sembol bazında borsa kabulü bekliyor |
| Trailing callback aralığı kodda 0.1–5 | 23 Ekim 2026 değişikliği algoOrder callbackRate üst sınırını 20 olarak bildiriyor | order_rules.py satır 97 ve önceki yerel örnekler | Destek sınırı doğrulandı. Güncel Demo davranışı bekliyor |
| Gelir geçmişinde eski page parametresinin kaldırılması kontrol edildi | 16 Ekim 2026 yürürlük tarihli değişiklik startTime/endTime kullanımını bildiriyor | history.py satır 85–86 zaman aralığı ve limit gönderiyor | İncelenen istek oluşturma bu değişiklikle uyumlu. Bütün sayfalama kabulü ayrıca gerekli |

Kaynaklar 15 Kasım 2026 tarihinde incelendi. İndirilebilir resmi OpenAPI şeması bağlantısına doğrudan erişim 202 ve boş gövde döndürdü. Şema dosyası alınmış olarak işaretlenmedi. Belgelerdeki alanlar, resmi SDK ve koleksiyonlarla karşılaştırılarak araştırma sürdürülecek.

Mevcut ayrıntılar [düzeltilmiş kapsam](EXCHANGE-CAPABILITY-SCOPE.md), [REST işlem tablosu](EXCHANGE-OPERATIONS.md) ve [parametre/kod kanıtı](../../../reports/crypto-bot-research-20261115/exchange-operation-audit.json) belgelerinde bulunuyor.
