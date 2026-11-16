/** Synthetic UI fixtures only: preserve missing precision and no order authority. */
import {canonical,canonicalRow,sha256,steps} from '../../frontend/src/evidence.ts';
import {marketSource,marketEnvironment} from '../../frontend/src/marketEnvironment.ts';
export const fixtureIdentity={source:marketSource,environment:marketEnvironment,product:'USD-M',price_type:'LAST_PRICE'};
export function fixtureResponse(url:string,value:any){
 const u=new URL(url);
 if(u.pathname==='/api/markets')return {...fixtureIdentity,...value};
 if(u.pathname==='/api/candles')return {...fixtureIdentity,symbol:u.searchParams.get('symbol')??'BTCUSDT',interval:u.searchParams.get('interval')??'15m',...value};
 return value;
}
export function fixturePacket(input:any){
 const p={...fixtureIdentity,...input},rows=(p.candles??[]).slice(-499),step=steps[p.interval as keyof typeof steps],anchor=p.interval==='1w'?345600:0;
 p.stream_epoch??=sha256('fixture:'+p.symbol+':'+p.interval+':'+p.generation).slice(0,32);
 p.quality??={state:'OK',missing_bars:0};
 if(p.data_proof)return p;
 const valid=rows.length>0&&rows.every((r:any,i:number)=>(i===rows.length-1||r.closed)&&((r.time-anchor)%step+step)%step===0&&r.close_time===r.time*1000+step*1000-1&&(!i||r.time>rows[i-1].time));
 let missing=0,warmup=0,end=rows.length-1;
 for(let i=1;i<rows.length;i++)missing+=Math.max(0,Math.floor((rows[i].time-rows[i-1].time)/step)-1);
 if(end>=0&&!rows[end].closed)end--;
 for(;end>=0&&rows[end].closed;end--){if(warmup&&rows[end+1].time-rows[end].time!==step)break;warmup++;}
 const reasons=[];
 if(!rows.length)reasons.push('EMPTY_SNAPSHOT');if(!valid)reasons.push('INVALID_GRID');if(missing)reasons.push('GRID_GAP');
 if(p.quality.state!=='OK'||p.quality.missing_bars!==0)reasons.push('QUALITY_UNPROVEN');
 if(!rows.every((r:any)=>r.exact?.schema==='chart-exact-decimal/1'&&r.exact?.state==='VERIFIED')||p.market?.exact?.schema!=='chart-exact-decimal/1'||p.market?.exact?.state!=='VERIFIED')reasons.push('PRICE_PRECISION_UNPROVEN');
 if(p.market?.symbol!==p.symbol)reasons.push('MARKET_IDENTITY_UNPROVEN');
 const revision=Math.max(1,p.sequence),payload={schema:'chart-data-snapshot/1',...fixtureIdentity,symbol:p.symbol,interval:p.interval,stream_epoch:p.stream_epoch,generation:p.generation,data_revision:revision,market:p.market,quality:p.quality,rows:rows.map(canonicalRow)};
 p.data_proof={schema:'chart-data-proof/1',stream_epoch:p.stream_epoch,generation:p.generation,data_revision:revision,state:reasons.length?'BLOCKED':'VERIFIED',blocked_reasons:reasons,snapshot_hash:sha256(canonical(payload)),grid_hash:sha256(canonical({interval:p.interval,times:rows.map((r:any)=>r.time)})),first_time:rows[0]?.time??null,last_time:rows.at(-1)?.time??null,valid,missing_bars:missing,bar_count:rows.length,closed_count:rows.filter((r:any)=>r.closed).length,warmup_available_closed_bars:warmup,live_eligible:false,order_authority:false};
 return p;
}
