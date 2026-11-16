# GitHub ve geliştirme aracı değerlendirmesi

15 Kasım 2026. 20 aday commit ile sabitlendi. İncelenen kaynak dosyaları ve hashler repository-assessment.json içinde. Yıldız sayısı seçim ölçütü yapılmadı.

| Repo | Katkı ve kullanım | Yük / sınır | Karar |
|---|---|---|---|
| [HypothesisWorks/hypothesis](https://github.com/HypothesisWorks/hypothesis/tree/9ab0be61aaaa27396fc1bbf4b34e7925cc68d1e2) | Emir/dolum/iptal/restart sıra kombinasyonları. Geliştirme aşamasında stateful test bağımlılığı adayı | Düşük-orta, model ve invariant yazımı gerekir | PREFERRED_DEV_TOOL_CANDIDATE |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean/tree/388713e04209a47d25e48ce2365128fdcb79a46c) | Olay tabanlı tam işlem motoru. Mimari karşılaştırma listesi | Yüksek, C#/Python motor geçişi mevcut amacın dışına taşar | DEFER_FRAMEWORK |
| [binance/binance-api-postman](https://github.com/binance/binance-api-postman/tree/1856d66cecd544191a01d60cdfbd99900d310547) | İstek örnekleri ve endpoint karşılaştırması. Örnekleri araştırma fixture girdisi olarak kullan | Düşük, örnek alan zorunluluğu ayrıca teyit edilir | PRIMARY_REFERENCE |
| [binance/binance-cli](https://github.com/binance/binance-cli/tree/f7c7e4ee5e36f27e7712cfa28c91b1bc2597ae87) | Komut ve argüman kapsamı, ortam profilleri. CLI tasarım karşılaştırması | Çalışma zamanı kurulumunda ek ikili/profil yolu. Kurulmadı | COMMAND_REFERENCE |
| [binance/binance-connector-python](https://github.com/binance/binance-connector-python/tree/6a75e7e5744904380ab0bfbd0bd3433b997010f5) | Parametre, yanıt ve ürün adaptörü sözleşmeleri. Kaynak/model referansı. Runtime geçişi ayrı mimari karar | Kaynak kullanımında düşük, runtime geçişinde orta | PRIMARY_REFERENCE |
| [binance/binance-skills-hub](https://github.com/binance/binance-skills-hub/tree/7d1b1f78d525f9e653b96819f91a549302fda1da) | Ürün komut referansları. binance SKILL.md ve auth/UM/CM referansları okundu | CLI kurmayı ve doğrudan işlem yapmayı merkeze alıyor. Özel geliştirme skilli seçildi | READY_SKILL_NOT_SELECTED |
| [binance/binance-spot-api-docs](https://github.com/binance/binance-spot-api-docs/tree/e5f8489162e79fa1da6d0ea3ded3ce810b3637a0) | Spot filtre, liste, cancel-replace, SOR ve akış sözleşmeleri. Sürümlü sözleşme ve kabul girdisi | Düşük, çalışma zamanı bağımlılığı yok | PRIMARY_REFERENCE |
| [bmoscon/cryptofeed](https://github.com/bmoscon/cryptofeed/tree/2b38da6f256feed158ee59612c159f6353b42592) | Çoklu borsa veri akışı. Veri katmanı büyürse yeniden değerlendir | Orta, emir/hesap mutasyon desteği sağlamaz | DEFER_MARKET_DATA_STACK |
| [ccxt/ccxt](https://github.com/ccxt/ccxt/tree/3eef3f52e3310f5a3b74eba8806d6d7f3ad43005) | Ürün dispatch, hata normalizasyonu ve CM algo kaynak farkı. Bağımsız uygulama karşılaştırması. Doğrudan bot adaptörünü değiştirme kararı yok | Runtime geçişi orta-yüksek, ortak API özel Binance alanlarını gizleyebilir | COMPARISON_REFERENCE |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade/tree/b6d30da09b6745065bf60d464286ebb1b889ccbe) | Strateji/backtest ve hazır bot örnekleri. Şimdilik referans listesi | Tüm motor yüksek, mevcut emir journal yerine geçirilmez | DEFER_STRATEGY_SCOPE |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot/tree/9af100d6822da7d2d0291a906c730ef172284ee2) | In-flight emir ve dolum uzlaştırması. Seçili adaptör ve test referansı | Tüm altyapı yüksek. Eski Testnet host sabiti görüldü | ARCHITECTURE_REFERENCE |
| [hummingbot/skills](https://github.com/hummingbot/skills/tree/01f776e7e2534e1862d163296d7f4fd4988a377b) | Hummingbot geliştirme ve connector keşfi. İki skill içeriği okundu | Hummingbot API/conda/Docker altyapısı gerektiriyor, mevcut projeye katkısı sınırlı | READY_SKILL_NOT_SELECTED |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse/tree/9afc357a5675a44b31dbf5d7c5244112a2c262cb) | Strateji araştırması ve hazır bot altyapısı. Şimdilik referans listesi | Orta-yüksek, mevcut görevde doğrudan açık kapatmıyor | DEFER_STRATEGY_SCOPE |
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader/tree/12982032fb970cabc085f00169c720792c3edecf) | Algo/child kimliği, ürün ayrımı ve recovery. Seçili adaptör kodundan tasarım örneği | Tüm motor yüksek. İncelenen sürüm Python 3.13–3.15/Rust 1.100 ister, proje Python 3.12 | ARCHITECTURE_REFERENCE |
| [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest/tree/5f3ec40b2afb764e0fea112f941ed85523ef4e88) | Kuyruk, gecikme ve limit dolum simülasyonu. İleride gerçekçi yürütme simülasyonu adayı | Orta-yüksek, veri ve simülatör modeli gerekir | DEFER_EXECUTION_SIMULATION |
| [optuna/optuna](https://github.com/optuna/optuna/tree/abf8914d48571120574469575d37c4b0929b7f0f) | Hiperparametre optimizasyonu. Strateji aşamasına bırak | Düşük-orta, işlem yeteneği açığı kapatmaz | DEFER_STRATEGY_SCOPE |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt/tree/9ac1b697166b00911def494cf95937274218aa54) | Vektörlü strateji simülasyonu. Sonraki strateji aşamasına bırak | Orta, mevcut yürütme sözleşmelerini sağlamaz | DEFER_STRATEGY_SCOPE |
| [prometheus/client_python](https://github.com/prometheus/client_python/tree/c0f1bdf39755ee9b028a63a1330c60a2b3455b49) | UNKNOWN emir, uzlaştırma gecikmesi, WS ve limit gözlemi. Geliştirme planında gözlem bağımlılığı adayı | Düşük, servis ve metrik sözleşmesi gerekir | OPTIONAL_DEV_TOOL |
| [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats/tree/d1a214fb906e76f974f45cdccf923b601c67a756) | Performans raporları. Strateji/performans aşamasına bırak | Düşük-orta, borsa komut desteği sağlamaz | DEFER_ANALYTICS |
| [timescale/timescaledb](https://github.com/timescale/timescaledb/tree/fa570b9d607f0804f4b6eae6cc3b42bff69654c3) | Büyük zaman serisi verisi. Ölçek ihtiyacı kanıtlanırsa değerlendir | Yüksek, PostgreSQL servis/taşıma ihtiyacı. Mevcut SQLite journal değiştirilmiyor | DEFER_STORAGE_MIGRATION |

## Seçim

Resmi Python connector birincil model/sözleşme referansı seçildi. Spot belgeleri ve Postman tamamlayıcı kaynak. Hypothesis durum makinesi testleri için tercih edilen geliştirme aracı adayıdır. Runtime bağımlılığı eklenmedi. Nautilus, Hummingbot ve CCXT seçili kod örnekleri olarak değerlendirildi.

## Skill sonucu

Resmi binance skilli CLI kurulumu ve doğrudan işlem yürütme odaklıdır. Hummingbot skilleri kendi API/conda/Docker altyapılarını gerektirir. Bu hazır paketler kurulmadı. Araştırma kaynakları ve mevcut denetimler üzerinden projeye özel agentrader-exchange-development skilli oluşturuldu, doğrulandı ve Codex skill dizinine kuruldu. Bu resmi Binance skilli veya GitHub reposunun aynen kurulumu olarak sunulmaz. Sonraki kullanıcı turunda keşfedilebilir. ccxt-python yeniden kurulmadı.

## Lisans ve güncellik bulguları

GitHub NOASSERTION etiketi kullanılabilir lisans sonucu sayılmadı. Hypothesis kaynak lisansı MPL-2.0, cryptofeed AGPL-3.0-or-later, vectorbt Commons Clause koşullu, Timescale dosya/dizine bağlı karma lisans olarak kaynak dosyalarından incelendi. Bu bulgular lisans uygunluğu onayı değildir. Kod kopyalama kararı ilgili dosyanın koşullarına bağlıdır. Hummingbotta eski Testnet host sabiti, CM algo konusunda resmi SDK/CLI ile güncel uygulama arasında kapsam farkı görüldü. Hiçbir üçüncü taraf motor tam veya güncel Binance desteği kanıtı sayılmadı.
