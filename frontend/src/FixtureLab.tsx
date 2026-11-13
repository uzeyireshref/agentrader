import {useEffect,useRef,useState} from 'react';
import {createChart,CandlestickSeries,LineSeries,HistogramSeries,ColorType,type IChartApi,type ISeriesApi,type UTCTimestamp} from 'lightweight-charts';
import {fixtures,fixtureRows,fixtureDrawings,comparePoint,type Fixture} from './fixtureReference';
import {ema,rsi} from './indicators';
import {LineSeriesWriter} from './lineWriter';
import DrawingLayer from './DrawingLayer';
import AlignmentPanel from './AlignmentPanel';
import type {Geometry} from './drawings';
export default function FixtureLab(){
 const [name,setName]=useState('time_gap'),[start,setStart]=useState(0),[selected,setSelected]=useState<string|null>(null),[revision,setRevision]=useState(0),[report,setReport]=useState<unknown>(null),[hover,setHover]=useState<unknown>(null);
 const fixture=fixtures.find(f=>f.name===name)!,rows=fixtureRows(fixture).slice(start);
 const [items,setItems]=useState(()=>fixtureDrawings(fixtures.find(f=>f.name==='time_gap')!));
 const host=useRef<HTMLDivElement>(null),chart=useRef<IChartApi|null>(null),candles=useRef<ISeriesApi<'Candlestick'>|null>(null),volume=useRef<ISeriesApi<'Histogram'>|null>(null),lines=useRef<ISeriesApi<'Line'>[]>([]),writers=useRef<LineSeriesWriter[]>([]),current=useRef<{fixture:Fixture;start:number}>({fixture,start});current.current={fixture,start};
 useEffect(()=>{
  if(!host.current)return;
  const instance=createChart(host.current,{autoSize:true,layout:{background:{type:ColorType.Solid,color:'#101416'},textColor:'#a1b0b7',attributionLogo:true},timeScale:{timeVisible:true},rightPriceScale:{minimumWidth:80},localization:{locale:'tr-TR'}});
  chart.current=instance;candles.current=instance.addSeries(CandlestickSeries,{upColor:'#4cba94',downColor:'#db786f'});volume.current=instance.addSeries(HistogramSeries,{priceFormat:{type:'volume'}},1);
  lines.current=[instance.addSeries(LineSeries,{title:'EMA 20',color:'#e5b75d',priceLineVisible:false}),instance.addSeries(LineSeries,{title:'EMA 50',color:'#7e9ed4',priceLineVisible:false}),instance.addSeries(LineSeries,{title:'RSI 14',color:'#b29ad4',priceLineVisible:false},2)];
  writers.current=lines.current.map(line=>new LineSeriesWriter({setData:points=>line.setData(points.map(p=>({...p,time:p.time as UTCTimestamp}))),update:(p,historical)=>line.update({...p,time:p.time as UTCTimestamp},historical)}));instance.panes()[0].setStretchFactor(4);
  instance.subscribeCrosshairMove(event=>{
   if(typeof event.time!=='number'){setHover(null);return;}
   const values=lines.current.map(line=>{const point=event.seriesData.get(line);return point&&'value'in point?point.value:null;});
   const sample=comparePoint(current.current.fixture,Number(event.time),{ema20:values[0],ema50:values[1],rsi14:values[2]});
   setHover(current.current.start?{result:'NOT_COMPARABLE_HISTORY'}:sample?{observed_at:new Date().toISOString(),case:current.current.fixture.name,source:'crosshair.seriesData',...sample}:null);
  });setRevision(v=>v+1);
  return()=>{queueMicrotask(()=>instance.remove());chart.current=null;};
 },[]);
 useEffect(()=>{
  if(!candles.current||!volume.current)return;
  const data=fixtureRows(fixture).slice(start);
  candles.current.setData(data.map(c=>({...c,time:c.time as UTCTimestamp})));volume.current.setData(data.map(c=>({time:c.time as UTCTimestamp,value:c.volume})));
  writers.current[0].write(ema(data,20));writers.current[1].write(ema(data,50));writers.current[2].write(rsi(data));
  chart.current?.timeScale().setVisibleLogicalRange({from:Math.max(0,115-start),to:Math.max(40,153-start)});setReport(null);setHover(null);
 },[name,start,revision]);
 const choose=(value:string)=>{setName(value);setStart(0);setSelected(null);setItems(fixtureDrawings(fixtures.find(f=>f.name===value)!));};
 const audit=()=>{
  if(start){setReport({result:'NOT_COMPARABLE_HISTORY',reason:'Önce tam geçmişi yükle; referans 300 mumla başlar.'});return;}
  const maps=lines.current.map(line=>new Map(line.data().map(point=>[Number(point.time),'value'in point?point.value:null])));
  const comparisons=fixture.times.map(time=>comparePoint(fixture,time,{ema20:maps[0].get(time)??null,ema50:maps[1].get(time)??null,rsi14:maps[2].get(time)??null}));
  setReport({observed_at:new Date().toISOString(),result:comparisons.every(c=>c?.passed)?'CHECKED_SERIES_VALUES_PASSED':'FAILED',case:name,points:comparisons.length,reference:'Python Decimal precision 50; tolerance 1e-8',scope:'native series data; crosshair sample shown separately',comparisons});
 };
 const change=async(id:string,geometry:Geometry)=>{setItems(list=>list.map(d=>d.drawing_id===id?{...d,geometry,revision:d.revision+1}:d));};
 return <main className="fixture-lab"><a href="/">← Canlı grafiğe dön</a><h1>Kontrollü grafik doğruluğu</h1><p>Yalnız sabit test verisi · borsa bağlantısı ve sunucuya çizim kaydı yok. Değişiklikler bu ekrana aittir.</p>
  <div className="fixture-controls"><label>Referans senaryosu <select value={name} onChange={e=>choose(e.target.value)}>{fixtures.map(f=><option key={f.name}>{f.name}</option>)}</select></label><button onClick={()=>setStart(100)}>Son 200 mum</button><button onClick={()=>setStart(0)}>Tam geçmişi yükle</button><button onClick={()=>chart.current?.timeScale().setVisibleLogicalRange({from:Math.max(0,115-start),to:Math.max(40,153-start)})}>Boşluk bölgesine git</button><button onClick={()=>chart.current?.timeScale().fitContent()}>Grafiği sığdır</button><button onClick={audit}>Seri değerlerini doğrula</button></div>
  <p>{rows.length} test mumu · {name==='time_gap'?'132 ve 133 indeksleri arasında 3 eksik 15 dakikalık mum':'Düzenli 15 dakikalık zamanlar'} · Tam geçmiş yoksa gösterge karşılaştırması yapılmaz.</p>
  <div className="chart-stage fixture-stage"><div className="chart-host" ref={host}/><DrawingLayer symbol="FIXTUREUSDT" chart={chart.current} series={candles.current} rows={rows} items={items} selected={selected} select={setSelected} change={change} interval="15m" tick={.01} disabled={false}/></div>
  <AlignmentPanel chart={chart.current} series={candles.current} rows={rows} items={items} symbol="FIXTUREUSDT" interval="15m"/>
  <section className="performance-panel"><h2>İmleçteki gerçek gösterge değeri</h2><p>Mumun üzerine gel: seriesData değerleri Python referansıyla karşılaştırılır.</p><pre aria-label="İmleç referans karşılaştırması">{JSON.stringify(hover,null,2)}</pre></section>
  <section className="performance-panel"><h2>Grafik motorundaki seri doğrulaması</h2><pre aria-label="Seri referans karşılaştırması">{JSON.stringify(report,null,2)}</pre></section>
 </main>;
}
