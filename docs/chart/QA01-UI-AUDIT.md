# QA01 arayüz incelemesi

13 Kasım 2026. [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) kullanılarak değişen etkileşimler incelendi. Kapsamlı WCAG veya fiziksel ekran okuyucu kabulü değildir.

- `frontend/src/drag.ts:17`: gizli belge/blur/Escape sırasında sürükleme iptali ortaklaştırıldı; bekleyen yazım oluşmadığı ve sonraki hareket test edildi.
- `frontend/src/useModalDialog.ts:3`: diyalog bağlıyken kapatma ve açan kontrole odak dönüşü; altı pencerede ortak yaşam döngüsü, dört mount/unmount birim kontrolü.
- `frontend/src/terminal.css:63`: diyalog kaydırma sınırı ve sabit footer için odak boşluğu; 48 Tab adımıyla doğrulandı.
- `frontend/src/App.tsx`: tema effect'inde document colorScheme ve theme-color eşlendi; yerel form kontrolleri açık/koyu temayı izler.
- `frontend/src/LocalEventHistory.tsx:19`: deneme kimliğine isim, autocomplete ve spellcheck politikası eklendi.

18 otomatik raster durumu ve odak kontrolleri başarılıdır. Fiziksel trackpad, native touch ve ekran okuyucu açık kabul maddeleridir. İyileştirmeler mevcut tasarım sistemini korur; vendor yüzeyinin birebir kopyalandığı iddia edilmez.
