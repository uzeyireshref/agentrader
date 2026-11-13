import {useEffect,useId,useRef,useState} from 'react';
import type {Geometry} from './drawings';
import {familyDefaults,isPitchfork} from './channelFamily';

type Props={geometry:Geometry;onChange:(geometry:Geometry)=>void;disabled:boolean};
const variants=[['pitchfork','Pitchfork'],['schiff_pitchfork','Schiff pitchfork'],['modified_schiff_pitchfork','Modified Schiff pitchfork'],['inside_pitchfork','Inside pitchfork']] as const;
const sourceNames={open:'Açılış',high:'En yüksek',low:'En düşük',close:'Kapanış',hl2:'HL2',hlc3:'HLC3',ohlc4:'OHLC4'};
const validDeviation=(value:string)=>/^\d+(?:\.\d{1,12})?$/.test(value)&&Number(value)>=0&&Number(value)<=10;

/** Valid drafts flow to the containing drawing editor; only its submit persists. */
export default function ChannelFamilySettings({geometry,onChange,disabled}:Props){
 const options=geometry.options??familyDefaults(geometry.kind),pitchfork=isPitchfork(geometry.kind),regression=geometry.kind==='regression_channel';
 const levelErrorId=useId();
 const [levels,setLevels]=useState(()=>options.levels.join('; ')),[levelError,setLevelError]=useState('');
 const [upper,setUpper]=useState(options.upper_deviation),[lower,setLower]=useState(options.lower_deviation),[text,setText]=useState(geometry.text??'');
 const levelsField=useRef<HTMLTextAreaElement>(null),upperField=useRef<HTMLInputElement>(null),lowerField=useRef<HTMLInputElement>(null),textField=useRef<HTMLTextAreaElement>(null);
 const update=(patch:Partial<typeof options>)=>onChange({...geometry,options:{...options,...patch}});
 useEffect(()=>{setLevels(options.levels.join('; '));setLevelError('');levelsField.current?.setCustomValidity('');},[JSON.stringify(options.levels)]);
 useEffect(()=>{setUpper(options.upper_deviation);upperField.current?.setCustomValidity('');},[options.upper_deviation]);
 useEffect(()=>{setLower(options.lower_deviation);lowerField.current?.setCustomValidity('');},[options.lower_deviation]);
 useEffect(()=>{setText(geometry.text??'');textField.current?.setCustomValidity('');},[geometry.text]);
 return <fieldset className="geometry-fields channel-family-settings" disabled={disabled} aria-label={pitchfork?'Pitchfork ayarları':regression?'Regresyon kanalı ayarları':'Kanal ayarları'}>
  {pitchfork&&<label>Pitchfork türü<select aria-label="Pitchfork türü" value={geometry.kind} onChange={e=>onChange({...geometry,kind:e.target.value as Geometry['kind']})}>{variants.map(([kind,name])=><option key={kind} value={kind}>{name}</option>)}</select></label>}
  <label>Çizgileri uzat<select aria-label="Kanal çizgilerini uzat" value={options.extend} onChange={e=>update({extend:e.target.value as typeof options.extend})}><option value="none">Uzatma</option><option value="left">Sola uzat</option><option value="right">Sağa uzat</option><option value="both">İki yöne uzat</option></select></label>
  <label className="management-check"><input type="checkbox" aria-label="Orta çizgiyi göster" checked={options.median} onChange={e=>update({median:e.target.checked})}/>Orta çizgi</label>
  <label className="management-check"><input type="checkbox" aria-label="Kanal dolgusunu göster" checked={options.background} onChange={e=>update({background:e.target.checked})}/>Arka plan dolgusu</label>
  {options.background&&<label>Dolgu opaklığı · %{Math.round(options.fill_opacity*100)}<input type="range" aria-label="Kanal dolgu opaklığı" min="0" max="100" step="1" value={Math.round(options.fill_opacity*100)} onChange={e=>update({fill_opacity:Number(e.target.value)/100})}/></label>}
  <label className="management-check"><input type="checkbox" aria-label="Kanal fiyat etiketlerini göster" checked={options.prices} onChange={e=>update({prices:e.target.checked})}/>Fiyat etiketleri</label>
  {pitchfork&&<label>Aktif seviye oranları<textarea ref={levelsField} aria-label="Pitchfork seviye oranları" aria-invalid={!!levelError} aria-describedby={levelError?levelErrorId:undefined} rows={3} value={levels} onChange={e=>{
   const value=e.target.value;setLevels(value);const values=value.split(/[;\n]/).map(v=>v.trim().replace(',','.')).filter(Boolean);
   const valid=values.length<=9&&values.every(v=>/^\d+(?:\.\d{1,12})?$/.test(v)&&Number(v)>0&&Number(v)<=10)&&new Set(values.map(Number)).size===values.length;
   const error=valid?'':'En fazla 9 farklı pozitif oran gir. En fazla 10; oranları noktalı virgül veya yeni satırla ayır.';setLevelError(error);e.target.setCustomValidity(error);if(valid)update({levels:values});
  }}/><small>Örnek: 0.5; 1; 1.5 · Her oran iki tarafta uygulanır; boş bırakırsan yalnız orta çizgi kalır.</small>{levelError&&<span id={levelErrorId} role="alert">{levelError}</span>}</label>}
  <fieldset className="family-line-styles"><legend>Çizgi stilleri</legend>{(pitchfork?[['median','Orta çizgi'],...options.levels.flatMap(v=>[['level:'+Number(v),'Seviye +'+v],['level:'+(-Number(v)),'Seviye −'+v]])]:regression?[['median','Orta çizgi'],['upper','Üst sınır'],['lower','Alt sınır']]:[['base','İlk sınır'],['offset','İkinci sınır'],['median','Orta çizgi']]).map(([role,name])=>{
   const custom=options.line_styles?.[role],value=custom??{color:'#2962ff',width:1,style:'solid' as const};
   const change=(patch:Partial<typeof value>)=>update({line_styles:{...options.line_styles,[role]:{...value,...patch}}});
   return <fieldset key={role} className="family-line-style"><legend>{name}</legend><label className="management-check"><input type="checkbox" aria-label={name+' için özel stil'} checked={!!custom} onChange={e=>{const styles={...options.line_styles};if(e.target.checked)styles[role]=value;else delete styles[role];update({line_styles:styles});}}/>Özel stil</label>{custom&&<><label>Renk<input type="color" aria-label={name+' rengi'} value={value.color} onChange={e=>change({color:e.target.value})}/></label><label>Kalınlık<select aria-label={name+' kalınlığı'} value={value.width} onChange={e=>change({width:Number(e.target.value)})}>{[1,2,3,4,5,6,7,8].map(n=><option key={n} value={n}>{n} px</option>)}</select></label><label>Çizgi<select aria-label={name+' çizgi stili'} value={value.style} onChange={e=>change({style:e.target.value as typeof value.style})}><option value="solid">Düz</option><option value="dashed">Kesik</option><option value="dotted">Noktalı</option></select></label></>}</fieldset>;
  })}<small>Özel stil kapalıyken yüzen çubuktaki ortak stil kullanılır.</small></fieldset>
  {regression&&<>
   <label>Fiyat kaynağı<select aria-label="Regresyon fiyat kaynağı" value={options.source} onChange={e=>update({source:e.target.value as typeof options.source})}>{Object.entries(sourceNames).map(([source,name])=><option key={source} value={source}>{name}</option>)}</select></label>
   <label className="management-check"><input type="checkbox" aria-label="Üst sınırda standart sapma kullan" checked={options.upper_enabled} onChange={e=>update({upper_enabled:e.target.checked})}/>Üst sınırda standart sapma kullan</label>
   <label>Üst sapma katsayısı<input ref={upperField} aria-label="Regresyon üst sapma katsayısı" inputMode="decimal" disabled={!options.upper_enabled} value={upper} onChange={e=>{const value=e.target.value.replace(',','.');setUpper(value);e.target.setCustomValidity(validDeviation(value)?'':'0 ile 10 arasında bir katsayı gir.');if(validDeviation(value))update({upper_deviation:value});}} required/></label>
   <label className="management-check"><input type="checkbox" aria-label="Alt sınırda standart sapma kullan" checked={options.lower_enabled} onChange={e=>update({lower_enabled:e.target.checked})}/>Alt sınırda standart sapma kullan</label>
   <label>Alt sapma katsayısı<input ref={lowerField} aria-label="Regresyon alt sapma katsayısı" inputMode="decimal" disabled={!options.lower_enabled} value={lower} onChange={e=>{const value=e.target.value.replace(',','.');setLower(value);e.target.setCustomValidity(validDeviation(value)?'':'0 ile 10 arasında bir katsayı gir.');if(validDeviation(value))update({lower_deviation:value});}} required/></label>
   <label className="management-check"><input type="checkbox" aria-label="Pearson korelasyonunu göster" checked={options.pearson} onChange={e=>update({pearson:e.target.checked})}/>Pearson R</label>
   <small>OLS · artık sapması √(Σe² / (N − 1)). Standart sapma kapalıysa sınır, aralıktaki yüksek/düşük uçlardan hesaplanır.</small>
  </>}
  <label>Çizim metni<textarea ref={textField} aria-label="Kanal ve pitchfork metni" rows={3} maxLength={1000} value={text} onChange={e=>{const value=e.target.value;setText(value);const valid=value.split(/\r?\n/).length<=8&&value.length<=1000;e.target.setCustomValidity(valid?'':'En fazla 8 satır ve 1000 karakter gir.');if(valid)onChange({...geometry,text:value});}}/><small>En fazla 8 satır ve 1000 karakter.</small></label>
 </fieldset>;
}
