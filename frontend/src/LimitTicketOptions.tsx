import {priceMatches,type BotDraft,type LimitOptions} from './botPrototype';

export default function LimitTicketOptions({draft,onChange}:{draft:BotDraft;onChange:(patch:Partial<BotDraft>)=>void}){
 const o=draft.options??{tif:'GTC',stp:'',expires:''};
 const update=(patch:Partial<LimitOptions>)=>onChange({options:{...o,...patch}});
 return <details><summary>Gelişmiş Limit seçenekleri</summary><div className="bot-field-grid">
 <label>Limit fiyat yöntemi<select value={o.priceMatch??''} onChange={e=>update({priceMatch:e.target.value as LimitOptions['priceMatch']})}><option value="">Açık Limit fiyatı</option>{priceMatches.map(p=><option key={p}>{p}</option>)}</select></label>
 <label>Emir süresi<select value={o.tif} onChange={e=>{const tif=e.target.value as LimitOptions['tif'];update({tif,stp:['GTC','IOC','GTD'].includes(tif)?o.stp:'',expires:tif==='GTD'?o.expires:''});}}>{['GTC','IOC','FOK','GTX','GTD'].map(t=><option key={t}>{t}</option>)}</select></label>
 <label>Kendi işlemini önleme · STP<select disabled={!['GTC','IOC','GTD'].includes(o.tif)} value={o.stp} onChange={e=>update({stp:e.target.value as LimitOptions['stp']})}><option value="">Belirtilmedi</option>{['EXPIRE_MAKER','EXPIRE_TAKER','EXPIRE_BOTH'].map(t=><option key={t}>{t}</option>)}</select></label>
 {o.tif==='GTD'&&<label>Son geçerlilik · bilgisayar yerel saati<input type="datetime-local" required value={o.expires} onChange={e=>update({expires:e.target.value})}/></label>}</div><p className="bot-note">FOK ve GTX ile STP seçilemez. GTD zamanı prototipte en az 10 dakika ileride olmalı. priceMatch seçilirse fiyatı emir defteri belirler; referans fiyatı risk kapsamı için kalır, sabit emir fiyatı değildir. Gerçek fiyat ve borsa uygunluğu işlem ön kontrolünde doğrulanacak.</p></details>;
}
