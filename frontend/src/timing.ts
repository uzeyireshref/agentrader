/** Producer durations are consumed with our own monotonic clock; no cross-process subtraction. */
export type TimeProof={schema:'chart-time-proof/1';policy:{schema:'chart-time-policy/1'};state:'FRESH'|'BLOCKED';reason:string|null;data_age_ms:number|null;upstream_age_upper_ms:number|null;uncertainty_ms:number|null;upstream_event_time:number|null};
export function validTiming(value:unknown):value is TimeProof{
 if(!value||typeof value!=='object')return false;const p=value as TimeProof;
 if(p.schema!=='chart-time-proof/1'||p.policy?.schema!=='chart-time-policy/1'||!['FRESH','BLOCKED'].includes(p.state))return false;
 if(p.state==='FRESH'&&p.reason!==null||p.state==='BLOCKED'&&typeof p.reason!=='string')return false;
 const ages=[p.data_age_ms,p.upstream_age_upper_ms,p.uncertainty_ms];
 if(!ages.every(v=>v===null?p.state==='BLOCKED':typeof v==='number'&&Number.isFinite(v)&&v>=0))return false;
 return p.upstream_event_time===null?p.state==='BLOCKED':Number.isSafeInteger(p.upstream_event_time)&&p.upstream_event_time>0;
}
