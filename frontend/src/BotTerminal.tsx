import {useEffect,useState} from 'react';
import BotBatch from './BotBatch';
import BotAdvanced from './BotAdvanced';
import BotFeedback from './BotFeedback';
import BotOrders from './BotOrders';
import BotSessionControls from './BotSessionControls';
import SingleManagement from './SingleManagement';
import PlanTrailing from './PlanTrailing';
import {addLocalRecord,downloadLocalRecords,useBotRecords,retryLocalRecords} from './botLocalState';
import GridTicket from './GridTicket';
import ExecutionTicket from './ExecutionTicket';
import BotReview from './BotReview';
import PositionActionDialog from './PositionActionDialog';
import type {PositionAction} from './positionPrototype';
import LimitTicketOptions from './LimitTicketOptions';
import {defaultGrid,updateBotDraft} from './botPrototype';

import {draftError,type BotDraft} from './botPrototype';
export {initialBotDraft,type BotDraft} from './botPrototype';
type Props={draft:BotDraft;onDraft:(draft:BotDraft)=>void;onChart:(symbol:string)=>void;compact?:boolean;active?:boolean;onTerminal?:()=>void;symbols?:string[];sourceChanged?:boolean};
const sections=['Genel bakış','Yeni işlem','Pozisyonlar','Emirler','Komut günlüğü','Toplu işlemler','Gelişmiş','Geri bildirim'] as const;
const capabilities=[['Tek pozisyon','SINGLE · Market / Limit · stop ve hedef'],['Grid oturumu','GRID / NEUTRAL · mevcut plan şeması'],['Pozisyon yönetimi','Artır / azalt / kapat / tersine çevir · sahip olunan V2 SINGLE'],['Trailing stop','Native ve yerel takip ayrı yönetilir'],['Toplu işlemler','Oluştur / değiştir / iptal · üye bazında sonuç'],['Hesap ve operasyon','Kaldıraç, marjin, ortak modlar, timer ve geçmiş']];

export default function BotTerminal({draft,onDraft,onChart,compact=false,symbols=[],sourceChanged=false}:Props){
 const [section,setSection]=useState<typeof sections[number]>('Genel bakış');
 const [scenario,setScenario]=useState('Aktif oturum');
 const [review,setReview]=useState<BotDraft|null>(null);
 const [message,setMessage]=useState('');
 const local=useBotRecords();const history=local.records.filter(r=>r.kind==='command');
 useEffect(()=>{setReview(null);},[draft,sourceChanged]);
 const [action,setAction]=useState<string|null>(null);
 const update=(patch:Partial<BotDraft>)=>{onDraft(updateBotDraft(draft,patch));setReview(null);setMessage('');};
 const preview=()=>{const error=sourceChanged?'Grafik kaynağı değişti veya doğrulanamıyor. Seçili planı yeniden aktarın.':draftError(draft);setMessage(error);if(!error)setReview({...draft});};
 const empty=scenario==='Boş hesap';
 const status=scenario==='Belirsiz sonuç'?'Sonuç teyidi bekleniyor':scenario==='Bağlantı kesildi'?'Veri güncel değil':scenario==='Ret'?'Borsa reddi örneği':scenario==='Kısmi dolum'?'Kısmen gerçekleşti':'Koruma etkin';
 const record=(label:string)=>{const saved=addLocalRecord('command',label+' · yalnız prototip',label);setMessage(saved?'Prototip adımı bu tarayıcıya kaydedildi. Borsaya emir gönderilmedi.':'Kayıt saklanamadı.');};
 const showTicket=compact||section==='Genel bakış'||section==='Yeni işlem';
 return <section className={'bot-terminal'+(compact?' bot-compact':'')+(section==='Yeni işlem'?' bot-order-only':'')+(!showTicket?' bot-no-ticket':'')} aria-label="Bot terminali prototipi">
  <header className="bot-toolbar"><div className="bot-title"><h1>{compact?'İşlem paneli':'Bot terminali'}</h1><span className="bot-mode">USD-M Demo</span></div>{!compact&&<details className="bot-scenarios"><summary>Test senaryosu</summary><label>Örnek senaryo<select value={scenario} onChange={e=>{setScenario(e.target.value);setReview(null);setAction(null);setMessage('');}}>{['Aktif oturum','Boş hesap','Kısmi dolum','Belirsiz sonuç','Ret','Bağlantı kesildi'].map(s=><option key={s}>{s}</option>)}</select></label></details>}</header>
  <div className="bot-preview"><span>Önizleme</span><p>Örnek veriler kullanılıyor. Borsaya emir gönderilmez.</p></div>
  {local.error&&<p className="bot-inline-notice" role="alert">{local.error}<button onClick={retryLocalRecords}>Yeniden oku</button></p>}
  {draft.source&&<p className="bot-inline-notice">Grafik planı · r{draft.source.revision} {sourceChanged?'değişti; yeniden aktarın.':'taslağa aktarıldı.'}</p>}
  {!compact&&<>{(section==='Genel bakış'||section==='Pozisyonlar')&&<div className="bot-metrics">{[['Hesap bakiyesi','10.000,00','USDT'],['Açık PnL',empty?'0,00':'+124,80','USDT'],['Aktif oturum',empty?'0':'1','USD-M'],['Açık risk',empty?'0,00':'20,00','USDT']].map(([label,value,unit],i)=><div key={label}><span>{label}</span><strong className={i===1?'bot-positive':undefined}>{value}<small>{unit}</small></strong></div>)}</div>}
  <nav className="bot-tabs bot-main-tabs" aria-label="Bot bölümleri">{sections.map(s=><button key={s} aria-pressed={section===s} onClick={()=>{setSection(s);setMessage('');}}>{s}</button>)}</nav></>}
  <div className="bot-workspace" aria-label="Bot çalışma alanı"><div className="bot-content">
  {!compact&&(section==='Genel bakış'||section==='Pozisyonlar')&&<article className="bot-card"><header><div><h2>Aktif pozisyonlar</h2><p>BTCUSDT · Demo hesap</p></div><span className="bot-tag">SINGLE</span></header>{empty?<p className="bot-empty">Henüz aktif pozisyon yok. Sağdaki formdan ilk işlem taslağınızı oluşturun.</p>:<><div className="bot-position"><div><strong>BTCUSDT</strong><span className="bot-positive">Long · 3x · Isolated</span></div><button onClick={()=>onChart('BTCUSDT')}>Grafikte göster ↗</button></div><dl className="bot-facts"><div><dt>Miktar</dt><dd>0,01 BTC</dd></div><div><dt>Giriş</dt><dd>90.000,00</dd></div><div><dt>Stop / Hedef</dt><dd>88.000 / 94.000</dd></div><div><dt>Durum</dt><dd>{status}</dd></div></dl>{['Belirsiz sonuç','Bağlantı kesildi','Ret'].includes(scenario)&&<p className="bot-warning">{scenario==='Belirsiz sonuç'?'Yeni emir gönderilmez. Mevcut komut kimliğiyle sonuç teyidi gerekir.':scenario==='Ret'?'Ret, dolum olmadığını tek başına kanıtlamaz; gerçekleşen miktar ayrıca incelenir.':'Son bilinen değerler gösteriliyor; işlem hazırlığı doğrulanmadı.'}</p>}<div className="bot-actions">{['Artır','Azalt','Kapat','Tersine çevir','Trailing'].map(a=><button key={a} disabled={['Belirsiz sonuç','Bağlantı kesildi'].includes(scenario)} onClick={()=>setAction(a)}>{a}</button>)}</div></>}</article>}
  {!compact&&section==='Pozisyonlar'&&<BotSessionControls onRecord={record}/>}
  {!compact&&(section==='Genel bakış'||section==='Emirler')&&<BotOrders empty={empty} scenario={scenario} onRecord={record}/>}
  {!compact&&section==='Komut günlüğü'&&<article className="bot-card"><h2>Komut günlüğü</h2><p>Prototip adımları bu tarayıcıda saklanır; bunlar borsa emir günlüğü değildir.</p>{history.length?<ol className="bot-history">{history.map(item=><li key={item.id}><time>{new Date(item.at).toLocaleString('tr-TR')}</time>{item.label}</li>)}</ol>:<p className="bot-empty">Henüz bir prototip adımı onaylanmadı.</p>}<button disabled={!history.length} onClick={()=>downloadLocalRecords(history)}>Günlüğü JSON indir</button></article>}
  {!compact&&section==='Toplu işlemler'&&<BotBatch onRecord={record}/>}
  {!compact&&section==='Geri bildirim'&&<BotFeedback/>}
  {!compact&&section==='Gelişmiş'&&<BotAdvanced onRecord={record}/>}
  {!compact&&section==='Gelişmiş'&&<article className="bot-card"><h2>Yetenekler ve hesap kapsamı</h2><p>Bu kontrollerin gerçek servislere bağlantısı sonraki aşamadır.</p>{capabilities.map(([title,description])=><details key={title}><summary>{title}</summary><p>{description}</p><small>Uygunluk, sahiplik ve hesap bağlamı işlem ön kontrolünde doğrulanacak.</small></details>)}<p className="bot-warning">Ortak pozisyon modu USD-M ve COIN-M kapsamını etkileyebilir. COIN-M finansal yürütmesi destekleniyor anlamına gelmez.</p></article>}
  </div>{showTicket&&<aside className="bot-ticket"><header><h2>Yeni işlem</h2><span className="bot-ticket-status">Emir gönderimi kapalı</span></header>
  <form onSubmit={e=>{e.preventDefault();preview();}}>
  <label>Plan türü<select value={draft.kind} onChange={e=>update({kind:e.target.value as BotDraft['kind'],grid:draft.grid??{...defaultGrid}})}>{['SINGLE','GRID','NEUTRAL'].map(k=><option key={k}>{k}</option>)}</select></label>
  <label>Sözleşme<select value={draft.symbol} onChange={e=>update({symbol:e.target.value})}>{Array.from(new Set([draft.symbol,...symbols,'BTCUSDT','ETHUSDT','SOLUSDT'])).map(s=><option key={s}>{s}</option>)}</select></label>
  <div hidden={draft.kind==='NEUTRAL'} className="bot-direction" role="group" aria-label="İşlem yönü">{(['Long','Short'] as const).map(side=><button type="button" key={side} aria-pressed={draft.side===side} onClick={()=>update({side})}>{side}</button>)}</div>
  {draft.kind!=='SINGLE'?<><GridTicket draft={draft} onChange={update}/><details className="bot-account-settings"><summary>Hesap ve başlatma ayarları</summary><ExecutionTicket draft={draft} onChange={update}/></details><PlanTrailing draft={draft} onChange={update}/><button className="bot-primary" type="submit">Grid planını önizle</button></>:<><label>Emir türü<select value={draft.orderType??'LIMIT'} onChange={e=>update({orderType:e.target.value as BotDraft['orderType']})}><option value="LIMIT">Limit</option><option value="MARKET">Market</option></select></label><div className="bot-field-grid">{([['entry',draft.orderType==='MARKET'||draft.options?.priceMatch?'Risk referans fiyatı · USDT':'Limit fiyatı · USDT'],['amount','İşlem bütçesi · USDT'],['stop','Stop fiyatı · USDT'],['target','Hedef fiyatı · USDT']] as const).map(([key,label])=><label key={key}>{label}<input inputMode="decimal" required value={draft[key]} onChange={e=>update({[key]:e.target.value})}/></label>)}</div><details className="bot-account-settings"><summary>Hesap ve başlatma ayarları</summary><ExecutionTicket draft={draft} onChange={update}/></details><SingleManagement draft={draft} onChange={update}/><PlanTrailing draft={draft} onChange={update}/>{draft.orderType!=='MARKET'&&<LimitTicketOptions draft={draft} onChange={update}/>}<p className="bot-note">Bütçe ve fiyatlar örnektir. Borsa filtreleri, bakiye ve gerçek risk hesabı bu prototipte doğrulanmaz.</p><button className="bot-primary" type="submit">İşlemi önizle</button></>}
  </form>{message&&<p role="status" className="bot-warning">{message}</p>}
  {review&&<section className="bot-review" aria-label="İşlem önizlemesi"><h3>Onay öncesi özet</h3><BotReview draft={review}/><p>Yalnız tasarım akışını onaylar. Emir göndermez.</p><button className="bot-primary" onClick={()=>{if(sourceChanged){setReview(null);setMessage('Grafik kaynağı değişti. Yeniden aktarın.');return;}const err=draftError(review);if(err){setReview(null);setMessage(err);return;}record(review.symbol+' '+review.kind+' '+(review.kind==='NEUTRAL'?'NEUTRAL':review.side)+' taslağı');setReview(null);}}>Prototip adımını onayla</button><button onClick={()=>setReview(null)}>Düzenlemeye dön</button></section>}
  <button className="bot-chart-link" onClick={()=>onChart(draft.symbol)}>Bu sözleşmeyi grafikte aç ↗</button>
  </aside>}</div>
  {action&&['Artır','Azalt','Kapat','Tersine çevir','Trailing'].includes(action)&&<PositionActionDialog action={action as PositionAction} onClose={()=>setAction(null)} onConfirm={summary=>{record(summary);setAction(null);}}/>}
  {action&&!['Artır','Azalt','Kapat','Tersine çevir','Trailing'].includes(action)&&<section className="bot-action-review" aria-label="Eylem önizlemesi"><h2>{action}</h2><p>Bu bir tasarım önizlemesidir. Gerçek uygulamada hesap, oturum, etkilenen emirler ve risk bu adımda doğrulanır.</p><p>{action.includes('iptal')?'İptal pozisyonu kapatmaz ve rezervi kendiliğinden serbest bırakmaz.':action.includes('durdur')?'Yeni girişleri durdurmak açık pozisyonları kapatmaz.':'Bu eylem yalnız desteklenen, sahip olunan oturum kapsamında uygulanabilir.'}</p><button onClick={()=>{record(action);setAction(null);}}>Prototip adımını onayla</button><button onClick={()=>setAction(null)}>Vazgeç</button></section>}
 </section>;
}
