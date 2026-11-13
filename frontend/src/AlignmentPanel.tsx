import {supportsView,type ViewScale} from './viewScale';
import {useEffect,useRef,useState} from 'react';
import type {IChartApi,ISeriesApi,UTCTimestamp} from 'lightweight-charts';
import type {Candle} from './types';
import type {Drawing} from './drawings';
import {auditDrawing} from './alignment';
type Props={viewScale?:ViewScale;chart:IChartApi|null;series:ISeriesApi<'Candlestick'>|null;rows:Candle[];items:Drawing[];symbol:string;interval:string};
export default function AlignmentPanel(props:Props){
 const latest=useRef(props);latest.current=props;const raf=useRef(0);const [report,setReport]=useState<Record<string,unknown>|null>(null);const [busy,setBusy]=useState(false);
 useEffect(()=>()=>cancelAnimationFrame(raf.current),[]);
 const measure=()=>{if(busy)return;setBusy(true);raf.current=requestAnimationFrame(()=>{raf.current=requestAnimationFrame(()=>{
  try{const p=latest.current;if(!p.chart||!p.series)throw Error('Grafik hazır değil.');const size=p.chart.paneSize(0),pane=p.chart.panes()[0]?.getHTMLElement();const svg=p.chart.chartElement().closest('.chart-stage')?.querySelector<SVGSVGElement>('.drawings-overlay');
   const canvas=pane&&Array.from(pane.querySelectorAll('canvas')).find(c=>{const r=c.getBoundingClientRect();return Math.abs(r.width-size.width)<1&&Math.abs(r.height-size.height)<1;});if(!svg||!canvas)throw Error('Grafik canvas referansı bulunamadı.');
   const a=svg.getBoundingClientRect(),b=canvas.getBoundingClientRect(),offset={x:a.left-b.left,y:a.top-b.top};const engine={time:(time:number)=>p.chart!.timeScale().timeToCoordinate(time as UTCTimestamp),price:(price:number)=>p.series!.priceToCoordinate(price)};
   const results=p.items.filter(d=>d.geometry.symbol===p.symbol&&supportsView(d.geometry.kind,p.viewScale??'LINEAR',d.geometry.schema)).map(d=>auditDrawing(d,svg.querySelector<SVGGElement>('[data-drawing="'+d.drawing_id+'"]'),p.rows,engine,offset,size));const errors=results.filter(r=>r.checked>0&&!r.passed).length,checked=results.reduce((n,r)=>n+r.checked,0);
   setReport({observed_at:new Date().toISOString(),view_scale:p.viewScale??'LINEAR',geometry_scale:'LINEAR',blocked_drawings:p.items.filter(d=>!supportsView(d.geometry.kind,p.viewScale??'LINEAR',d.geometry.schema)).length,symbol:p.symbol,interval:p.interval,bundle:document.querySelector('script[type=module][src]')?.getAttribute('src'),dpr:window.devicePixelRatio,viewport:{width:window.innerWidth,height:window.innerHeight},size,overlay_canvas_offset_css_px:offset,checked_points:checked,failed_drawings:errors,unchecked_drawings:results.filter(r=>!r.checked).length,scope:'SVG attributes + DOM origins versus native engine time/price coordinates; CSS pixels, not raster pixel inspection',result:checked===0?'NOT_MEASURED':errors?'FAILED':'CHECKED_POINTS_PASSED',drawings:results});
  }catch(e){setReport({result:'NOT_MEASURED',reason:e instanceof Error?e.message:'Ölçüm tamamlanamadı.'});}finally{setBusy(false);}
 });});};
 return <section className="performance-panel" aria-label="Çizim hizalama kontrolü"><h2>Çizim hizalama kontrolü</h2><p>Zoom, kaydırma veya ölçek değişiminden sonra görünür çizimleri ölç. Yüklü geçmiş dışındaki noktalar doğrulanmaz. Eşik: 1 CSS piksel.</p><button onClick={measure} disabled={busy}>{busy?'Ölçülüyor…':'Hizalamayı ölç'}</button>{report&&<><p role="status">{String(report.result)} · {Number(report.checked_points??0)} nokta</p><details open><summary>Hizalama raporu</summary><pre>{JSON.stringify(report,null,2)}</pre></details></>}</section>;
}
