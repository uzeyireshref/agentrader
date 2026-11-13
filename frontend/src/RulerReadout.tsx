import {measureRuler,exactText,durationText} from './ruler';
import type {Geometry} from './drawings';
import type {Candle,Interval} from './types';
import {labels} from './types';
export default function RulerReadout({geometry,tick,rows,interval}:{geometry:Geometry;tick:string;rows:Candle[];interval:Interval}){
 try{
  const m=measureRuler(geometry,tick,rows.length?rows.map(r=>r.time):null,interval);
  return <section className="ruler-readout" aria-label="Cetvel ölçümü"><b>Fiyat–zaman cetveli · {labels[interval]}</b><dl><div><dt>Fiyat farkı</dt><dd>{exactText(m.price_change)} USDT</dd></div><div><dt>Değişim</dt><dd>{exactText(m.percent_change)}%</dd></div><div><dt>Tick farkı</dt><dd>{exactText(m.tick_change)}</dd></div><div><dt>UTC süre</dt><dd>{durationText(m.duration_seconds)}{m.elapsed_seconds<0?' · geriye':''}</dd></div><div><dt>Yüklenmiş mum</dt><dd>{m.bars.count===null?'Geçmiş gerekli':m.bars.count+' mum · '+exactText(m.bars.intervals!)+' aralık'}</dd></div></dl>{m.bars.state==='GAPPED'&&<p role="status">Arada {m.bars.missing_bars} eksik mum var. Süre gerçek UTC farkıdır; mum sayısı yüklenmiş veriye aittir.</p>}{m.bars.state==='UNAVAILABLE'&&<p role="status">Mum sayısı için iki noktayı kapsayan geçmişi yükle.</p>}<small>Farklar ilk noktadan ikinciye hesaplanır. Kesirler tam değeri gösterir.</small></section>;
 }catch{return <p className="ruler-readout" role="status">Ölçüm için geçerli fiyat adımı ve noktalar gerekli.</p>;}
}
