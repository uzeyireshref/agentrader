# T08 — zaman dilimleri ve üst zaman bağlamı

12 Kasım 2026. Tamamlandı; plan 17/27. Sıradaki T09 gösterge yapılandırması.

Üst çubuğa 1/5/30 dakika eklendi; 15 dakika, 1/4 saat, günlük ve haftalık aralıklar korunur. History, WebSocket, kanıt parmak izi, çizim grid'i, çalışma alanı tercihi ve çizim görünürlük filtresi sekiz aralığı destekler. UTC kovaları ortak sözleşmeyle doğrulanır; haftalık başlangıç pazartesi UTC'dir.

Veri paneli → Üst zaman bağlamı isteğe bağlı açılır. Daha büyük bir aralık seçildiğinde `/api/higher-context` doğrudan native Binance USD-M klines history'sinden son kapanmış mumu getirir. Yeniden örnekleme yapılmaz. Açık temel mum için başlangıç, kapalı temel mum için kapanış sınırı referanstır; üst mumun kapanışı bu referanstan ve ölçülmüş sunucu zamanının belirsizlik düşülmüş alt sınırından önce olmalıdır. Henüz kapanmamış üst mum veya beklenen son kapanmış mumdan daha eski kayıt gösterilmez. Kaynak, sembol, aralık, UTC grid, kesin fiyat ve saat kanıtı doğrulanamazsa değer yerine açık engel gösterilir.

Bağlam değiştiğinde önceki değer hemen gizlenir; devam eden istek iptal edilir ve geç cevap yeni seçimi değiştiremez. İstekler 250 ms bekletilir; her tick için yeni istek yoktur. Güncelleme elle “Üst zamanı yenile” ile yapılır. Haftalık temel aralıkta desteklenen daha büyük aralık olmadığı açıklanır. Çoklu grafik ve otomatik üst-zaman göstergesi bu teslimin kapsamı değildir. Bilgi paneli bot/işlem yetkisi vermez.

## Doğrulama

- 788 Python testi geçti. Altı yeni test grubu sekiz aralığın UTC sözleşmesini; yeni üç aralığın pagination/warmup/kapanış/reseed bağlantısını; saat belirsizliğiyle tam sınır ve tarihsel referansı; eksik grid/yanlış kaynak/kanıtsız fiyat reddini; tercih ve görünürlük kaydını; gerçek HTTP endpoint kabulünü kapsar.
- 221 frontend testi geçti. Yedi yeni test interval sözleşmesi, üst hedefler, açık/kapalı referans, erken/eskimiş üst mum, saat belirsizliği, yanlış bağlam/provenans ve engelli yanıtta OHLC reddini kapsar.
- Üretim TypeScript/Vite derlemesi geçti. Ana JS 536.95 kB, gzip 170.46 kB; mevcut 500 kB uyarısı sürer. QA01 performans kabulü açık kalır.
- 10 yeni üretim arayüzü tarayıcı kontrolü geçti. Yeni üç aralık, isteğe bağlı yükleme, kaynak/referans, hedef değiştirme, hatalı yanıtta eski değerlerin kaldırılması, tekrar deneme, 1024 px taşmasız yerleşim ve haftalık sınır doğrulandı. Açık/koyu ekranlar incelendi.
- G01/G03/G04 için 42 ilgili regresyon tarayıcı kontrolü geçti. Testler sentetik piyasa ve izole SQLite kullanır; canlı borsa paritesi veya fiziksel GPU/touch kabulü değildir. Hesap/emir çağrısı ve sayfa hatası yok.

Rapor: `reports/chart-t08-validation-20261112.json`; test günlükleri `reports/t08-*.log`; kaynak ve derleme SHA256 manifesti `reports/chart-t08-delivery-20261112.json`.

Native endpoint/aralık araştırmasının birincil kaynakları: [Binance connector market.py](https://github.com/binance/binance-futures-connector-python/blob/main/binance/um_futures/market.py), [Binance public data](https://github.com/binance/binance-public-data). Canlı ağ davranışı yerine kontrollü sözleşme testleri kullanıldı.
