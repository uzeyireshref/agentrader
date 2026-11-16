# Ürünler arası bot karşılaştırması

15 Kasım 2026. 555 REST kaydı işlem ailesi, parametre listesi, kaynak sürümü, adaptör kanıtı ve kabul gereksinimleriyle eşleştirildi. Yöntem, kaynak taraması ve mevcut USD-M ürün kapısına dayanır. Tam parametre anlam incelemesi bekliyor.

| Ürün | Kayıt | Adaptör yolu | Ürün/yol incelemesi gereken |
|---|---|---|---|
| Binance Convert API.json | 9 | 0 | 9 |
| Binance Derivatives Trading COIN Futures API.json | 64 | 0 | 64 |
| Binance Derivatives Trading Options API.json | 44 | 0 | 44 |
| Binance Derivatives Trading Portfolio Margin API.json | 102 | 0 | 102 |
| Binance Derivatives Trading Portfolio Margin Pro API.json | 24 | 0 | 24 |
| Binance Derivatives Trading USDS Futures API.json | 95 | 39 | 56 |
| Binance Margin Trading API.json | 69 | 0 | 69 |
| Binance Spot API.json | 48 | 0 | 48 |
| Binance Sub Account API.json | 50 | 0 | 50 |
| Binance Wallet API.json | 50 | 0 | 50 |

## Ürün modellerinin uygulama etkisi

Spot için serbest/kilitli envanter, quoteOrderQty, emir listesi bacakları ve cancel-replace kısmi sonuçları gerekir. Margin için borç, faiz, geri ödeme ve emir yan etkileri ayrı finansal kayıtlardır. COIN-M için kontrat çarpanı ve coin cinsi PnL gerekir. Options için vade, prim, egzersiz/uzlaşma, MMP ve underlying kapsamlı iptal gerekir. Portfolio Margin için papi hesap/teminat modeli ve ürün bacakları gerekir. Convert için teklif geçerliliği ve kabul sonrası durum sorgusu gerekir. Transferlerde gönderim sonucu bilinmiyorsa hareket geçmişinden teyit gerekir. Bunlar resmi koleksiyonların alan ve işlem ailelerinden türetilen tasarım gereksinimleridir. Her ürünün parametre sınırları ayrıca doğrulanmalıdır.

Mevcut bot planı demo/binance/USD-M ve USDT sembollerine bağlıdır. Bu nedenle diğer ürünlerde ortak isimli emir fonksiyonlarının bulunması uçtan uca destek sağlamaz.
