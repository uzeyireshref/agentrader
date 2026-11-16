# Demo stop ve hedef tetiklenme kabulü — 14 Kasım 2026

Kullanıcının küçük Demo işlemleriyle özellik testi yetkisi ve sıradaki adıma geçme talebi kapsamında bu aşama gerçek fiyatla native stop/hedef tetiklenmesini gözlemler. Gerçek Binance bağlantısı açılmaz. Grafik uçtan uca kabulü bu aşamayla tamamlanmış sayılmaz.

## Bütçe ve ön koşullar

Önceki başarılı turdaki başlangıç zararı ve sabit 532,69467203 USDT günlük tavan devralınır. Yeni 3 USDT ek bütçe oluşturulmaz. Başlangıç günlük zarar 529,75247855 olduğundan yaklaşık 2,94219 USDT alan kalmıştır. İşlem başına/toplam açık stop+masraf riski 1 USDT, toplam nominal 60 USDT, tek pozisyon sınırları korunur. Hesap kimliği, önceki başarılı ve boş hesap kanıtı, aynı UTC günü ve değişmemiş bütçe doğrulanır. Sınırlamalar beklenen riski sınırlar; kesin zarar garantisi değildir.

Yeni tur öncesinde boş hesap, terminal geçmiş ve etkin oturum bulunmaması gerçek GET verileriyle doğrulanır. Her senaryo taze tam risk ön kontrolü, sürümlü plan ve yerel yetkilendirme üzerinden yürür. Kaynak veri veya zarar kayıtları değiştirilmez; sahte mum/mark fiyatı kullanılmaz.

## Senaryolar ve başarı tanımı

İki sıralı küçük LONG pozisyon denenir. STOP senaryosunda stop güncel mark fiyatının yaklaşık %0,15 altında, uzak hedef yaklaşık %0,5 üstündedir. TARGET senaryosunda hedef yaklaşık %0,15 üstünde, uzak stop yaklaşık %0,5 alttadır. Fiyatlar gerçek sembol tick adımına yuvarlanır. Giriş ön kontrolü dar aralığın dışına çıkmışsa emir reddedilir; seviyeler sırf test geçsin diye değiştirilmez.

Koruma kurulumundan sonra en fazla 90 saniye salt okunur koşullu emir gözlemi yapılır. Başarı için doğru kimlik/seviye/closePosition/MARK_PRICE içeriği, FINISHED koşullu emir, gerçek actualOrderId ve doğru sembol/yön/miktarda FILLED kapanış emri gerekir. Yalnız NEW koruma, iptal, süre dolumu, botun kendi MARKET çıkışı veya elle yapılan temizlik native tetiklenme başarısı değildir. Diğer koruma tetiklenirse ayrıca OTHER_NATIVE_TRIGGER, fiyat hiç tetiklemezse TIMEOUT_CLEANED kaydedilir.

Koşu sonunda yalnız kayıtlı ve sahipliği doğrulanan pozisyon temizlenir, giriş durdurması korunur. On dakikalık yeni giriş penceresi vardır; pozisyon temizliği bu pencere dolsa da yapılır. Araç süreli ve gözetimlidir; otomatik tekrarlayan test işi başlatılmaz.

## Kod ve kanıt

Araç: scripts/bot/run_demo_trigger_acceptance.py. Altı yeni test küçük bütçeli iki planı, aynı hesap/gün ve değişmeyen tavanı, sahte tetiklenme başarısını engellemeyi, koruma kimliği/içeriğini ve üretilen kapanışın dolum kimliği/miktarını doğrular.

Gerçek koşu raporu: reports/demo-trigger-acceptance-048013076d17.json. İşlem öncesi yedek: reports/demo-trigger-before-048013076d17.sqlite3. Sonuçlar raporun son durumu ve bağımsız son kontrolle değerlendirilmelidir; PREPARING başarı değildir.


## Sonuç: PARTIAL — native tetiklenme henüz kanıtlanmadı

STOP ve TARGET senaryoları 90 saniyelik gözlemde kendi seviyelerine ulaşmadı: ikisi de TIMEOUT_CLEANED. Her iki küçük girişte borsa korumaları aktif gözlendi; süre sonunda sahipliği doğrulanan pozisyonlar kontrollü kapatıldı. Bu sonuç bir native stop/hedef yürütme kabulü değildir. Fiyatı değiştirme, sahte tetiklenme veya sonucu başarılıya çevirme yapılmadı.

Sonradan ayrı GET sorgularıyla yapılan kanıt incelemesi de herhangi bir native tetiklenmiş kapanış bulmadı. reports/demo-trigger-acceptance-048013076d17-evidence.json yalnız okuma kullanır; zaman aşımı gözlemini değiştirmez. Geç tetiklenme yarışı için FINISHED koşullu emir ve gerçek FILLED kapanış kontrolü ayrıca uygulanır. Araç: scripts/bot/verify_demo_trigger_evidence.py.

Bu aşamanın net gerçekleşmiş zarar/masrafı 0,20712983 USDT; önceki küçük turla birlikte toplam net artış 0,26493635 USDT. İlk 529,69467203 USDT günlük zarar kaydı korunur; güncel günlük zarar 529,95960838 USDT, sabit test tavanı 532,69467203 USDT. Yeni zarar bütçesi eklenmedi.

Bağımsız son kontrol 0 pozisyon, 0 normal emir ve 0 koşullu emir doğruladı. Etkin oturum sıfır, giriş durdurması aktiftir. Altı son koruma/kapanış kaydı yedekli ve atomik uzlaştırıldı; toplam 37 yerel niyetin tamamı terminal. Kanıtlar: reports/demo-trigger-final-history-20261114.json ve reports/demo-trigger-final-account-20261114.json. Son kabul kontrolünün BLOCKED olması yeni giriş durdurması ve eksik grafik yürütme yetkisi nedeniyledir; hesapta açık pozisyon anlamına gelmez.

Native tetiklenme maddesi açık kalır. Gelecekteki küçük ve süreli bir gerçek fiyat gözlemiyle tamamlanabilir; bu aşama beklenirken diğer geliştirmeler ve çevrimdışı testler ilerleyebilir. Bu teslimde yeni sürekli arka plan işi veya açık pozisyon bırakılmadı.

Son tam regresyon: 1152 Python testi geçti (reports/demo-trigger-python-tests-20261114.log). Altı yeni test dahil kimlik, bütçe, tetiklenme kanıtı ve salt okunur son inceleme kontrolleri başarılıdır. Bu yazılım testi sonucu gerçek native tetiklenme kanıtının yerine geçmez.
