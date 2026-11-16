"""Consolidate findings without treating source extraction as execution proof."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/research/crypto-bot-20261115'

FINDINGS=[
 ('F01','Ürün/hesap/ortam kimliği','Ortak istek ve journal kimliği USD-M dışı ürünleri kapsamalı','Aynı sembol/kimlik başka ürün veya hesapta yanlış kayda bağlanmaz','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F02','Genel kullanıcı işlem yüzeyi','Planlı SINGLE/GRID dışında keyfi borsa talimatları için normal giriş sınırlı','İstenen işlem normal komuttan doğrulama, yürütme ve sonuç teyidine ulaşır','WORKFLOW-CAPABILITY-REVIEW.md'),
 ('F03','TIF/priceMatch/STP/response seçimi','Yardımcı validator ve standart plan seçenekleri farklı. ACK/RESULT reddediliyor','Seçilen alanlar korunur, çelişen kombinasyon gerekçeyle reddedilir','WORKFLOW-CAPABILITY-REVIEW.md'),
 ('F04','Trailing callback sınırı','7.5/10/20 yerel reddi, güncel UM algo şemasıyla fark','Ürünün güncel aralığı desteklenir, aralık dışı reddedilir','SYMBOL-SCENARIO-COVERAGE.md'),
 ('F05','Borsa trailing ile yerel stop yenileme ayrımı','native_stop aynı native trailing emir sözleşmesi değil','Kullanıcı talimatı doğru yerel/native modele açıkça bağlanır','WORKFLOW-CAPABILITY-REVIEW.md'),
 ('F06','Artırma/azaltma/yön değiştirme','SINGLE scale-in/reentry ve allow_reverse sınırları','Gerçek pozisyon miktarı, sahiplik ve riskle açık talimat uygulanır','WORKFLOW-CAPABILITY-REVIEW.md'),
 ('F07','İptal kapsamları ve zamanlayıcı','Genel normal/algo iptali ve countdown yolları eksik','Seçili/sembol/hesap/bot kapsamı ayrı, dolum yarışı uzlaştırılır','WORKFLOW-CAPABILITY-REVIEW.md'),
 ('F08','Batch işlem çeşitliliği','Native create LIMIT/GTC akışına bağlı','Geçerli ürün/emir kombinasyonu ve her alt sonuç bağımsız teyit edilir','FAILURE-RECOVERY-REVIEW.md'),
 ('F09','Dinamik kaldıraç basamağı','Sabit 125 sınırı mevcut','Hesap/sembol leverageBracket ile uygunluk ölçülür','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F10','Dinamik fiyat bandı','PERCENT_PRICE dışı 527 örnek validatorca teklif edildi','Güncel fiyat referansı ve filtre bandı yerel kontrolde değerlendirilir','SYMBOL-SCENARIO-COVERAGE.md'),
 ('F11','Hemen tetiklenen koşullu emir','527 BUY STOP örneği mevcut markın altında teklif edildi','Emir türü/yönü/workingType için tetik uygunluğu değerlendirilir','SYMBOL-SCENARIO-COVERAGE.md'),
 ('F12','Yeni sembol risk/limit filtreleri','POSITION_RISK_CONTROL ve order/list/amend limitleri kapsamı','Bilinmeyen veya kısıtlayıcı filtre izin verilmiş kabul edilmez','SYMBOL-SCENARIO-COVERAGE.md'),
 ('F13','UM/CM ortak hesap modu','Tek ürün okuması ortak dualSidePosition etkisini kapsamaz','İki ürünün aktif emir/pozisyonu ayar değişimi öncesi değerlendirilir','FAILURE-RECOVERY-REVIEW.md'),
 ('F14','Ortak rate-budget modeli','Host cooldown ortak IP/UID/order kotası değildir','Birleşik UM/CM ve ürün özel limitlerinde toplam bütçe korunur','FAILURE-RECOVERY-REVIEW.md'),
 ('F15','Geçmiş bütünlüğü','Tüm emir/algo/geçmiş yolları ve saklama sınırları kapsanmıyor','Süre penceresi ve sayfalama eksik sonucu tam başarı yapmaz','WORKFLOW-CAPABILITY-REVIEW.md'),
 ('F16','Spot ürün desteği','Normal/SOR/listeler/amend/pegged/iceberg için ürün akışı yok','Spot bakiye, filtre, parent/child ve sonuç muhasebesi kabul edilir','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F17','Margin ürün desteği','Borç/faiz/cross/isolated/listeler/repay süreci yok','Anapara/faiz, yan etki ve hesap riski uzlaştırılır','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F18','COIN-M miktar ve muhasebe','Inverse kontrat/coin teminat/vade desteği yok','Kontrat ve coin birimleri, PnL/funding/teslim doğru tutulur','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F19','CM algo geçişi ve ek envanter','Üç resmi ek ve üç uygulama adayı, tam alan/sınır çelişkisi','Resmi tam sözleşme veya belirli kontrollü kabul kapısı sağlanır','SOURCE-CONFLICT-RESOLUTIONS.md'),
 ('F20','Options ürün desteği','Prim/vade/exercise/MMP/block-trade süreçleri yok','İlgili hesap ve olay şemaları, kullanım ve nakit akışı kabul edilir','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F21','Portfolio Margin/Pro/SPAN','Yerel portfolio.py bu ürün adaptörü değil','Hesap modeline uygun birleşik teminat/borç/risk/işlem yönlendirme','PORTFOLIO-MARGIN-REVIEW.md'),
 ('F22','Convert yaşam döngüsü','Teklif/kabul/limit/sonuç komutu yok','Teklif süresi, cüzdan ve dönüşüm sonucu uzlaştırılır','WALLET-CONVERT-REVIEW.md'),
 ('F23','Wallet süreçleri','Transfer/dust/deposit/withdraw/Travel Rule akışları yok','Ağ/adres/memo/ücret/izin ve hareket geçmişi teyit edilir','SOURCE-CONFLICT-RESOLUTIONS.md'),
 ('F24','Sub Account süreçleri','Master/sub/managed yetki, transfer ve pozisyon taşıma yok','İki hesap etkisi ve operasyon özel VIP/ürün koşulları teyit edilir','PRODUCT-CONTRACT-DECISIONS.md'),
 ('F25','WS API komut arabirimi','Olay dinlemek WS emir API desteği değildir','83 kaynak komutun gerekli alt kümesi normal talimat ve sonuç takibine bağlanır','DETAILED-CONTRACT-COMPARISON.md'),
 ('F26','Ortam ve hesap kabulü','Public GET başarısı private işlem uygunluğu değildir','Ürün/ortam/anahtar/hesap uygunluğu ayrı kabul kanıtı taşır','ENVIRONMENT-REVIEW.md'),
 ('F27','Kaynak şeması belirsizlikleri','Options iç olay alanları, CM algo ve transfer örneği açık','Belirli bilinmeyen alan için kaynak veya dış kabul sonucu kaydedilir','SOURCE-CONFLICT-RESOLUTIONS.md'),
 ('F28','Yeni ürünlerde recovery','Mevcut USD-M kanıtları diğer ürünlere otomatik taşınamaz','Lost reply, restart ve kısmi sonuç her ilgili ürün ailesinde kanıtlanır','FAILURE-RECOVERY-REVIEW.md'),
 ('F29','İşlem gözlemi','UNKNOWN/WS/uzlaştırma/limit metriklerinin ortak görünümü geliştirilmeli','Belirsiz işlem ve recovery gecikmesi kullanıcıya ve operasyon kaydına yansır','REPOSITORY-SELECTION.md'),
 ('F30','Durum makinesi test kapsamı','Mevcut testler bütün yeni sıra kombinasyonlarını kapsamaz','Gerektiğinde model tabanlı testler anlamlı muhasebe/tekilleştirme invariantlarını sınar','REPOSITORY-SELECTION.md'),
 ('F31','Snapshot tutarsızlığı','SXP 62 ölçümü veriden bloklu','Tutarlı yeni filtre/fiyat çifti bulunursa ölçülür, önceki engel korunur','SYMBOL-SCENARIO-COVERAGE.md'),
 ('F32','Sürüm ve kanıt güncelliği','555 ortak şema eşleşmesi tam canlı sözleşme kanıtı değil','Kaynak/ortam/kod sürümü değişiminde ilgili kanıt yeniden değerlendirilir','SOURCE-CONFLICT-RESOLUTIONS.md'),
 ('F33','USD-M eksik REST yolları','55 başlangıç işleminde adaptör yolu yok','Her seçilen yol normal komut ve uygun yaşam döngüsüyle tamamlanır','EXCHANGE-OPERATIONS.md'),
 ('F34','Diğer istemcide piyasa veri yolu','Bir yol başka istemcide bulunuyor','Ortak ürün/ortam/veri sözleşmesine bağlanır, route varlığı yürütme desteği sayılmaz','WORKFLOW-CAPABILITY-REVIEW.md'),
]


def main():
    support=json.loads((DATA/'operation-support-audit.json').read_text(encoding='utf-8'))
    product_finding={'spot':'F16','margin_trading':'F17','derivatives_trading_coin_futures':'F18',
      'derivatives_trading_options':'F20','derivatives_trading_portfolio_margin':'F21','derivatives_trading_portfolio_margin_pro':'F21',
      'convert':'F22','wallet':'F23','sub_account':'F24'}
    mapped=[]
    for op in support['operations']:
        p=op['product']
        if p=='derivatives_trading_usds_futures':
            findings=['F33'] if op['support']=='MISSING_PRODUCT_OR_ROUTE' else (['F34'] if op['support']=='OTHER_CLIENT_REFERENCE' else ['F02'])
        else:findings=[product_finding[p],'F01','F26','F28']
        mapped.append(dict(operation_id=op['operation_id'],product=p,method=op['method'],path=op['path'],findings=findings,
                           support=op['support'],contract_evidence='SOURCE_EXTRACTED_AND_PRODUCT_REVIEWED',exchange_acceptance='NOT_RUN'))
    source='https://developers.binance.com/en/docs/products/derivatives-trading-coin-futures/Important-CM-UM-Integration-Notice'
    extra=[dict(id=f'ADD-CM-{i:03d}',method=m,path=p,product='derivatives_trading_coin_futures',
                evidence='OFFICIAL_NOTICE_ROUTE',source=source,fields='PARTIAL_NOTICE_CONTRACT',finding='F19',exchange_acceptance='NOT_RUN')
           for i,(m,p) in enumerate([('POST','/dapi/v1/algoOrder'),('GET','/dapi/v1/openAlgoOrders'),('DELETE','/dapi/v1/algoOrder')],1)]
    candidates=[dict(id=f'CAND-CM-{i:03d}',method=m,path=p,evidence='IMPLEMENTATION_ONLY_NOT_OFFICIAL_CONTRACT',
                    source='https://github.com/ccxt/ccxt/blob/3eef3f52e3310f5a3b74eba8806d6d7f3ad43005/python/ccxt/binance.py',finding='F19')
                for i,(m,p) in enumerate([('GET','/dapi/v1/algoOrder'),('GET','/dapi/v1/allAlgoOrders'),('DELETE','/dapi/v1/algoOpenOrders')],1)]
    rows=[dict(id=id,title=title,finding=detail,acceptance=acceptance,source_document=doc,
               classification='EXTERNAL_DATA_ACCEPTANCE' if id=='F31' else ('RESEARCH_OR_ACCOUNT_GATE' if id in ('F19','F26','F27','F32') else 'DEVELOPMENT_REQUIREMENT'),
               operation_ids=[x['operation_id'] for x in mapped if id in x['findings']]) for id,title,detail,acceptance,doc in FINDINGS]
    payload=dict(reviewed_at_utc=datetime.now(timezone.utc).isoformat(),baseline_count=555,official_supplements=extra,
                 confirmed_route_inventory_count=558,implementation_candidates=candidates,candidates_in_confirmed_count=False,
                 finding_count=len(rows),findings=rows,operation_mapping=mapped,unmapped_baseline_operations=[],
                 source_contract_completeness='BASELINE_EXTRACTED_SUPPLEMENTAL_FIELDS_PARTIAL',financial_execution_acceptance='NOT_RUN')
    (DATA/'final-gap-register.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    text='# Birleşik eksik ve kabul gereksinimleri\n\n15 Kasım 2026. 34 bulgu ailesi. Bu aileler bağımsız hata sayısı veya hazır geliştirme iş paketi değildir. 555 başlangıç işlemi bir aileye bağlı, 3 resmi ek ve 3 uygulama adayı ayrı kaydedildi.\n\n'
    text+='| Kimlik | Bulgu | Kabul ölçütü |\n|---|---|---|\n'
    for row in rows:text+=f"| {row['id']} | {row['title']}: {row['finding']} | {row['acceptance']} |\n"
    text+='\n## Kapsam hesabı\n\nBaşlangıç 555 REST: 39 izinli adaptör yolu, 1 diğer istemci referansı, 515 ürün/yol açığı. Resmi CM duyurusundaki 3 yeni yol ile kayıtlı resmi yol envanteri 558. Bu üç ekte tam alan sözleşmesi henüz yok. CCXT kaynaklı üç aday bu sayıya eklenmedi. 83 WS API komutu ayrı arabirim envanteridir. Bütün API veya hizmet ürünlerinin toplamı olarak yorumlanamaz.\n\n'
    text+='## Geliştirme planına geçiş girdisi\n\nBu dosya neyin değişmesi ve hangi sonuçla kabul edilmesi gerektiğini gösterir. Sıralama, paket bağımlılıkları, veri migrationı ve efor tahmini sonraki geliştirme planının işidir. F19/F26/F27 kapsamındaki kabul kapıları çözülmeden ilgili ürün için tam destek sözü verilmez. Mevcut USD-M çekirdeği ve diğer ürünler için kapsam kararları ayrı tutulabilir.\n'
    (DATA/'FINAL-GAP-REGISTER.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(baseline_mapped=len(mapped),findings=len(rows),confirmed_inventory=558,implementation_candidates=len(candidates))))


if __name__=='__main__':main()
