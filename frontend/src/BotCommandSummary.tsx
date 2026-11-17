import type {CommandResult} from './botApi';

const names:Record<string,string>={SET_LEVERAGE:'Kaldıracı değiştir',SET_MARGIN_TYPE:'Teminat modunu değiştir',SET_POSITION_MODE:'Pozisyon modunu değiştir',SET_MULTI_ASSETS_MODE:'Çoklu varlık modunu değiştir',SET_FEE_BURN:'Komisyon indirimi ayarını değiştir',INCREASE_POSITION:'Pozisyonu artır',REDUCE_POSITION:'Pozisyonu azalt',CLOSE_POSITION:'Pozisyonu kapat',REVERSE_POSITION:'Pozisyonu kapat ve ters yön planını uygula',CREATE_NATIVE_TRAILING:'Borsada takip stopu oluştur',QUERY_NATIVE_TRAILING:'Takip stopunu sorgula',CANCEL_NATIVE_TRAILING:'Takip stopunu iptal et',CANCEL_SELECTED_ORDERS:'Seçili emirleri iptal et',CANCEL_SYMBOL_ORDERS:'Sözleşmedeki emirleri iptal et',CANCEL_ACCOUNT_ORDERS:'Hesap genelinde emir iptali',SET_CANCEL_TIMER:'Sözleşme geneli iptal zamanlayıcısı kur',REFRESH_CANCEL_TIMER:'Mevcut zamanlayıcıya heartbeat gönder',DISABLE_CANCEL_TIMER:'İptal zamanlayıcısını kapat',BATCH_CREATE_ORDERS:'Seçili planları toplu gönder',BATCH_AMEND_ORDERS:'Seçili emirleri toplu değiştir',BATCH_CANCEL_ORDERS:'Seçili normal emirleri toplu iptal et',CREATE_HISTORY_EXPORT:'Geçmiş dışa aktarma işi oluştur'};
const labels:Record<string,string>={leverage:'Kaldıraç',margin_type:'Teminat modu',enabled:'Ayar',quantity:'Miktar · baz varlık',price_floor:'Onaylanan alt fiyat',price_ceiling:'Onaylanan üst fiyat',activate_price:'Aktivasyon fiyatı',callback_rate:'Callback · %',working_type:'Tetik referansı',countdown_ms:'İptal geri sayımı',heartbeat_ms:'Heartbeat aralığı',lease_ms:'Worker kiralaması',include_foreign:'Diğer istemcilerin emirleri',next_plan_id:'Karşı yön planı',next_version:'Plan sürümü',kind:'Geçmiş ailesi',start_ms:'Başlangıç · yerel saat',end_ms:'Bitiş · yerel saat',timer_id:'Zamanlayıcı kimliği',create_command_id:'Kaynak oluşturma komutu',source_command_id:'Kaynak dışa aktarma komutu'};
const enumNames:Record<string,string>={ISOLATED:'İzole',CROSSED:'Çapraz',MARK_PRICE:'Mark fiyatı',CONTRACT_PRICE:'Sözleşme fiyatı'};
function object(value:unknown):Record<string,unknown>{return value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};}
export function scopeText(scope:Record<string,unknown>):string{
 if(scope.account_wide===true)return 'Hesabın tamamı';
 if(Array.isArray(scope.affected_products))return scope.affected_products.map(String).join(' + ')+' hesapları';
 if(Array.isArray(scope.symbols))return scope.symbols.map(String).join(', ');
 return typeof scope.symbol==='string'?scope.symbol:'Kapsam ayrıntılarını kontrol edin';
}
export default function BotCommandSummary({command}:{command:CommandResult}){
 const {operation,scope,parameters:p}=command.request;
 const facts:[string,string][]=[];
 for(const [key,value] of Object.entries(p)){
  if(!labels[key])continue;
  let text=typeof value==='boolean'?(value?'Dahil / açık':'Hariç / kapalı'):String(value);
  if(key==='enabled'&&operation==='SET_POSITION_MODE')text=value?'Hedge · iki yön':'Tek yön';
  else if(typeof value==='string')text=enumNames[value]??value;
  if(['countdown_ms','heartbeat_ms','lease_ms'].includes(key)&&typeof value==='number')text=String(value/1000)+' saniye';
  if(['start_ms','end_ms'].includes(key)&&typeof value==='number'&&Number.isFinite(value))text=new Date(value).toLocaleString('tr-TR');
  facts.push([labels[key],text]);
 }
 const reduction=object(p.reduction);
 if(reduction.kind)facts.push(['Azaltma',String(reduction.value)+(reduction.kind==='PERCENT'?' %':' baz varlık')]);
 const plans=Array.isArray(p.plans)?p.plans.map(object):[];
 const targets=Array.isArray(p.targets)?p.targets.map(object):[];
 const changes=Array.isArray(p.changes)?p.changes.map(object):[];
 return <section className="bot-command-summary" aria-label="Onaylanacak işlem özeti"><h3>{names[operation]??operation}</h3><dl className="bot-review-facts"><div><dt>Etki alanı</dt><dd>{scopeText(scope)}</dd></div>{facts.map(([label,text])=><div key={label}><dt>{label}</dt><dd>{text}</dd></div>)}</dl>
 {scope.account_wide===true&&<p className="bot-warning">Bu işlem yalnız seçili sözleşmeyle sınırlı değildir; hesabın tamamını etkiler.</p>}
 {Array.isArray(scope.affected_products)&&<p className="bot-warning">Bu hesap ayarı USD-M ve COIN-M ürünlerini birlikte etkiler.</p>}
 {['CLOSE_POSITION','REVERSE_POSITION'].includes(operation)&&<p className="bot-warning">Mevcut pozisyonun kapanışı söz konusudur.{operation==='REVERSE_POSITION'?' Kapanış teyidinden sonra ayrıca seçili karşı yön planının koşulları denetlenir.':''}</p>}
 {operation==='SET_CANCEL_TIMER'&&<p className="bot-warning">Zamanlayıcı sözleşme genelindedir. Worker durursa borsadaki geri sayım devam eder; bu bir pozisyon kapatma komutu değildir.</p>}
 {plans.length>0&&<><h3>Seçili plan sürümleri · {plans.length}</h3><ul>{plans.map((plan,i)=><li key={i}>{String(plan.plan_id)} · sürüm {String(plan.version)}</li>)}</ul><p>Her üyenin borsa sonucu ayrı değerlendirilir; toplu yanıt tüm emirlerin dolduğu anlamına gelmez.</p></>}
 {targets.length>0&&<><h3>İptal kapsamındaki emirler · {targets.length}</h3><ul>{targets.map((target,i)=><li key={i}>{target.namespace==='ALGO'?'Koşullu / Algo':'Normal'} · {String(target.client_id)}</li>)}</ul></>}
 {changes.length>0&&<><h3>Değişecek emirler · {changes.length}</h3><ul>{changes.map((change,i)=><li key={i}>{String(change.client_id)} · miktar {String(change.quantity)} · fiyat {String(change.price)}</li>)}</ul></>}
 </section>;
}
