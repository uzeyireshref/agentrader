# Margin emir ve borç işlemleri incelemesi

15 Kasım 2026. Resmi koleksiyonda 69 Margin işlemi bulunuyor. Bu adım temel emir yan etkileri ve borç/geri ödeme sözleşmelerini inceler. Hesap, risk, transfer ve akış incelemeleri ayrıca tamamlanacak.

Mevcut bot planı yalnız USD-M kabul ediyor. Futures isolated teminat desteği, Margin borç/geri ödeme desteğini sağlamıyor.

| Sözleşme | Sonuç |
|---|---|
| Cross/isolated borç ve geri ödeme | asset, isIsolated, amount, type ve imzalı zaman gerekir. Isolated kapsamı symbol ile bağlanır. |
| Emir yan etkileri | NO_SIDE_EFFECT, MARGIN_BUY, AUTO_REPAY, AUTO_BORROW_REPAY ayrı davranışlardır. |
| İptalde geri ödeme | autoRepayAtCancel borç oluşturan emir seçenekleriyle ilişkilidir. |
| Eşzamanlı borç işlemleri | Hesap genelinde bekleyen işlem sonraki varlık isteklerini de engelleyebilir. |
| İşlem teyidi | Emir dolumu ile borcun gerçekten kapanması ayrı sorgulanmalıdır. |

- BORROW_ACK_LOST — Submit borrow then lose reply. Beklenen sonuç Find transaction and outstanding principal before retry.
- REPAY_ACK_LOST — Repayment reply missing. Beklenen sonuç Verify transaction and remaining principal/interest.
- CROSS_ASSET_CONCURRENT — Borrow two assets concurrently. Beklenen sonuç Handle account-wide pending transaction without duplicate financial effect.
- AUTO_REPAY_SILENT — Sell succeeds but repayment incomplete. Beklenen sonuç Report fill and outstanding liability separately.
- PARTIAL_FILL_CANCEL — Auto-borrow order partly fills then cancels. Beklenen sonuç Verify actual inventory and debt after autoRepayAtCancel.
- ISOLATED_SCOPE — Same asset in cross and isolated accounts. Beklenen sonuç Only requested account and symbol change.
- INTEREST_BOUNDARY — Interest accrues while repaying. Beklenen sonuç Residual debt remains visible.
- BORROW_STOCK — Borrowable inventory or maximum changes. Beklenen sonuç Fresh preflight and definite rejection preserve local state.

Kaynaklar [Margin Trade](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/trade) ve [Borrow/Repay](https://developers.binance.com/en/docs/catalog/core-trading-margin-trading/api/rest-api/borrow-repay). Ayrıntılı kayıt margin-core-contract-review.json dosyasındadır.
