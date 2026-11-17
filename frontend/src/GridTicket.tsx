import {defaultGrid,type BotDraft} from './botPrototype';

export default function GridTicket({draft,onChange,errors={},errorId="grid"}:{draft:BotDraft;onChange:(patch:Partial<BotDraft>)=>void;errors?:Record<string,string>;errorId?:string}){
 const g=draft.grid??defaultGrid;const neutral=draft.kind==='NEUTRAL';
 const grid=(patch:Partial<typeof g>)=>onChange({grid:{...g,...patch}});
 const input=(name:string,value:string,change:(value:string)=>void,numeric=false)=><><input name={name} autoComplete="off" required inputMode={numeric?'numeric':'decimal'} value={value} aria-invalid={Boolean(errors[name])} aria-describedby={errors[name]?`${errorId}-${name}`:undefined} onChange={e=>change(e.target.value)}/>{errors[name]&&<small className="bot-field-error" id={`${errorId}-${name}`}>{errors[name]}</small>}</>;
 return <fieldset className="bot-grid-fields"><legend>{neutral?'İki yönlü neutral grid':'Yönlü grid'} kurulumu</legend>
 <p className="bot-note">{neutral?'Hedge modu gerekir; hesap modu otomatik değiştirilmez. Hedefler hücre çıkışlarıyla tanımlanır, trailing desteklenmez.':'Piyasa başlangıcı ve tek son hedef kullanılır; LIMIT başlangıç desteklenmez.'}</p>
 <div className="bot-field-grid">{([['lower','Alt bant · USDT'],['upper','Üst bant · USDT'],['intervals',neutral?'Aralık sayısı · 2–20':'Aralık sayısı · 2–100']] as const).map(([key,label])=><label key={key}>{label}{input('grid.'+key,g[key],value=>grid({[key]:value}),key==='intervals')}</label>)}
 <label>Aralık türü<select value={g.spacing} onChange={e=>grid({spacing:e.target.value as typeof g.spacing})}><option value="ARITHMETIC">Aritmetik</option><option value="GEOMETRIC">Geometrik</option></select></label>
 <label>{neutral?'Merkez / referans':'Referans fiyatı'} · USDT{input('entry',draft.entry,value=>onChange({entry:value}))}</label>
 <label>{neutral?'Alt global stop':'Stop'} · USDT{input('stop',draft.stop,value=>onChange({stop:value}))}</label>
 {neutral?<><label>Üst global stop · USDT{input('grid.upperStop',g.upperStop,value=>grid({upperStop:value}))}</label><label>LONG bütçe payı · %{input('grid.longPercent',g.longPercent,value=>grid({longPercent:value}))}</label><p className="bot-note">SHORT payı: {Number.isFinite(Number(g.longPercent))?100-Number(g.longPercent):'—'}%</p></>:<label>Son hedef · USDT{input('target',draft.target,value=>onChange({target:value}))}</label>}
 <label>Bütçe türü<select value={g.sizing} onChange={e=>grid({sizing:e.target.value as typeof g.sizing})}><option value="NOTIONAL">Toplam nominal</option><option value="MARGIN">Teminat bütçesi</option><option value="MAX_LOSS">Azami kayıp bütçesi</option></select></label><label>Bütçe · USDT{input('grid.budget',g.budget,value=>grid({budget:value}))}</label></div>
 <p className="bot-note">Bütçe hücre başına miktar değildir. Lot/tick, ücret, kaldıraç, teminat ve portföy riski için gerçek preflight gerekir. Bu önizleme yürütülebilir plan üretmez.</p>
 </fieldset>;
}
