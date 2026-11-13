import {useEffect,useRef} from 'react';
import type {IChartApi,ISeriesApi,MouseEventParams,Time} from 'lightweight-charts';
import type {Candle} from './types';
import {pricePrecision} from './drawings';
export const OHLC_EMPTY='Mum seçilmedi · UTC';
type Ohlc=Pick<Candle,'open'|'high'|'low'|'close'>;
export function formatOhlc(value:Ohlc|undefined,tick:number):string{
 if(!value||!Number.isFinite(tick)||tick<=0||![value.open,value.high,value.low,value.close].every(Number.isFinite))return OHLC_EMPTY;
 const digits=pricePrecision(tick),format=new Intl.NumberFormat('tr-TR',{minimumFractionDigits:digits,maximumFractionDigits:digits});
 return 'A '+format.format(value.open)+'  Y '+format.format(value.high)+'  D '+format.format(value.low)+'  K '+format.format(value.close);
}
function find(rows:Candle[],time:number):Candle|undefined{let low=0,high=rows.length-1;while(low<=high){const mid=(low+high)>>>1;if(rows[mid].time===time)return rows[mid];if(rows[mid].time<time)low=mid+1;else high=mid-1;}return undefined;}
type Props={chart:IChartApi|null;series:ISeriesApi<'Candlestick'>|null;rows:Candle[];tick:number};
/** Parent remounts this label for market/timeframe changes; queued old events cannot write the new DOM. */
export default function OhlcReadout(props:Props){
 const node=useRef<HTMLDivElement>(null),latest=useRef(props),hoverTime=useRef<number|null>(null);latest.current=props;
 useEffect(()=>{
  if(!props.chart||!props.series)return;const series=props.series;
  const move=(event:MouseEventParams<Time>)=>{
   const p=latest.current,c=event.seriesData.get(series),expected=typeof event.time==='number'?find(p.rows,Number(event.time)):undefined;
   const matches=c&&'open'in c&&expected&&c.open===expected.open&&c.high===expected.high&&c.low===expected.low&&c.close===expected.close;
   hoverTime.current=matches?Number(event.time):null;
   const text=matches?formatOhlc(c,p.tick):OHLC_EMPTY;if(node.current&&node.current.textContent!==text)node.current.textContent=text;
  };
  props.chart.subscribeCrosshairMove(move);return()=>props.chart?.unsubscribeCrosshairMove(move);
 },[props.chart,props.series]);
 useEffect(()=>{if(hoverTime.current===null)return;const value=find(props.rows,hoverTime.current);if(!value)hoverTime.current=null;const text=formatOhlc(value,props.tick);if(node.current&&node.current.textContent!==text)node.current.textContent=text;},[props.rows,props.tick]);
 return <div className="ohlc" ref={node} aria-label="Seçili mum fiyatları">{OHLC_EMPTY}</div>;
}
