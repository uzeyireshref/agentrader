import {familyKinds,type FamilyKind} from './channelFamily';
import {useModalDialog} from './useModalDialog';
import {supportsView,type ViewScale} from './viewScale';
import {useEffect,useId,useMemo,useRef,useState} from 'react';
import Icon from './ChartIcon';
import {chartTools,normalizeSearch,searchMarkets,type ToolKind} from './chartCommands';
import {intervals,labels,type Interval,type Market} from './types';
export type CommandMode='symbols'|'tools'|'intervals';
type Props={viewScale?:ViewScale;initialMode:CommandMode;markets:Market[];symbol:string;interval:Interval;tool:ToolKind;toolsDisabled:boolean;catalogError:boolean;onSymbol:(s:string)=>void;onTool:(t:ToolKind)=>void;onInterval:(i:Interval)=>void;onClose:()=>void;onRetry:()=>void};
export default function ChartCommandDialog(p:Props){
 const dialog=useRef<HTMLDialogElement>(null),input=useRef<HTMLInputElement>(null),id=useId();
 const [mode,setMode]=useState(p.initialMode),[query,setQuery]=useState(''),[active,setActive]=useState(0);
 const options=useMemo(()=>{
  if(mode==='symbols')return searchMarkets(p.markets,query).map(m=>({id:m.symbol,label:m.symbol,detail:'Binance USD-M · Sürekli vadeli',icon:'candle',selected:m.symbol===p.symbol,disabled:false,pick:()=>p.onSymbol(m.symbol)}));
  if(mode==='tools')return chartTools.filter(t=>normalizeSearch(t.label+t.search).includes(normalizeSearch(query))).map(t=>({id:t.id,label:t.label,detail:!supportsView(t.id,p.viewScale??'LINEAR',familyKinds.includes(t.id as FamilyKind)?'chart-channel-family/1':undefined)?'Log görünümde engelli':t.key?'Grafik odağında '+t.key:'Çizim aracı',icon:t.icon,selected:t.id===p.tool,disabled:t.id!=='cursor'&&(p.toolsDisabled||!supportsView(t.id,p.viewScale??'LINEAR',familyKinds.includes(t.id as FamilyKind)?'chart-channel-family/1':undefined)),pick:()=>p.onTool(t.id)}));
  return intervals.filter(i=>normalizeSearch(i+labels[i]).includes(normalizeSearch(query))).map(i=>({id:i,label:labels[i],detail:i,icon:'candle',selected:i===p.interval,disabled:false,pick:()=>p.onInterval(i)}));
 },[mode,query,p.markets,p.symbol,p.interval,p.tool,p.toolsDisabled,p.viewScale,p.onSymbol,p.onTool,p.onInterval]);
 const visible=options.slice(0,100),index=Math.min(active,Math.max(0,visible.length-1));
 useModalDialog(dialog);useEffect(()=>{input.current?.focus();},[]);
 useEffect(()=>{document.getElementById(id+'-'+index)?.scrollIntoView({block:'nearest'});},[id,index,mode,query]);
 const choose=(i:number)=>{const option=visible[i];if(!option||option.disabled)return;option.pick();p.onClose();};
 const changeMode=(next:CommandMode)=>{setMode(next);setQuery('');setActive(0);input.current?.focus();};
 return <dialog className="command-dialog" ref={dialog} aria-labelledby={id+'-title'} onCancel={e=>{e.preventDefault();p.onClose();}} onKeyDown={e=>{e.stopPropagation();if(e.key==='Escape'){e.preventDefault();p.onClose();}}}>
  <header><h2 id={id+'-title'}>Hızlı erişim</h2><button className="icon-button" aria-label="Hızlı erişimi kapat" onClick={p.onClose}><Icon name="close"/></button></header>
  <div className="command-tabs" role="group" aria-label="Arama kapsamı">{([['symbols','Semboller'],['tools','Araçlar'],['intervals','Zaman dilimleri']] as const).map(([key,label])=><button key={key} aria-pressed={mode===key} onClick={()=>changeMode(key)}>{label}</button>)}</div>
  <label className="command-search"><Icon name="search"/><input ref={input} role="combobox" aria-label="Hızlı erişimde ara" aria-autocomplete="list" aria-controls={id+'-list'} aria-expanded={true} aria-activedescendant={visible.length?id+'-'+index:undefined} value={query} placeholder={mode==='symbols'?'Sembol ara · BTC, ETH…':mode==='tools'?'Araç ara · trend, cetvel…':'Zaman dilimi ara · 15m, 1h…'} onChange={e=>{setQuery(e.target.value);setActive(0);}} onKeyDown={e=>{if(e.nativeEvent.isComposing)return;if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();setActive(v=>Math.max(0,Math.min(visible.length-1,v+(e.key==='ArrowDown'?1:-1))));}else if(e.key==='Home'){e.preventDefault();setActive(0);}else if(e.key==='End'){e.preventDefault();setActive(Math.max(0,visible.length-1));}else if(e.key==='Enter'){e.preventDefault();choose(index);}}}/></label>
  <div className="command-results" role="listbox" aria-label="Arama sonuçları" id={id+'-list'}>{visible.map((o,i)=><button type="button" role="option" id={id+'-'+i} key={o.id} aria-selected={i===index} aria-disabled={o.disabled} className={i===index?'highlighted':''} onPointerMove={()=>setActive(i)} onClick={()=>choose(i)}><Icon name={o.icon}/><span><b>{o.label}</b><small>{o.disabled&&o.detail!=='Log görünümde engelli'?'Çizimlerin hazır olması bekleniyor':o.detail}</small></span>{o.selected&&<small className="command-current">Etkin</small>}<span className="command-enter">↵</span></button>)}</div>
  {!visible.length&&<div className="command-empty" role="status">{mode==='symbols'&&!p.markets.length?<><p>{p.catalogError?'Piyasa listesi alınamadı.':'Piyasa listesi yükleniyor…'}</p>{p.catalogError&&<button onClick={p.onRetry}>Yeniden dene</button>}</>:<p>Eşleşen sonuç yok. {mode==='intervals'?'Yalnız desteklenen zaman dilimleri listelenir.':'Başka bir arama dene.'}</p>}</div>}
  <footer><span>↑ ↓ Gezin · Enter Seç · Esc Kapat</span><span>{options.length>100?'İlk 100 sonuç · Aramanı daralt':options.length+' sonuç'}</span></footer>
 </dialog>;
}
