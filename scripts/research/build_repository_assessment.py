"""Pin repository evidence to a task-specific integration decision."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/research/crypto-bot-20261115'
REPORT=ROOT/'reports/crypto-bot-research-20261115/repository-review'

DECISIONS={
 'binance/binance-connector-python':('PRIMARY_REFERENCE','Parametre, yanıt ve ürün adaptörü sözleşmeleri','Kaynak/model referansı. Runtime geçişi ayrı mimari karar','Kaynak kullanımında düşük, runtime geçişinde orta','MIT'),
 'binance/binance-spot-api-docs':('PRIMARY_REFERENCE','Spot filtre, liste, cancel-replace, SOR ve akış sözleşmeleri','Sürümlü sözleşme ve kabul girdisi','Düşük, çalışma zamanı bağımlılığı yok','Repo metadata lisans belirtmiyor. Belge atfı korunur'),
 'binance/binance-api-postman':('PRIMARY_REFERENCE','İstek örnekleri ve endpoint karşılaştırması','Örnekleri araştırma fixture girdisi olarak kullan','Düşük, örnek alan zorunluluğu ayrıca teyit edilir','MIT'),
 'HypothesisWorks/hypothesis':('PREFERRED_DEV_TOOL_CANDIDATE','Emir/dolum/iptal/restart sıra kombinasyonları','Geliştirme aşamasında stateful test bağımlılığı adayı','Düşük-orta, model ve invariant yazımı gerekir','MPL-2.0 kaynak dosyası doğrulandı'),
 'nautechsystems/nautilus_trader':('ARCHITECTURE_REFERENCE','Algo/child kimliği, ürün ayrımı ve recovery','Seçili adaptör kodundan tasarım örneği','Tüm motor yüksek. İncelenen sürüm Python 3.13–3.15/Rust 1.100 ister, proje Python 3.12','LGPL-3.0 metadata, dosya lisansı kopyalamadan önce kontrol'),
 'hummingbot/hummingbot':('ARCHITECTURE_REFERENCE','In-flight emir ve dolum uzlaştırması','Seçili adaptör ve test referansı','Tüm altyapı yüksek. Eski Testnet host sabiti görüldü','Apache-2.0'),
 'ccxt/ccxt':('COMPARISON_REFERENCE','Ürün dispatch, hata normalizasyonu ve CM algo kaynak farkı','Bağımsız uygulama karşılaştırması. Doğrudan bot adaptörünü değiştirme kararı yok','Runtime geçişi orta-yüksek, ortak API özel Binance alanlarını gizleyebilir','MIT kaynak dosyası doğrulandı'),
 'prometheus/client_python':('OPTIONAL_DEV_TOOL','UNKNOWN emir, uzlaştırma gecikmesi, WS ve limit gözlemi','Geliştirme planında gözlem bağımlılığı adayı','Düşük, servis ve metrik sözleşmesi gerekir','Apache-2.0'),
 'binance/binance-cli':('COMMAND_REFERENCE','Komut ve argüman kapsamı, ortam profilleri','CLI tasarım karşılaştırması','Çalışma zamanı kurulumunda ek ikili/profil yolu. Kurulmadı','Repo metadata lisans belirtmiyor'),
 'binance/binance-skills-hub':('READY_SKILL_NOT_SELECTED','Ürün komut referansları','binance SKILL.md ve auth/UM/CM referansları okundu','CLI kurmayı ve doğrudan işlem yapmayı merkeze alıyor. Özel geliştirme skilli seçildi','İncelenen binance skill MIT LICENSE.md içeriyor'),
 'hummingbot/skills':('READY_SKILL_NOT_SELECTED','Hummingbot geliştirme ve connector keşfi','İki skill içeriği okundu','Hummingbot API/conda/Docker altyapısı gerektiriyor, mevcut projeye katkısı sınırlı','Repo metadata lisans belirtmiyor'),
 'freqtrade/freqtrade':('DEFER_STRATEGY_SCOPE','Strateji/backtest ve hazır bot örnekleri','Şimdilik referans listesi','Tüm motor yüksek, mevcut emir journal yerine geçirilmez','GPL-3.0'),
 'jesse-ai/jesse':('DEFER_STRATEGY_SCOPE','Strateji araştırması ve hazır bot altyapısı','Şimdilik referans listesi','Orta-yüksek, mevcut görevde doğrudan açık kapatmıyor','MIT'),
 'polakowo/vectorbt':('DEFER_STRATEGY_SCOPE','Vektörlü strateji simülasyonu','Sonraki strateji aşamasına bırak','Orta, mevcut yürütme sözleşmelerini sağlamaz','Commons Clause koşullu lisans, LICENSE.md doğrulandı'),
 'nkaz001/hftbacktest':('DEFER_EXECUTION_SIMULATION','Kuyruk, gecikme ve limit dolum simülasyonu','İleride gerçekçi yürütme simülasyonu adayı','Orta-yüksek, veri ve simülatör modeli gerekir','MIT'),
 'QuantConnect/Lean':('DEFER_FRAMEWORK','Olay tabanlı tam işlem motoru','Mimari karşılaştırma listesi','Yüksek, C#/Python motor geçişi mevcut amacın dışına taşar','Apache-2.0'),
 'bmoscon/cryptofeed':('DEFER_MARKET_DATA_STACK','Çoklu borsa veri akışı','Veri katmanı büyürse yeniden değerlendir','Orta, emir/hesap mutasyon desteği sağlamaz','AGPL-3.0-or-later LICENSE doğrulandı'),
 'optuna/optuna':('DEFER_STRATEGY_SCOPE','Hiperparametre optimizasyonu','Strateji aşamasına bırak','Düşük-orta, işlem yeteneği açığı kapatmaz','MIT'),
 'ranaroussi/quantstats':('DEFER_ANALYTICS','Performans raporları','Strateji/performans aşamasına bırak','Düşük-orta, borsa komut desteği sağlamaz','Apache-2.0'),
 'timescale/timescaledb':('DEFER_STORAGE_MIGRATION','Büyük zaman serisi verisi','Ölçek ihtiyacı kanıtlanırsa değerlendir','Yüksek, PostgreSQL servis/taşıma ihtiyacı. Mevcut SQLite journal değiştirilmiyor','Apache uyumlu/Timescale lisansları dosya ve dizine bağlı, LICENSE doğrulandı'),
}


def load(p):return json.loads(p.read_text(encoding='utf-8'))


def main():
    metadata=load(REPORT/'metadata.json')['repositories']
    revisions={x['repository']:x for x in load(REPORT/'revisions.json')}
    manifests=load(REPORT/'readme-manifest.json')+load(REPORT/'code-manifest.json')
    rows=[]
    for m in metadata:
        repo=m['repository']
        decision,gap,reuse,cost,license_=DECISIONS[repo]
        evidence=[]
        for s in manifests:
            if s.get('repository')==repo and s['status']==200:
                p=REPORT/s['file']
                evidence.append(dict(path=s['path'],url=s['url'],local_file=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        assert evidence,repo
        rows.append(dict(repository=repo,commit=revisions[repo]['sha'],metadata=m,decision=decision,
                         target_gap=gap,reuse_mode=reuse,integration_cost=cost,license_review=license_,evidence=evidence,
                         installed_runtime_dependency=False))
    out=dict(reviewed_at_utc=datetime.now(timezone.utc).isoformat(),repository_count=len(rows),repositories=rows,
             selected_runtime_replacement=None,
             selected_skill=dict(name='agentrader-exchange-development',kind='PROJECT_SPECIFIC_CREATED_SKILL',
                                 source='tools/skills/agentrader-exchange-development',
                                 installed_path='C:/Users/asus/.codex/skills/agentrader-exchange-development',
                                 primary_upstream_reference='binance/binance-connector-python',
                                 third_party_skill_installed=False,ccxt_python_reinstalled=False))
    (DATA/'repository-assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    md='# GitHub ve geliştirme aracı değerlendirmesi\n\n15 Kasım 2026. 20 aday commit ile sabitlendi. İncelenen kaynak dosyaları ve hashler repository-assessment.json içinde. Yıldız sayısı seçim ölçütü yapılmadı.\n\n'
    md+='| Repo | Katkı ve kullanım | Yük / sınır | Karar |\n|---|---|---|---|\n'
    for r in sorted(rows,key=lambda x:x['repository']):
        link='https://github.com/'+r['repository']+'/tree/'+r['commit']
        md+=f"| [{r['repository']}]({link}) | {r['target_gap']}. {r['reuse_mode']} | {r['integration_cost']} | {r['decision']} |\n"
    md+='\n## Seçim\n\nResmi Python connector birincil model/sözleşme referansı seçildi. Spot belgeleri ve Postman tamamlayıcı kaynak. Hypothesis durum makinesi testleri için tercih edilen geliştirme aracı adayıdır. Runtime bağımlılığı eklenmedi. Nautilus, Hummingbot ve CCXT seçili kod örnekleri olarak değerlendirildi.\n\n'
    md+='## Skill sonucu\n\nResmi binance skilli CLI kurulumu ve doğrudan işlem yürütme odaklıdır. Hummingbot skilleri kendi API/conda/Docker altyapılarını gerektirir. Bu hazır paketler kurulmadı. Araştırma kaynakları ve mevcut denetimler üzerinden projeye özel agentrader-exchange-development skilli oluşturuldu, doğrulandı ve Codex skill dizinine kuruldu. Bu resmi Binance skilli veya GitHub reposunun aynen kurulumu olarak sunulmaz. Sonraki kullanıcı turunda keşfedilebilir. ccxt-python yeniden kurulmadı.\n\n'
    md+='## Lisans ve güncellik bulguları\n\nGitHub NOASSERTION etiketi kullanılabilir lisans sonucu sayılmadı. Hypothesis kaynak lisansı MPL-2.0, cryptofeed AGPL-3.0-or-later, vectorbt Commons Clause koşullu, Timescale dosya/dizine bağlı karma lisans olarak kaynak dosyalarından incelendi. Bu bulgular lisans uygunluğu onayı değildir. Kod kopyalama kararı ilgili dosyanın koşullarına bağlıdır. Hummingbotta eski Testnet host sabiti, CM algo konusunda resmi SDK/CLI ile güncel uygulama arasında kapsam farkı görüldü. Hiçbir üçüncü taraf motor tam veya güncel Binance desteği kanıtı sayılmadı.\n'
    (DATA/'REPOSITORY-SELECTION.md').write_text(md,encoding='utf-8')
    print(json.dumps(dict(repository_count=len(rows),evidence_file_count=sum(len(x['evidence']) for x in rows),selected_skill=out['selected_skill']),ensure_ascii=False))


if __name__=='__main__':main()
