import {useEffect,useState} from 'react';
import {candleCountdown,COUNTDOWN_EXPLANATION,type CountdownClock} from './closeCountdown';
import type {ChartState} from './types';
export const browserCountdownClock=():CountdownClock=>({mono:performance.now(),wall:Date.now()});
export default function CandleCountdown({view,clock=browserCountdownClock}:{view:ChartState;clock?:()=>CountdownClock}){
 const [,setTick]=useState(0);
 useEffect(()=>{
  const tick=()=>setTick(value=>value+1);
  const timer=setInterval(tick,250);
  return()=>clearInterval(timer);
 },[clock]);
 // A newly received proof can be newer than the last timer tick. Sample at
 // render time so that normal packet delivery cannot resemble clock reversal.
 const result=candleCountdown(view,clock());
 return <span className="candle-countdown" data-countdown-state={result.state} data-countdown-reason={result.reason} aria-label="Mum kapanış süresi" title={result.state==='APPROXIMATE'?COUNTDOWN_EXPLANATION:'Güncel ve güvenilir saat kanıtı olmadan kapanış süresi gösterilmez.'}>{result.label}</span>;
}

