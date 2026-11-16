# Mevcut botun güvenilirliği için öncelik kararı

**Nihai yerel doğrulama: 1649 test / 155.096 saniye / OK; geniş kabul 290 test / 44.5 saniye / 0 skip; grafik replay 36/36.**

16 Kasım 2026. Kullanıcı, planın derin incelenmesini, sorunsuz çalışmaya en fazla katkı veren paketlerin uygulanmasını ve kalanların açıkça uygulanmadı olarak ertelenmesini istedi. Bu turdaki amaç mevcut Binance USD-M Demo yürütmesinin güvenilirliğidir. Strateji seçimi kullanıcıda kalır.

## Karar ve gerekçe

G00–G12 teslimlerinin normal giriş, kalıcı niyet, sahiplik, risk rezervi, iptal/amend/batch, hesap ayarı, sorgu/geçmiş, ortam ayrımı ve WS sınırları incelendi. G02/G03/G07/G09/G11/G12 mevcut çalışmanın kritik temelidir; bunların kabul kapsamları korunur. G04/G05/G06/G08/G10 da mevcut yeteneklerin parçasıdır. Tamamlanan paketler yeniden uygulanmış gibi sayılmadı.

| Seçim | Öncelik | Somut ihtiyaç | Bu turdaki teslim |
|---|---|---|---|
| G13 | Kritik | Kesinti, gecikmiş/tekrarlanan olay ve dolum sıraları test edilmeden yeni yolların güvenilirliği bilinemez | Seed ile tekrarlanabilir model dizileri, aynı hatayı koruyan küçültme ve mevcut gerçek süreç kesinti testlerini birleştiren kabul aracı |
| G22 | Kritik | UNKNOWN, durmuş izleyici, kota beklemesi ve toparlanma gecikmesi birlikte görünmüyordu | Salt okunur owner/context kontrollü CLI/API görünümü ve sabit isimli sayısal metrikler |
| G23 | Kritik, yerel kapsam | Test sayısı bütün borsa desteği veya gerçek hesap kabulü gibi yorumlanmamalı | Kapsam matrisi, tüm Python kaynaklarını bağlayan kanıt manifesti ve sürüm/kapsam tutarlılık denetimi |

G13 ilk turunda gerçek bir durum birleştirme açığı bulundu: kısmi gerçekleşme korunurken durum REJECTED kalabiliyordu. 60 adımlık bir diziden iki olaylık örnek çıkarıldı. Düzeltme, kanıtlı dolumun terminal sıfır-dolum reddi sayılmasını önler. Eski çelişkili kayıtlar G22'de dikkat gerektiren durum olarak görünür; geçmiş kayıtları otomatik yeniden yazılmaz.

Windows'ta cp1252 çıktıda erken `commands`/`discovery` yönlendirmesinin UTF-8 ayarını atlaması da giderildi. Normal CLI yardımının bu ortamda açılması subprocess testiyle doğrulandı.

## Şimdilik uygulanmayan paketler

| Paket | Durum | Erteleme nedeni ve yeniden başlama koşulu |
|---|---|---|
| G14 Spot | UYGULANMADI — ERTELENDİ | Mevcut Futures yolundan farklı bakiye/emir-listesi muhasebesi ekler. Spot ihtiyacı seçildiğinde kendi filtre, parent/child ve kabul yoluyla başlanmalı. |
| G15 Margin | UYGULANMADI — ERTELENDİ | Borç/faiz ve borrow/repay yan etkileri mevcut USD-M işleyişinin önkoşulu değildir. G14/G19 ve borç muhasebesi kapıları gerekir. |
| G16 COIN-M | UYGULANMADI — ERTELENDİ | Inverse kontrat/coin/teslim muhasebesi yeni ürün işidir. G09'un ortak hesap modu için dar CM okumaları korunur; bunlar CM finansal yürütmesi sayılmaz. |
| G17 Options | UYGULANMADI — ERTELENDİ | Prim/vade/exercise/MMP ve olay şeması ile hesap/ortam erişimi ayrı kabul ister. |
| G18 PM/Pro/SPAN | UYGULANMADI — ERTELENDİ | G15/G16 ve hesap modeline özel risk bağımlılıkları vardır; mevcut portfolio.py bu ürünleri uygulamaz. |
| G19 Wallet | UYGULANMADI — ERTELENDİ | Transfer/çekim/ağ/adres/ücret ve iki hesap ayağı ekler. Mevcut emir güvenilirliğinin bağımlılığı değildir. |
| G20 Convert | UYGULANMADI — ERTELENDİ | Teklif/kabul/dönüşüm muhasebesi ve G19 bağımlılığı ayrı ihtiyaçtır. |
| G21 Sub Account | UYGULANMADI — ERTELENDİ | Master/sub/VIP/izin ve iki hesap etkisi gerekir; mevcut tek demo hesap yolunun önkoşulu değildir. |

Bu ürünlerin G11 keşif kayıtları korunur. Salt okuma kaydı veya public sorgu, finansal ürün uygulaması olarak işaretlenmez. Yeniden başlatma kararı ilgili paketlerin yeni açık kapsam seçimini gerektirir; bu turda örtük sonraki iş değildir.

## Kabul sınırı ve mevcut yerel durum

Kod kabulü, [G13](G13.md), [G22](G22.md), [G23](G23.md) ve `reports/exchange-development-20261115/reliability-priority-validation.json` ile sürüme bağlanır. Mevcut davranışa ait sınırlar korunur: sahip olunan plan/oturum, USDT perpetual filtreleri, varsayılan risk kapıları, altı WS yöntemi ve kaynak sözleşmesi belirsizlikleri. Manuel pozisyon devralma, her USD-M sözleşmesi ve bütün 83 tarihsel WS kaydı tamamlandı sayılmaz.

Salt okunur yerel gözlemde varsayılan `data/execution.sqlite3` için **CONTEXT_UNVERIFIED** elde edildi. Bu, eski günlüğün doğrulanmış ortam işareti bulunmadığını gösterir. Günlük silinmedi, kimlik/rezerv/durdurma değiştirilmedi. Bu veri kökeni/migration kabulü ve kimlik doğrulamalı hesap/borsa kabulü açık kalır. Kod testleri bu yerel durumu temiz veya işlem yapmaya hazır ilan etmez.

G23 bu nedenle yalnız seçilen USD-M yazılım kapsamını yerelde kapatır. Orijinal bütün ürün geliştirme planı tamamlandı olarak gösterilmez ve hiçbir hata olmayacağı garantisi verilmez.
