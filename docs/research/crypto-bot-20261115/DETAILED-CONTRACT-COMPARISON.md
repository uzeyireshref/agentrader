# Sürümlü işlem sözleşmesi karşılaştırması

Otomatik SDK çıkarımı ile alan ve kaynak karşılaştırmasıdır. Borsa kabulü veya tek başına semantik inceleme tamamlanması değildir.

SDK commit: `6a75e7e5744904380ab0bfbd0bd3433b997010f5`. Başlangıç 555 REST kaydı. Ek SDK REST 0. WS/akış metodu 83. Yanıt/model sınıfı 2010.

| Ürün | Başlangıç | SDK eşleşmesi | Eşleşmeyen |
|---|---:|---:|---:|
| convert | 9 | 9 | 0 |
| derivatives_trading_coin_futures | 64 | 64 | 0 |
| derivatives_trading_options | 44 | 44 | 0 |
| derivatives_trading_portfolio_margin | 102 | 102 | 0 |
| derivatives_trading_portfolio_margin_pro | 24 | 24 | 0 |
| derivatives_trading_usds_futures | 95 | 95 | 0 |
| margin_trading | 69 | 69 | 0 |
| spot | 48 | 48 | 0 |
| sub_account | 50 | 50 | 0 |
| wallet | 50 | 50 | 0 |

## Alan farkı veya kaynak uyuşmazlığı olan kayıtlar

| Kimlik | İşlem | Sonuç | Postman tarafında | SDK tarafında |
|---|---|---|---|---|
