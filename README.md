# Agentrader

Binance USD-M Demo bot çekirdeği ve yerel grafik terminali.

## Proje yapısı

| Konum | İçerik |
| --- | --- |
| [agentrader/bot](agentrader/bot/) | Emir, risk, plan, grid, hesap ve kurtarma çekirdeği |
| [agentrader/chart](agentrader/chart/) | Grafik verisi, çizimler, göstergeler, alarmlar ve replay |
| [agentrader/integration](agentrader/integration/) | Grafik bağlamından bot önizlemesi ve onaylı yürütmeye geçiş |
| [agentrader/shared](agentrader/shared/) | Yapılandırma, borsa erişimi, veri, kilit ve kalıcı durum |
| [agentrader/cli](agentrader/cli/) | Komut satırı girişleri |
| [agentrader/api](agentrader/api/) · [application](agentrader/application/) | HTTP ve uygulama servisleri |
| [frontend](frontend/) | React/TypeScript grafik arayüzü ve arayüz testleri |
| [tests](tests/) | Python regresyonları ve ortak test yardımcıları |
| [scripts](scripts/) | Bot, grafik, entegrasyon ve bakım komutları |
| [docs](docs/) | Alanlara ayrılmış planlar, sözleşmeler ve teslim geçmişi |

## Çalıştırma

Proje kökünde:

```powershell
python -m pip install -e ".[web-test]"
python -m agentrader --help
python -m agentrader web --help
python -m agentrader web serve
```

Arayüz geliştirme için ayrı terminalde:

```powershell
cd frontend
npm ci
npm run dev
```

Üretim arayüzü `frontend` içinde `npm run build` ile `agentrader/web_assets` dizinine derlenir. Python paket verileri ve API'nin bu dizini kullanması korunmuştur. Çalışma verileri `data/`, yerel kanıtlar `reports/`, günlükler `logs/` altında kalır. Yerel risk profili `risk-demo.json` ve `.env` kökteki mevcut yollarını kullanır.

## Doğrulama

```powershell
python -m unittest discover -s tests
python scripts/maintenance/check_project_layout.py
python scripts/chart/build_binding_evidence.py
python scripts/chart/run_chart_p7.py
cd frontend
npm test
npm run build
```

## Belgeler

- [Belge dizini](docs/README.md)
- [Bot belgeleri](docs/bot/README.md)
- [Grafik planı](docs/chart/PLAN.md)
- [Bot–grafik entegrasyon planı](docs/integration/history/46-BOT-GRAFIK-ORTAK-ARAYUZ-VE-CIZIM-ADAPTORU-GELISTIRME-PLANI.md)
- [Düzenleme analizi ve doğrulama](docs/project/REORGANIZATION.md)
- [Önceki geliştirme günlüğü ve ayrıntılı kullanım](docs/project/DEVELOPMENT-HISTORY.md)

REA araçları ve yüklü skill dizinleri bu düzenlemenin dışında tutulmuştur.
