import {createChart,CandlestickSeries,HistogramSeries,type UTCTimestamp} from 'lightweight-charts';
import {ChartSeriesWriter} from '../../src/seriesWriter';
import {RenderRecovery,applyRenderedPacket} from '../../src/renderRecovery';
import {initialState,type Candle,type Packet} from '../../src/types';

const check=(value:unknown,message:string)=>{if(!value)throw Error(message);};
const frame=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
async function run(){
 const results=[];
 for(const target of ['candle','volume'] as const)for(const phase of ['snapshot','update','history'] as const){
  const host=document.getElementById('chart')!,chart=createChart(host,{width:1000,height:600});
  try{
   const candle=chart.addSeries(CandlestickSeries),volume=chart.addSeries(HistogramSeries,{},1);
   let fault=false,fullWrites=0,injections=0;
   const fail=(series:string)=>{if(fault&&target===series){injections++;throw Error('A1 injected '+series+' write failure');}};
   const writer=new ChartSeriesWriter({setData:rows=>{fail('candle');fullWrites++;candle.setData(rows.map(c=>({...c,time:c.time as UTCTimestamp})));},update:(c,h)=>{fail('candle');candle.update({...c,time:c.time as UTCTimestamp},h);}},
    {setData:rows=>{fail('volume');volume.setData(rows.map(c=>({...c,time:c.time as UTCTimestamp})));},update:(c,h)=>{fail('volume');volume.update({...c,time:c.time as UTCTimestamp},h);}});
   const recovery=new RenderRecovery();
   let state=initialState('BTCUSDT','15m');
   const rows:Candle[]=Array.from({length:30},(_,i)=>({time:1800000000+i*900,open:100+i,high:110+i,low:90+i,close:105+i,volume:10+i,quote_volume:1000,close_time:(1800000000+i*900)*1000+899999,closed:i<29}));
   const packet=(extra:Partial<Packet>={}):Packet=>({type:'snapshot',symbol:'BTCUSDT',interval:'15m',generation:1,sequence:1,status:'LIVE',received_at:Date.now(),candles:rows,...extra});
   const paint=(next:typeof state,full:boolean)=>{writer.write(next.candles,full);};
   const send=(p:Packet)=>{state=applyRenderedPacket(state,p,recovery,paint);document.getElementById('status')!.textContent=state.status;};
   if(phase!=='snapshot')send(packet());
   fault=true;
   if(phase==='snapshot')send(packet());
   if(phase==='update')send(packet({type:'update',sequence:2,candles:undefined,candle:{...rows[29],close:138,volume:99}}));
   if(phase==='history'){
    state={...state,candles:[{...rows[0],time:rows[0].time-900,close_time:rows[0].time*1000-1,closed:true},...state.candles]};
    if(!recovery.run(true,full=>paint(state,full)))state={...state,status:'RENDER_ERROR'};
    document.getElementById('status')!.textContent=state.status;
   }
   check(state.status==='RENDER_ERROR'&&recovery.pending,'failure must latch');
   const heartbeat=()=>packet({type:'update',sequence:state.sequence,candles:undefined});
   for(let i=0;i<3;i++){send(heartbeat());await frame();check(document.getElementById('status')!.textContent==='RENDER_ERROR','heartbeat hid error');}
   fault=false;const writesBefore=fullWrites;send(heartbeat());await frame();
   check(state.status==='LIVE'&&!recovery.pending,'successful repaint must recover');
   check(fullWrites===writesBefore+1,'recovery must use full setData');
   const actual=candle.data(),actualVolume=volume.data();
   check(actual.length===state.candles.length&&actualVolume.length===actual.length,'paired series length mismatch');
   state.candles.forEach((expected,i)=>{
    const c=actual[i],v=actualVolume[i];
    check(c.time===expected.time&&'open'in c&&c.open===expected.open&&c.high===expected.high&&c.low===expected.low&&c.close===expected.close,'native candle mismatch '+i);
    check(v.time===expected.time&&'value'in v&&v.value===expected.volume,'native volume mismatch '+i);
   });
   chart.timeScale().fitContent();await frame();
   check(candle.priceToCoordinate(state.candles.at(-1)!.close)!==null,'native chart has no price coordinate');
   const stable=fullWrites;send(heartbeat());check(fullWrites===stable,'healthy heartbeat repainted');
   results.push({target,phase,passed:true,failed_heartbeats:3,injections,candles:actual.length,compared_fields:actual.length*7,full_recovery:true});
  }finally{chart.remove();}
 }
 return {passed:true,engine:'lightweight-charts 5.2.1',cases:results};
}
run().then(result=>{(window as any).__a1={...result,done:true};}).catch(error=>{(window as any).__a1={done:true,passed:false,error:String(error),stack:error.stack};});
