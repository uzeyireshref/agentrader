import {useEffect,useRef,useState} from 'react';
import type {IChartApi,ISeriesApi} from 'lightweight-charts';
import PriceScaleControl from './PriceScaleControl';
type Props={macd?:ISeriesApi<'Line'>|null;onHideMacd?:()=>void;atr?:ISeriesApi<'Line'>|null;atrLabel?:string;onHideAtr?:()=>void;rsiLabel?:string;chart:IChartApi|null;host:HTMLElement|null;volume:ISeriesApi<'Histogram'>|null;rsi:ISeriesApi<'Line'>|null;context:string;onHideVolume:()=>void;onHideRsi:()=>void};
export default function PaneLegends(p:Props){
 const latest=useRef(p);latest.current=p;const [tops,setTops]=useState<{volume?:number;rsi?:number;atr?:number;macd?:number}>({});
 useEffect(()=>{
  if(!p.chart||!p.host)return;let frame=0;const host=p.host;
  const read=()=>{frame=0;const value:typeof tops={},origin=host.getBoundingClientRect().top;for(const key of ['volume','rsi','atr','macd'] as const){const series=latest.current[key];const element=series?.getPane().getHTMLElement();if(element&&series!.getPane().paneIndex()!==0)value[key]=element.getBoundingClientRect().top-origin+5;}setTops(old=>old.volume===value.volume&&old.rsi===value.rsi&&old.atr===value.atr&&old.macd===value.macd?old:value);};
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(read);};const observer=new ResizeObserver(schedule);observer.observe(host);for(const pane of p.chart.panes()){const element=pane.getHTMLElement();if(element)observer.observe(element);}window.addEventListener('pointerup',schedule);window.addEventListener('resize',schedule);schedule();
  return()=>{cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('pointerup',schedule);window.removeEventListener('resize',schedule);};
 },[p.chart,p.host,p.volume,p.rsi,p.atr,p.macd,p.context]);
 return <div className="pane-legends">{(['volume','rsi','atr','macd'] as const).map(key=>{const value=p[key];return value&&tops[key]!==undefined?<div className="pane-legend" key={key} style={{top:tops[key]}} data-pane-kind={key}><b>{key==='volume'?'Hacim':key==='rsi'?(p.rsiLabel??'RSI 14'):key==='atr'?(p.atrLabel??'ATR 14'):'MACD'}</b><small>{key==='volume'?'Baz hacim':key==='rsi'?'0–100':key==='atr'?'Fiyat birimi':'Çizgi / Sinyal / Histogram'}</small><PriceScaleControl series={value} host={p.host} context={p.context} label={key==='volume'?'Otomatik hacim ölçeği':key==='rsi'?'Otomatik RSI ölçeği':key==='atr'?'Otomatik ATR ölçeği':'Otomatik MACD ölçeği'}/><button aria-label={key==='volume'?'Hacim panelini gizle':key==='rsi'?'RSI panelini gizle':key==='atr'?'ATR panelini gizle':'MACD panelini gizle'} title="Paneli gizle" onClick={key==='volume'?p.onHideVolume:key==='rsi'?p.onHideRsi:key==='atr'?p.onHideAtr:p.onHideMacd}>×</button></div>:null;})}</div>;
}
