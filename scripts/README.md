# Geliştirme ve doğrulama komutları

| Dizin | Kapsam |
| --- | --- |
| [bot](bot/) | Demo kabulü, kontrollü kapanış, izleme ve görev hazırlığı |
| [chart](chart/) | Grafik ve arayüz doğrulamaları, fixture, replay, sürüm adayları |
| [integration](integration/) | Bot–grafik arayüzü ve uçtan uca kabul |
| [maintenance](maintenance/) | Proje yapısı, genel regresyon ve yerel API kontrolü |
| [archive](archive/) | Çalıştırılmayan tarihsel tasarım örnekleri |

Komutları proje kökünden `python scripts/<alan>/<dosya>.py` ile çalıştırın. `python -m scripts.<alan>.<dosya>` biçimi de desteklenir. Betikler doğrudan başlatıldığında proje kökünü import yoluna ekler. TypeScript araçlarında bağımlılıklar `frontend/node_modules` üzerinden kullanılır.

Genel kontroller:

```powershell
python scripts/maintenance/check_project_layout.py
python scripts/maintenance/validate_development.py
python scripts/maintenance/check_local_api.py
```

Bot ve entegrasyon dizinlerindeki komutların bir kısmı açık işlem yetkisiyle Demo hesabına yazabilir. Genel çevrimdışı doğrulama için yukarıdaki bakım komutlarını kullanın. Taşıma, mevcut emir/onay koşullarını değiştirmez.
