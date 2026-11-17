import {useEffect,useRef} from 'react';
import type {IChartApi,ISeriesApi,MouseEventParams,Time} from 'lightweight-charts';
import type {Candle} from './types';
import {UiPublisher,chartUiVisibility,type UiPolicy,type UiSnapshot,type UiEnvelope} from './uiSession';
import {emptyCrosshair,currentUiCrosshair,type UiCrosshair} from './uiCrosshair';
export function useUiSession(policy:UiPolicy|null,options:{visible?:boolean;chart:()=>IChartApi|null;series:()=>ISeriesApi<'Candlestick'>|null;rows:Candle[];marketKey:string;collect:(hover:UiCrosshair)=>UiSnapshot}){
 const latest=useRef(options);latest.current=options;const publisher=useRef<UiPublisher|null>(null),hover=useRef(emptyCrosshair()),market=useRef(options.marketKey);
 if(market.current!==options.marketKey){market.current=options.marketKey;hover.current=emptyCrosshair();}
 useEffect(()=>{publisher.current?.markDirty();});
 useEffect(()=>{
  if(!policy)return;
  const environment=()=>({visibility:chartUiVisibility(document.visibilityState==='visible',latest.current.visible!==false),online:navigator.onLine,clientTime:Date.now()});
  const send=async(id:string,key:string,value:UiEnvelope,keepalive:boolean)=>{
   const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),5000);
   try{const response=await fetch('/api/workspaces/main/ui-sessions/'+encodeURIComponent(id),{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-UI-Publisher-Key':key},body:JSON.stringify(value),keepalive,signal:abort.signal});return {status:response.status,body:await response.json().catch(()=>undefined)};}
   finally{clearTimeout(timeout);}
  };
  const client=new UiPublisher({policy,collect:()=>latest.current.collect(currentUiCrosshair(latest.current.rows,hover.current)),environment,send,
   refreshPolicy:async()=>{try{const r=await fetch('/api/workspaces/main/ui-sessions?policy_only=true',{credentials:'same-origin'});return r.ok?(await r.json()).policy:null;}catch{return null;}},
   identity:(id,status)=>{document.documentElement.dataset.uiSessionId=id;document.documentElement.dataset.uiSessionStatus=status;}});
  publisher.current=client;
  const chart=latest.current.chart(),series=latest.current.series();
  const move=(event:MouseEventParams<Time>)=>{
   const row=typeof event.time==='number'?latest.current.rows.find(r=>r.time===Number(event.time)):undefined;
   const rendered=series?event.seriesData.get(series):undefined;
   const matches=event.point&&row&&rendered&&'open'in rendered&&'high'in rendered&&'low'in rendered&&'close'in rendered&&rendered.open===row.open&&rendered.high===row.high&&rendered.low===row.low&&rendered.close===row.close;
   const price=series&&event.point&&event.paneIndex===0?series.coordinateToPrice(event.point.y):null;
   const candle:Record<string,unknown>|null=matches?{time:row.time,closed:row.closed}:null;
   if(candle&&row)for(const field of ['open','high','low','close','volume','quote_volume'] as const)candle[field]=typeof row.exact?.[field]==='string'?row.exact[field]:String(row[field]);
   hover.current={time:matches?row.time:null,price:price!==null&&Number.isFinite(price)?String(price):null,pane:event.point?event.paneIndex??0:null,hover_candle:candle};client.markDirty();
  };
  const changed=()=>client.markDirty(),visibility=()=>{void client.restrict(performance.now());},offline=()=>{void client.restrict(performance.now(),'OFFLINE');},close=()=>{void client.restrict(performance.now(),'CLOSED');};
  const reopen=(event:PageTransitionEvent)=>{if(event.persisted){client.resume();void client.step(performance.now());}};
  chart?.subscribeCrosshairMove(move);chart?.timeScale().subscribeVisibleLogicalRangeChange(changed);
  const host=document.querySelector('.chart-host');host?.addEventListener('wheel',changed,{passive:true});host?.addEventListener('pointerup',changed);
  const resize=new ResizeObserver(changed);if(host)resize.observe(host);
  document.addEventListener('visibilitychange',visibility);window.addEventListener('offline',offline);window.addEventListener('online',changed);window.addEventListener('pagehide',close);window.addEventListener('pageshow',reopen);
  const timer=setInterval(()=>{void client.step(performance.now());},250);void client.step(performance.now());
  return()=>{clearInterval(timer);close();resize.disconnect();chart?.unsubscribeCrosshairMove(move);chart?.timeScale().unsubscribeVisibleLogicalRangeChange(changed);host?.removeEventListener('wheel',changed);host?.removeEventListener('pointerup',changed);document.removeEventListener('visibilitychange',visibility);window.removeEventListener('offline',offline);window.removeEventListener('online',changed);window.removeEventListener('pagehide',close);window.removeEventListener('pageshow',reopen);if(publisher.current===client)publisher.current=null;};
 },[policy?.server_instance_id]);
 useEffect(()=>{if(options.visible===false)void publisher.current?.restrict(performance.now());else publisher.current?.markDirty();},[options.visible,policy?.server_instance_id]);
}
