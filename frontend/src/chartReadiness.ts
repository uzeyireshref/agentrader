import type {Candle,ChartState,Interval} from './types';
export const statusLabels:Record<string,string>={CONNECTING:'Bağlanıyor',SYNCING:'Mumlar eşitleniyor',EMPTY:'Mum verisi yok',LIVE:'Canlı',RECONNECTING:'Yeniden bağlanıyor',STALE:'Veri gecikiyor',GAP:'Veri boşluğu',STOPPED:'Bağlantı durdu',ERROR:'Veri alınamadı',RENDER_ERROR:'Grafik güncellenemedi',UNVERIFIED:'Veri doğrulanamadı'};
export function marketReadiness(view:ChartState,symbol:string,interval:Interval){
 const matches=view.symbol===symbol&&view.interval===interval;
 const rows=matches?view.candles:[];
 const status=!matches?'CONNECTING':view.status==='RENDER_ERROR'?view.status:view.data_proof?.state==='BLOCKED'?(view.data_proof.blocked_reasons.includes('GRID_GAP')?'GAP':'UNVERIFIED'):view.status==='LIVE'&&!rows.length?'EMPTY':view.status;
 return {matches,rows,status,label:statusLabels[status]??'Veri bekleniyor',inspectable:rows.length>0&&status!=='RENDER_ERROR',fresh:status==='LIVE'&&rows.length>0,renderError:status==='RENDER_ERROR'};
}
export function candleAt(rows:Candle[],time:number):Candle|undefined{let low=0,high=rows.length-1;while(low<=high){const mid=(low+high)>>>1;if(rows[mid].time===time)return rows[mid];if(rows[mid].time<time)low=mid+1;else high=mid-1;}return undefined;}
export function matchesCandle(expected:Candle|undefined,value:unknown):boolean{
 if(!expected||!value||typeof value!=='object')return false;
 const c=value as Partial<Candle>;return c.open===expected.open&&c.high===expected.high&&c.low===expected.low&&c.close===expected.close;
}
export function displayValue(value:number|undefined,digits=2):string{return value===undefined||!Number.isFinite(value)?'—':new Intl.NumberFormat('tr-TR',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);}
export function utcCandleTime(row:Candle|undefined){return row?new Date(row.time*1000).toISOString().slice(0,19).replace('T',' ')+' UTC':'—';}
