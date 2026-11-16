# Birleşik eksik ve kabul gereksinimleri

15 Kasım 2026. 34 bulgu ailesi. Bu aileler bağımsız hata sayısı veya hazır geliştirme iş paketi değildir. 555 başlangıç işlemi bir aileye bağlı, 3 resmi ek ve 3 uygulama adayı ayrı kaydedildi.

| Kimlik | Bulgu | Kabul ölçütü |
|---|---|---|
| F01 | Ürün/hesap/ortam kimliği: Ortak istek ve journal kimliği USD-M dışı ürünleri kapsamalı | Aynı sembol/kimlik başka ürün veya hesapta yanlış kayda bağlanmaz |
| F02 | Genel kullanıcı işlem yüzeyi: Planlı SINGLE/GRID dışında keyfi borsa talimatları için normal giriş sınırlı | İstenen işlem normal komuttan doğrulama, yürütme ve sonuç teyidine ulaşır |
| F03 | TIF/priceMatch/STP/response seçimi: Yardımcı validator ve standart plan seçenekleri farklı. ACK/RESULT reddediliyor | Seçilen alanlar korunur, çelişen kombinasyon gerekçeyle reddedilir |
| F04 | Trailing callback sınırı: 7.5/10/20 yerel reddi, güncel UM algo şemasıyla fark | Ürünün güncel aralığı desteklenir, aralık dışı reddedilir |
| F05 | Borsa trailing ile yerel stop yenileme ayrımı: native_stop aynı native trailing emir sözleşmesi değil | Kullanıcı talimatı doğru yerel/native modele açıkça bağlanır |
| F06 | Artırma/azaltma/yön değiştirme: SINGLE scale-in/reentry ve allow_reverse sınırları | Gerçek pozisyon miktarı, sahiplik ve riskle açık talimat uygulanır |
| F07 | İptal kapsamları ve zamanlayıcı: Genel normal/algo iptali ve countdown yolları eksik | Seçili/sembol/hesap/bot kapsamı ayrı, dolum yarışı uzlaştırılır |
| F08 | Batch işlem çeşitliliği: Native create LIMIT/GTC akışına bağlı | Geçerli ürün/emir kombinasyonu ve her alt sonuç bağımsız teyit edilir |
| F09 | Dinamik kaldıraç basamağı: Sabit 125 sınırı mevcut | Hesap/sembol leverageBracket ile uygunluk ölçülür |
| F10 | Dinamik fiyat bandı: PERCENT_PRICE dışı 527 örnek validatorca teklif edildi | Güncel fiyat referansı ve filtre bandı yerel kontrolde değerlendirilir |
| F11 | Hemen tetiklenen koşullu emir: 527 BUY STOP örneği mevcut markın altında teklif edildi | Emir türü/yönü/workingType için tetik uygunluğu değerlendirilir |
| F12 | Yeni sembol risk/limit filtreleri: POSITION_RISK_CONTROL ve order/list/amend limitleri kapsamı | Bilinmeyen veya kısıtlayıcı filtre izin verilmiş kabul edilmez |
| F13 | UM/CM ortak hesap modu: Tek ürün okuması ortak dualSidePosition etkisini kapsamaz | İki ürünün aktif emir/pozisyonu ayar değişimi öncesi değerlendirilir |
| F14 | Ortak rate-budget modeli: Host cooldown ortak IP/UID/order kotası değildir | Birleşik UM/CM ve ürün özel limitlerinde toplam bütçe korunur |
| F15 | Geçmiş bütünlüğü: Tüm emir/algo/geçmiş yolları ve saklama sınırları kapsanmıyor | Süre penceresi ve sayfalama eksik sonucu tam başarı yapmaz |
| F16 | Spot ürün desteği: Normal/SOR/listeler/amend/pegged/iceberg için ürün akışı yok | Spot bakiye, filtre, parent/child ve sonuç muhasebesi kabul edilir |
| F17 | Margin ürün desteği: Borç/faiz/cross/isolated/listeler/repay süreci yok | Anapara/faiz, yan etki ve hesap riski uzlaştırılır |
| F18 | COIN-M miktar ve muhasebe: Inverse kontrat/coin teminat/vade desteği yok | Kontrat ve coin birimleri, PnL/funding/teslim doğru tutulur |
| F19 | CM algo geçişi ve ek envanter: Üç resmi ek ve üç uygulama adayı, tam alan/sınır çelişkisi | Resmi tam sözleşme veya belirli kontrollü kabul kapısı sağlanır |
| F20 | Options ürün desteği: Prim/vade/exercise/MMP/block-trade süreçleri yok | İlgili hesap ve olay şemaları, kullanım ve nakit akışı kabul edilir |
| F21 | Portfolio Margin/Pro/SPAN: Yerel portfolio.py bu ürün adaptörü değil | Hesap modeline uygun birleşik teminat/borç/risk/işlem yönlendirme |
| F22 | Convert yaşam döngüsü: Teklif/kabul/limit/sonuç komutu yok | Teklif süresi, cüzdan ve dönüşüm sonucu uzlaştırılır |
| F23 | Wallet süreçleri: Transfer/dust/deposit/withdraw/Travel Rule akışları yok | Ağ/adres/memo/ücret/izin ve hareket geçmişi teyit edilir |
| F24 | Sub Account süreçleri: Master/sub/managed yetki, transfer ve pozisyon taşıma yok | İki hesap etkisi ve operasyon özel VIP/ürün koşulları teyit edilir |
| F25 | WS API komut arabirimi: Olay dinlemek WS emir API desteği değildir | 83 kaynak komutun gerekli alt kümesi normal talimat ve sonuç takibine bağlanır |
| F26 | Ortam ve hesap kabulü: Public GET başarısı private işlem uygunluğu değildir | Ürün/ortam/anahtar/hesap uygunluğu ayrı kabul kanıtı taşır |
| F27 | Kaynak şeması belirsizlikleri: Options iç olay alanları, CM algo ve transfer örneği açık | Belirli bilinmeyen alan için kaynak veya dış kabul sonucu kaydedilir |
| F28 | Yeni ürünlerde recovery: Mevcut USD-M kanıtları diğer ürünlere otomatik taşınamaz | Lost reply, restart ve kısmi sonuç her ilgili ürün ailesinde kanıtlanır |
| F29 | İşlem gözlemi: UNKNOWN/WS/uzlaştırma/limit metriklerinin ortak görünümü geliştirilmeli | Belirsiz işlem ve recovery gecikmesi kullanıcıya ve operasyon kaydına yansır |
| F30 | Durum makinesi test kapsamı: Mevcut testler bütün yeni sıra kombinasyonlarını kapsamaz | Gerektiğinde model tabanlı testler anlamlı muhasebe/tekilleştirme invariantlarını sınar |
| F31 | Snapshot tutarsızlığı: SXP 62 ölçümü veriden bloklu | Tutarlı yeni filtre/fiyat çifti bulunursa ölçülür, önceki engel korunur |
| F32 | Sürüm ve kanıt güncelliği: 555 ortak şema eşleşmesi tam canlı sözleşme kanıtı değil | Kaynak/ortam/kod sürümü değişiminde ilgili kanıt yeniden değerlendirilir |
| F33 | USD-M eksik REST yolları: 55 başlangıç işleminde adaptör yolu yok | Her seçilen yol normal komut ve uygun yaşam döngüsüyle tamamlanır |
| F34 | Diğer istemcide piyasa veri yolu: Bir yol başka istemcide bulunuyor | Ortak ürün/ortam/veri sözleşmesine bağlanır, route varlığı yürütme desteği sayılmaz |

## Kapsam hesabı

Başlangıç 555 REST: 39 izinli adaptör yolu, 1 diğer istemci referansı, 515 ürün/yol açığı. Resmi CM duyurusundaki 3 yeni yol ile kayıtlı resmi yol envanteri 558. Bu üç ekte tam alan sözleşmesi henüz yok. CCXT kaynaklı üç aday bu sayıya eklenmedi. 83 WS API komutu ayrı arabirim envanteridir. Bütün API veya hizmet ürünlerinin toplamı olarak yorumlanamaz.

## Geliştirme planına geçiş girdisi

Bu dosya neyin değişmesi ve hangi sonuçla kabul edilmesi gerektiğini gösterir. Sıralama, paket bağımlılıkları, veri migrationı ve efor tahmini sonraki geliştirme planının işidir. F19/F26/F27 kapsamındaki kabul kapıları çözülmeden ilgili ürün için tam destek sözü verilmez. Mevcut USD-M çekirdeği ve diğer ürünler için kapsam kararları ayrı tutulabilir.
