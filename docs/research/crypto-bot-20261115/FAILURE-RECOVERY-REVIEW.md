# Hata ve toparlanma araştırması

15 Kasım 2026. 1–5 geniş turu. Aşağıdaki kararlar mevcut kod ve testlerin incelenmesinden çıkarıldı. Diğer ürünlerde uygulanması gereken davranışlar tasarım gereksinimidir.

## Ortak durum sözleşmesi

Talimat hazırlanması → kalıcı niyet/rezervasyon → gönderim denemesi → kabul/ret/belirsiz sonuç → kimlikle sorgu → dolum ve hesap uzlaştırması → kesin sonuç. İstemci yanıtı kaybettiğinde borsanın emri kaybettiği varsayılmaz. Bulunamayan emir de tek başına ret kanıtı değildir. Kayıtta ürün, ortam, hesap, sembol, normal/algo/liste/child kimlik alanı ve komut sürümü bulunmalı.

| Olay | Gerekli davranış | Mevcut kanıt | Ürünlere genişleme |
|---|---|---|---|
| GET geçici ağ hatası | Sınırlı tekrar, her denemede taze imza | shared/transport.py, test_transport | Mevcut temel tekrar kullanılabilir |
| POST/PUT/DELETE timeout | Belirsiz sonucu kaydet, otomatik tekrar gönderme | test_mutations_never_retry_timeout | Ürün bazlı sonuç sorgusu eklenmeli |
| HTTP 503 | Gövde ve hata koduyla ret/belirsiz ayrımı | test_http_503_variants_preserve_uncertainty | Her ürün hata sözleşmesine bağlı |
| HTTP 200 içinde hata | Başarı sayma | test_http_success_with_error_payload_is_not_success | Diğer yanıt zarfı biçimleri incelenmeli |
| 429/418 | Kalıcı bekleme ve Retry-After | RequestGovernor, GovernorTests | UID/IP/order ve UM/CM ortak bütçeler eklenmeli |
| Saat/imza/izin hatası | Finansal niyeti çoğaltmadan düzelt, uygunluk yeniden denetle | exchange.sync_time, transport hata kodları | Hesap/ürün izin keşfi gerekir |
| Bozuk JSON/yarım yanıt | Mutasyon sonucu UNKNOWN kalır | test_invalid_json_mutation_is_unknown | Yeni ürün parserları aynı ilkeyi korumalı |
| Emir bulunamadı | Kimlik, zaman penceresi, aktif emir/pozisyon/geçmiş sorgula | history_reconciliation missing_order testi | Ürün saklama süreleri ayrı |
| Kısmi dolum | Gerçek miktarı muhasebeleştir, kalan ve korumaları yeniden hesapla | batch/amend/guardian testleri | Liste, borç ve prim ilişkileri eklenmeli |
| İptal sırasında dolum | İptal kabulüyle pozisyonu sıfır varsayma | guardian fill_during_cancel | Bütün emir ailelerine uygulanmalı |
| Amend sırasında dolum | Yeni revizyonu yanlış uygulama | order_amend fill_during_put | Spot cancel-replace/keep-priority ayrı |
| Batch kısmi sonuç | Her üyeyi ayrı teyit et | batch_create/batch_cancel/order_amend | Ürün limitleri ve alt kimlikler ayrı |
| Başka istemci değişikliği | Hesap snapshotı ve sahiplik uyuşmazlığını görünür kıl | foreign_position, manual_price_change testleri | Master/sub ve PM birleşik kapsam gerekir |
| Restart | Journal ve rezervi yeniden yükle, belirsiz niyeti tekrar gönderme | recovery_process 9 çökme noktası | Diğer ürün niyet tabloları yok |
| Guardian kaybı | Yeni giriş kapısını durdur, mevcut koruma sahipliğini koru | test_recovery_guardian | Yeni ürünlere mevcut sınıf otomatik yetki vermez |
| WS kopması/anahtar bitişi | REST bariyeri, snapshot/geçmiş, sonra devam | test_stream_recovery, test_user_stream | Spot/Margin/PM aboneliği ayrı |
| Tekrarlı/sırasız olay | Kimlik/sürüm ve birikimli dolumla tekilleştir | user_stream normalizasyonu | Her ürün E/T ve payload sözleşmesi gerekir |
| Risk/tasfiye/ADL | Borsa tarafından oluşan kapanışı kullanıcı emriyle karıştırma | USD-M olay tanıma kısmi | CM teslim, Options exercise, PM risk ayrı |
| Borç/transfer sonucu gecikmesi | İki muhasebe ayağını ve geçmişi doğrula | Mevcut ürün desteği yok | Margin/Wallet/Sub/PM açığı |

## Mevcut güçlü taraflar

Kalıcı rezervasyon ve journal, değişiklikte digest/sahiplik, belirsiz gönderimi tekrar etmeme, batch üye teyidi, restart bariyerleri ve manuel değişikliklerde durdurma mevcut testlerle destekleniyor. Bu parçalar genişlemede kullanılabilir. Araştırma turunda geçen 1262 test bu mevcut kapsamın kanıtıdır.

## Doğrulanmış altyapı sınırları

RequestGovernor host anahtarıyla bekleme saklıyor. Güncel CM/UM duyurusu ortak limit havuzlarını açıkladığından ayrı hostların birikimli bütçesini bu yapı tek başına karşılamaz. Başlıkları okumak, gönderim öncesi ağırlık/UID/order kotasını rezerv etmekle aynı davranış değildir.

Kalıcı kimlikler mevcut USD-M yollarına bağlıdır. Spot order lists, CM strategyId, PM algo/conditional ve transfer/borç kimlikleri için ayrı eşleme gerekir. Ortak bir `FINISHED` sonucu her üründe tam dolum anlamına gelmez.

Mevcut normal akış USD-M hesabını okur. UM/CM ortak position mode değişikliği öncesi iki ürünün aktif emir/pozisyonlarını birlikte doğrulama ihtiyacı açık bir geliştirme bulgusudur. Sadece bir ürünü okumak ortak hesap ayarının etkisini kapsamaz.

## Yeni ürünlere uygulanacak kabul senaryoları

Her finansal mutasyon için sonuç kaybı, tekrar komut, restart öncesi/sonrası ve yanlış hesap kimliği senaryoları gerekir. Her batch için boş/eksik/tekrarlı/karışık sonuç gerekir. Her liste için parent/child olayı, kısmi gerçekleşme ve iptal yarışı gerekir. Her hesap hareketi için tek ayağın gecikmesi, çift kayıt, ücret/kur/faiz farkı gerekir. Bu çapraz uygulama araştırma tasarımıdır, çalıştırılmış yeni ürün testi sayılmaz.

Kaynaklar: yerel `shared/transport.py`, `bot/execution.py`, `bot/user_stream.py`, `bot/history.py`, `bot/recovery_guardian.py`, `tests/test_transport.py`, `tests/test_stream_recovery.py`, `tests/test_recovery_process.py`, `tests/test_history_reconciliation.py`, [CM/UM ortak mimari](https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice). Tam kaynak hashleri operation-support-audit.json içindedir.
