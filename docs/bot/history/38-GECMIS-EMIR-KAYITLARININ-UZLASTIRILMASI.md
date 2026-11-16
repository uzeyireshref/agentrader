# Geçmiş emir kayıtlarının uzlaştırılması — 14 Kasım 2026

Kapatma sonrası kalan üç eski `NEW` niyet, Binance USD-M Demo borsa tarihçesinden doğrulanarak yerelde güncellendi. Borsaya yalnız GET gönderildi. Yeni giriş, iptal, azaltma veya hesap ayarı isteği yapılmadı. Mevcut giriş durdurması kaldırılmadı.

## Gerçek hesap sonucu

| Kayıt | Yerelde önce | Borsada doğrulanan ve yerelde saklanan |
|---|---|---|
| BTCUSDT MARKET BUY, 0,0008 | NEW | FILLED |
| BTCUSDT STOP_MARKET | NEW | FINISHED |
| BTCUSDT TAKE_PROFIT_MARKET | NEW | EXPIRED |

İstemci kimlikleri, mevcut broker kimlikleri, sembol, yön, positionSide, emir tipi ve uygulanabilir miktar/fiyat/koruma alanları eşleştirildi. Normal emrin tam dolumu ve önceki dolum/zaman kaydına göre gerileme olmaması kontrol edildi. closePosition algoritmalarında başlangıç yanıtındaki sıfır miktar, sonradan borsanın belirlediği gerçek miktarla yanlış biçimde çelişki sayılmadı; kayıtlı tetik fiyatı ve koruma kapsamı doğrulandı.

İşlem öncesinde ve sorgular tamamlandıktan sonra hesap ve `positionRisk` envanteri karşılaştırıldı: pozisyon yok, normal veya koşullu açık emir yok. Yerelde aktif yönetilen oturum, yürütülen plan veya bırakılmamış rezerv bulunmadığı kontrol edildi.

Üç güncelleme tek SQLite işlemiyle yapıldı. Yerel kaynak kayıtlar sorgu sırasında değişseydi bütün uygulama duracaktı. Güncelleme öncesi çevrimiçi yedek alındı ve bütünlüğü doğrulandı. Diğer 17 terminal niyet yeniden yazılmadı; genel giriş durdurması aynen korundu.

## Yeniden kullanılabilir komut

```powershell
# Borsada GET ve yerelde salt okunur inceleme:
python -m agentrader service reconcile-history

# Yedekten sonra yalnız doğrulanmış terminal kayıtları yerelde uygula:
python -m agentrader service reconcile-history --apply-local
```

Hesap ön kontrolünün endpoint kapsamı genişletilmedi. Tarihçe için ayrı `HistoryReads` adaptörü GET `/order` ve `/algoOrder` sorgularını destekler; POST/PUT/DELETE engellidir. CLI bütün işlem boyunca mevcut yürütme kilidini tutar.

Bulunamayan, kimliği uyuşmayan, henüz terminal olmayan veya dolumu doğrulanamayan bir emir bu yoldan kapatılmış sayılmaz. Tek bir kayıt bile doğrulanamazsa hiçbir aday yerel güncellemesi uygulanmaz. Bilinmeyen geçmişe varsayımsal FILLED/EXPIRED veya RESOLVED_FLAT yazılmaz. Bir kez doğrulanıp güncellenen kayıtlar tekrar çağrıda yeniden gönderilmez; değişiklik yok sonucu alınır.

## Son durum

Ayrı `acceptance-check` sonucu: **0 pozisyon, 0 açık normal emir, 0 açık koşullu emir**. Yerel niyetler: 10 FILLED, 6 EXPIRED, 2 FINISHED, 1 CANCELED ve önceden mevcut 1 RESOLVED_FLAT. Toplam 20; NEW veya yeni uzlaştırılmamış niyet kalmadı.

Plan incelemesinin önünde kalan yerel engel, eski giriş durdurmasıdır. Gerçek yürütme ayrıca bağımsız kurtarma izleyicisi, taze plan ve plana özel kullanıcı onayı gerektirir. Bu teslim hiçbirini etkinleştirmedi. Gerçek Binance bağlantısı kapalıdır; yeni giriş için kontrollü Demo kabulü tamamlanmış sayılmaz.

## Doğrulama ve kanıtlar

1124 Python testi ve 36 replay senaryosu geçti. Uzlaştırma için 13 yeni test; yanlış kimlik/içerik, sorgulanamayan emir, eksik dolum, eski yanıt, hesap/yerel kayıt değişimi, toplu uygulamada tek hatanın bütününü durdurması, yedeği koruma, aktif oturuma dokunmama ve mutasyon yöntemlerinin engelini kapsar. Arayüz değişmedi.

- İnceleme: `reports/demo-history-verified-preview-20261114.json`
- Uygulama: `reports/demo-history-applied-20261114.json`
- Son kontrol: `reports/demo-after-history-reconciliation-20261114.json`
- Yedek: `reports/history-reconcile-before-c2d8048ec1b24be6a2966995033eef67.sqlite3`
- Testler: `reports/history-reconciliation-python-tests-20261114.log`

Sonraki çalışma, eski güvenlik durdurmasının kaldırılma koşullarını değerlendirmek ve kontrollü Demo plan hazırlığına geçmektir. Otomatik emir gönderimi açılmadı.
