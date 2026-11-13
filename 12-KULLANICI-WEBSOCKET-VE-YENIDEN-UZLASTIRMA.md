# Kullanıcı WebSocket bağlantısı ve yeniden uzlaştırma

6 Kasım 2026. Kullanıcı akışı mevcut demo SINGLE/grid oturumlarının yönetimine
bağlandı. Gerçek hesap adresi ve WebSocket üzerinden emir gönderme yolu yoktur.

## Akış

1. Demo hesabından kullanıcı akışı anahtarı alınır ve TLS WebSocket bağlantısı
   kurulur. Anahtar bellekte tutulur; günlüğe veya rapora yazılmaz.
2. Her yeni bağlantıda önce REST üzerinden sahiplik, gerçekleşme, açık emir,
   pozisyon ve koruma kontrolleri yapılır. Önceki süreçten bekleyen olay varsa
   bu olayın borsada görünmesi de doğrulanır.
3. Normal ve koşullu emir olayları sınırlı alanlara normalleştirilir. Olay kaydı
   ve bekleyen uzlaştırma işareti SQLite üzerinde atomik saklanır. Bu işaret
   yeni girişleri engeller; sürecin kapanması işareti silmez.
4. Normal emirlerde kimlik, kümülatif gerçekleşme ve terminal durum REST ile
   karşılaştırılır. Koşullu emirlerde algo kimliği, durum ilerlemesi, tetiklenen
   alt emir ve gerçekleşen miktar doğrulanır. REST gecikiyorsa en çok üç okuma
   yapılır; doğrulanamazsa yürütme durur. Bu bekleme bir emir gönderme tekrarı değildir.
5. Salt okunur oturum kontrolü başarılı olunca işaret kaldırılır. Sonra mevcut
   yürütücünün onay, risk, sahiplik ve koruma kontrolleriyle yönetim sürer.
   WebSocket mesajı doğrudan envantere dolum eklemez veya işlem yetkisi vermez.

Hesap, yapılandırma ve diğer kısmi olaylar REST kontrolünü uyandırır. Bunlar tam
hesap görünümü olarak kabul edilmez. Tekrarlanan mesajlar bellekte sınırlı bir
kimlik önbelleğiyle elenir; dolum muhasebesi mevcut REST/journal yolunda kalır.
Olay yokken periyodik REST izleme sürer.

## Bağlantı yaşam döngüsü

Akış istekleri yalnız API anahtar başlığı kullanır; listenKey isteklerine HMAC,
timestamp veya sorgu parametresi eklenmez. Süre yenilemesi 30 dakikada bir;
planlı bağlantı yenilemesi 23 saatte yapılır. Ping/pong, sessiz bağlantı kaybını
da denetler. Yeniden bağlantı denemeleri sınırlıdır; her bağlantı tekrar REST
kontrolünden geçer. Emir yanıtı belirsizliği bağlantı hatası gibi tekrar edilmez.

Soket kapanırken uzak hesaptaki ortak listenKey silinmez. Binance aynı hesaptaki
aktif anahtarı tekrar verebildiği için DELETE başka istemcileri de etkileyebilir.
Yerel soket kapatılır ve anahtar bellekte bırakılmaz. HTTP yönlendirmesi takip
edilmez; WebSocket el sıkışmasının 101 yanıtı doğrulanır.

## Kullanım

Gerekli isteğe bağlı paket: `pip install -e ".[streams]"`.

Mevcut bir oturumu emir göndermeden akışla izlemek:

```powershell
python -m agentrader plans manage SESSION_ID --user-stream --iterations 2
```

Bu komut akış kaynağı oluşturur/yeniler; işlem emri veya hesap ayarı değiştirmez.
Onaylı mevcut oturumun yürütmesini devralmak için aynı komuta `--execute-demo`
eklenir. Bu seçenek yeni bir plan veya yeni işlem onayı oluşturmaz. Gridin
kontrollü ön plan çıkışında mevcut DRAINING davranışı korunur.

Oturum yönetimi başlatmadan bağlantı kontrolü:

```powershell
python scripts/check_demo_user_stream.py
```

## Doğrulama ve kalan sınır

Tam test kümesi: **430 test başarılı**. Testler bağlantı kaybı, süre yenilemesi,
ping/pong, bozuk mesaj, özel anahtarın hata/raporda görünmemesi, REST gecikmesi,
normal/koşullu emir kimliği, yeniden başlatma ve kalıcı bekleme işaretini kapsar.
Grid entegrasyon testi bekleyen dolumu yeniden başlatma sonrası doğrular ve
karşı emrin yalnız bir kez gönderildiğini denetler.

Gerçek demo bağlantısı, listenKey POST/PUT ve ping/pong başarılıdır:
`reports/user-stream-connection-20261106.json`. Bu kontrolde özel hesap olayı
alınmadı; emir açılmadı ve hesap ayarı değiştirilmedi. Yeni açılmış somut onaylı
demo işlemiyle gerçek fill/iptal/stop olaylarının uçtan uca ve uzun süreli
kesinti doğrulaması hâlâ yapılmalıdır. Bu sonuç A0–A12'nin tamamlandığı anlamına gelmez.

Kaynaklar: [Binance kullanıcı akışları](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams),
[akış REST işlemleri](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/user-data-streams),
[demo adresleri](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info),
[resmî koşullu olay modeli](https://github.com/binance/binance-connector-python/blob/master/clients/derivatives_trading_usds_futures/src/binance_sdk_derivatives_trading_usds_futures/websocket_streams/models/algo_update_o.py),
[WebSocket istemci belgeleri](https://websocket-client.readthedocs.io/en/latest/examples.html).
