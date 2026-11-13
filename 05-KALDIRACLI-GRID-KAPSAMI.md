# Kaldıraçlı grid geliştirmesi

Tarih: 6 Kasım 2026. Güncel durum: plan v2 grid yürütücüsü kodu eklendi;
312 test geçti. Gerçek demo yazma doğrulaması henüz yapılmadı.
Güncel sözleşme: [08-GRID-YURUTME-VE-REZERVASYON.md](08-GRID-YURUTME-VE-REZERVASYON.md).
Aşağıdaki 132/134 test ve kapalı yürütme notları ilk aşamanın tarihsel
kayıtlarıdır; kullanıcının planı veya bütçesi değiştirilmedi.

## Kullanıcının planı

Demo BTCUSDT LONG, giriş LIMIT 75725, kaldıraç 20x, alt sınır 73000,
üst sınır 82500, 8 aritmetik aralık, stop 71000. Kullanıcı tutarı açıkça
**200 USDT toplam nominal** belirledi. Bu, 200 USDT teminat değildir ve
4000 USDT pozisyon açma yetkisi vermez. Bütün grid alımları bütçeye dahildir.

Dokuz sınır: 73000 / 74187.5 / 75375 / 76562.5 / 77750 / 78937.5 / 80125 /
81312.5 / 82500. Aralık farkı 1187.5 USDT'dir.

## Borsa ön kontrolü

BTCUSDT minimum yeni alış nominali 50 USDT, miktar adımı .0001 BTC,
fiyat adımı .10 USDT. Hesap one-way, açık pozisyon/emir yok. SymbolConfig
kaldıraç 20 ve marginType CROSSED döndürdü. Hesap ayarları değiştirilmedi.

200 USDT bütçede hücre miktarı .0003 BTC; alış nominali yaklaşık 21.9–24.394
USDT, minimumun altında. Eşit BTC hücreleri için minimum .0007 BTC gerekli.
Bu uygulama toplam miktarın üst bant fiyatından nominalini de sınırladığı
için minimum bütçe .0007 × 8 × 82500 = 462 USDT çıkar. Alt sınır fiyatlarından
alış rezervi ise 432.075 USDT'dir. 462 USDT bütün Binance gridleri için
evrensel minimum değil, bu ihtiyatlı eşit miktarlı modelin hesabıdır.

İstenen plan BLOCKED. Eski risk profili 100 USDT nominal ve 5 USDT işlem
kaybı sınırlarını korur; kendiliğinden yükseltilmedi. Tüm hücreler için
ihtiyatlı stop kaybı 16.15875 USDT, masraflar hariç. Sonuç:
`reports/grid-preflight-20261106.json`. Yeni emir ve kaldıraç POST'u yok.

## Eklenen işlevler

- `agentrader/grid.py`: seviyeler, tick/lot/minimum nominal doğrulama,
  tekrar alım rezervi, toplam nominal ve stop riski denetimi.
- Salt okunur kaldıraç/basamak kontrolü; açık çağrıyla boş hesapta kaldıraç
  ayarlayıp SymbolConfig ile doğrulayan yardımcı. Zaman aşımı tekrar edilmez.
- Kalıcı GridLedger: başlangıç stoğu ve hücrelerde BUY → SELL → BUY döngüsü.
  SELL teklifleri reduceOnly=true. Yalnız tam ve kimliği/miktarı/yönü eşleşen
  FILLED yanıtı ilerler. Tekrarlı fill ikinci işlem üretmez. Restart aynı
  eylem kimliğini korur; STOPPING durumunda yeni döngü üretilmez.
- `python -m agentrader grid preview DOSYA --output RAPOR` yalnızca ön
  kontroldür; emir açmaz, kaldıraç değiştirmez, risk sınırını yükseltmez.

## Yürütme henüz tamamlanmadı

GridLedger tek başına borsayla çalışan grid botu değildir. Önce sürümlü grid
yetkisi, aktif alışların ve envanterin portföy riski, gerçekleşme sahipliği,
başlangıç fill/stop sıralaması, kısmi fill/iptal yarışı, borsa korumaları ve
restart uzlaştırması tamamlanmalı. Stop sonrası bekleyen alışlar yeniden
pozisyon açmamalı; iptal ve terminal durum doğrulanmalı. Eski tek girişli
Watchdog grid defterini devralmaz. Tamamlanmış grid desteği iddiası yoktur.

132 test geçti; yeni 14 test bütçe, filtreler, döngü, kimlik, tekrar,
restart, kısmi/belirsiz fill ve kaldıraç kontrolünü kapsar. Gerçek grid
açılışı ve 20x stop/likidasyon senaryosu test edildi sayılmaz.

Kaynaklar: Binance resmî USD-M REST trade/account belgeleri ve Futures Grid
rehberi. CROSSED modunda hesap bakiyesi teminata katkı sağlayabilir;
200 USDT nominal, izole teminat veya azami kayıp değildir. Likidasyon ve
teminat politikası yürütme öncesi ayrıca doğrulanmalıdır. Teminat modu
değiştirilmedi; bütçe/grid sayısı için kullanıcı yerine karar verilmedi.

### Son kullanıcı değişikliği

6 Kasım 2026: fiyat bandı 73000–78000 ve 4 grid korunarak stop 74000 yapıldı.
20x ve önceki açık 200 USDT toplam nominal tercihi korundu; 'üst sınır
muhabbetine takılma' ifadesi sınırsız bütçe veya otomatik risk yükseltme
sayılmadı. Taslak dosyası btc-grid-user-20261106-four.json güncellendi.
Bandın içindeki stop artık genel şema hatası değil, stop sonrası alt alış
emirlerini iptal etme gereksinimi olarak raporlanıyor. 73000 alışının stop
sonrasında yeni pozisyon açması engellenmeden yürütme etkinleşmez. Çevrimdışı
mark-stop kontrolü yeni döngüleri durdurur. 134 test geçti. Demo ön kontrol
BLOCKED; yeni emir yok, grid yürütücüsü hâlâ tamamlanmadı.
