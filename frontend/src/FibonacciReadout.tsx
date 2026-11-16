import {fibLevels,tryFibValue} from './fibonacci';
import {exactDecimal} from './exactGeometry';
import type {Geometry} from './drawings';
export default function FibonacciReadout({geometry}:{geometry:Geometry}){
 return <section className="fibonacci-readout" aria-label="Fibonacci seviye fiyatları"><b>{geometry.kind==='fibonacci_projection'?'Üç noktalı projection':geometry.kind==='fibonacci_extension'?'İki noktalı extension':'Fibonacci seviyeleri'}</b><small>{['chart-fibonacci/1','chart-fibonacci-projection/1'].includes(geometry.schema??'')?'Ayarlanabilir oranlar':'Eski kayıt · 7 sabit seviye'} · Sonuçlar fiyat adımına yuvarlanmaz.</small><div className="fibonacci-price-table"><span>ORAN</span><span>HESAP FİYATI</span>{fibLevels(geometry).map(r=>{const value=tryFibValue(geometry,r);return <div className="fibonacci-price-row" key={r}><span>{r}</span><span>{value?exactDecimal(value):'Pozitif fiyat üretmiyor'}</span></div>;})}</div><small>{geometry.kind==='fibonacci_projection'?'Fiyat = C + (B − A) × oran. PRICE_DELTA; log görünüm formülü değiştirmez.':'Fiyat = ilk nokta + (ikinci − ilk) × oran. Extension iki noktalıdır; üç noktalı projection ayrı araçtır.'}</small></section>;
}
