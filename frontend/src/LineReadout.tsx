import type {Geometry} from './drawings';
import type {Candle,Interval} from './types';
import {linePriceAt} from './lineGeometry';
import {displayNumber} from './exactGeometry';
import {displayValue} from './chartReadiness';
import {pricePrecision} from './drawings';
export default function LineReadout({geometry,rows,interval,tick}:{geometry:Geometry;rows:Candle[];interval:Interval;tick:string}){
 let value='—',reason='';try{if(!rows.length)throw Error('GRID_UNAVAILABLE');value=displayValue(displayNumber(linePriceAt(geometry,rows,rows.at(-1)!.time,interval)),pricePrecision(Number(tick)));}catch(e){const code=e instanceof Error?e.message:'';reason=code==='OUT_OF_SCOPE'?'Son mum çizimin yön kapsamı dışında.':code==='NON_POSITIVE_PROJECTION'?'Bu zamandaki izdüşüm pozitif fiyat üretmiyor.':'Hesap için kesintisiz yüklü mum ızgarası gerekiyor.';}
 return <div className="line-readout"><b>{geometry.kind==='extended_line'?'İki yöne uzatılmış':geometry.kind==='horizontal_ray'?'Başlangıçtan sağa':'İlk noktadan ikinciye doğru'}</b><p>Son yüklü mumda fiyat: <span>{value}</span></p>{reason&&<small>{reason}</small>}</div>;
}
