import {useEffect,useState} from 'react';
import type {ISeriesApi} from 'lightweight-charts';
type Props={series:Pick<ISeriesApi<'Candlestick'>,'priceScale'>|null;host:HTMLElement|null;context:string;label?:string};
/** Observe the native scale after gestures; no idle animation/polling loop. */
export default function PriceScaleControl({series,host,context,label='Otomatik fiyat ölçeği'}:Props){
 const [automatic,setAutomatic]=useState<boolean|null>(null);
 useEffect(()=>{
  if(!series||!host){setAutomatic(null);return;}
  let frame=0;
  const read=()=>{frame=0;setAutomatic(series.priceScale().options().autoScale);};
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(read);};
  const move=(event:PointerEvent)=>{if(event.buttons)schedule();};
  schedule();
  host.addEventListener('pointermove',move);
  host.addEventListener('dblclick',schedule);
  window.addEventListener('pointerup',schedule);
  window.addEventListener('pointercancel',schedule);
  window.addEventListener('keyup',schedule);
  return()=>{cancelAnimationFrame(frame);host.removeEventListener('pointermove',move);host.removeEventListener('dblclick',schedule);window.removeEventListener('pointerup',schedule);window.removeEventListener('pointercancel',schedule);window.removeEventListener('keyup',schedule);};
 },[series,host,context]);
 return <button className="price-scale-control" aria-label={label} aria-pressed={automatic===true} disabled={automatic===null} title={label+(automatic?' · Otomatik; manuel için tıkla.':' · Manuel; görünür değerleri otomatik sığdır.')} onClick={()=>{if(!series)return;const next=!series.priceScale().options().autoScale;series.priceScale().applyOptions({autoScale:next});setAutomatic(next);}}><span>Ölçek:</span> {automatic===null?'Hazırlanıyor':automatic?'Otomatik':'Manuel'}</button>;
}
