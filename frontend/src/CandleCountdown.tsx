import {useEffect,useState} from 'react';
import {candleCountdown,COUNTDOWN_EXPLANATION,type CountdownClock} from './closeCountdown';
import type {ChartState} from './types';
export const browserCountdownClock=():CountdownClock=>({mono:performance.now(),wall:Date.now()});
export default function CandleCountdown({view,clock=browserCountdownClock}:{view:ChartState;clock?:()=>CountdownClock}){
 const [now,setNow]=useState(clock);
 useEffect(()=>{
  const tick=()=>setNow(clock());tick();
  const timer=setInterval(tick,250);
  return()=>clearInterval(timer);
 },[clock,view.timing_received_mono,view.symbol,view.interval]);
 const result=candleCountdown(view,now);
 return <span className="candle-countdown" data-countdown-state={result.state} data-countdown-reason={result.reason} aria-label="Mum kapanış süresi" title={result.state==='APPROXIMATE'?COUNTDOWN_EXPLANATION:'Güncel ve güvenilir saat kanıtı olmadan kapanış süresi gösterilmez.'}>{result.label}</span>;
}

