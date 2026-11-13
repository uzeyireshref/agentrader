import type {Candle,Market,Interval} from './types';
export type DataProof={schema:'chart-data-proof/1';stream_epoch:string;generation:number;data_revision:number;state:'VERIFIED'|'BLOCKED';blocked_reasons:string[];snapshot_hash:string;grid_hash:string;first_time:number|null;last_time:number|null;valid:boolean;missing_bars:number;bar_count:number;closed_count:number;warmup_available_closed_bars:number;live_eligible:false;order_authority:false};
export const steps:Record<Interval,number>={'1m':60,'5m':300,'30m':1800,'15m':900,'1h':3600,'4h':14400,'1d':86400,'1w':604800};
export function canonical(value:unknown):string{
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 if(value!==null&&typeof value==='object')return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+canonical((value as Record<string,unknown>)[key])).join(',')+'}';
 const encoded=JSON.stringify(value);if(encoded===undefined)throw Error('Unsupported canonical value');return encoded;
}
/** SHA-256 fingerprint only, never an authentication signature. Tested against node crypto. */
export function sha256(text:string):string{
 const bytes=new TextEncoder().encode(text),length=Math.ceil((bytes.length+9)/64)*64,buffer=new Uint8Array(length);buffer.set(bytes);buffer[bytes.length]=128;
 const view=new DataView(buffer.buffer);view.setUint32(length-8,Math.floor(bytes.length/0x20000000));view.setUint32(length-4,(bytes.length*8)>>>0);
 const k=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
 const h=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],w=new Uint32Array(64);const rotr=(x:number,n:number)=>(x>>>n)|(x<<(32-n));
 for(let offset=0;offset<length;offset+=64){
  for(let i=0;i<16;i++)w[i]=view.getUint32(offset+i*4);
  for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=((rotr(a,7)^rotr(a,18)^(a>>>3))+w[i-16]+(rotr(b,17)^rotr(b,19)^(b>>>10))+w[i-7])>>>0;}
  let [a,b,c,d,e,f,g,j]=h;
  for(let i=0;i<64;i++){const t1=(j+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^(~e&g))+k[i]+w[i])>>>0,t2=((rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c)))>>>0;j=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}
  [a,b,c,d,e,f,g,j].forEach((v,i)=>h[i]=(h[i]+v)>>>0);
 }
 return h.map(v=>v.toString(16).padStart(8,'0')).join('');
}
function numberHex(value:number):string{if(!Number.isFinite(value))throw Error('Nonfinite chart value');const data=new DataView(new ArrayBuffer(8));data.setFloat64(0,value===0?0:value);return Array.from(new Uint8Array(data.buffer),v=>v.toString(16).padStart(2,'0')).join('');}
export function canonicalRow(row:Candle){return {time:row.time,close_time:row.close_time,closed:row.closed,chart_values:[row.open,row.high,row.low,row.close,row.volume,row.quote_volume].map(numberHex),exact:row.exact??null};}
export function verifyEvidence(rows:Candle[],market:Market|null,quality:Record<string,unknown>,symbol:string,interval:Interval,epoch:string,generation:number,proof:DataProof):boolean{
 try{
  if(proof.schema!=='chart-data-proof/1'||proof.stream_epoch!==epoch||proof.generation!==generation||!Number.isSafeInteger(proof.data_revision)||proof.data_revision<1||proof.live_eligible!==false||proof.order_authority!==false)return false;
  if(!Number.isSafeInteger(proof.bar_count)||proof.bar_count<1||proof.bar_count>499)return false;
  const window=rows.filter(r=>proof.first_time!==null&&proof.last_time!==null&&r.time>=proof.first_time&&r.time<=proof.last_time);if(window.length!==proof.bar_count||window[0].time!==proof.first_time||window.at(-1)!.time!==proof.last_time)return false;
  const step=steps[interval],anchor=interval==='1w'?345600:0;
  const valid=window.every((r,i)=>(i===window.length-1||r.closed)&&((r.time-anchor)%step+step)%step===0&&r.close_time===r.time*1000+step*1000-1&&(!i||r.time>window[i-1].time));
  let missing=0;for(let i=1;i<window.length;i++)missing+=Math.max(0,Math.floor((window[i].time-window[i-1].time)/step)-1);
  let warmup=0,end=window.length-1;if(!window[end].closed)end--;for(;end>=0&&window[end].closed;end--){if(warmup&&window[end+1].time-window[end].time!==step)break;warmup++;}
  const reasons:string[]=[];if(!valid)reasons.push('INVALID_GRID');if(missing)reasons.push('GRID_GAP');
  if(quality.state!=='OK'||!Number.isInteger(quality.missing_bars)||quality.missing_bars!==0)reasons.push('QUALITY_UNPROVEN');
  if(!window.every(r=>r.exact?.schema==='chart-exact-decimal/1'&&r.exact?.state==='VERIFIED')||market?.exact?.schema!=='chart-exact-decimal/1'||market?.exact?.state!=='VERIFIED')reasons.push('PRICE_PRECISION_UNPROVEN');
  if(market?.symbol!==symbol)reasons.push('MARKET_IDENTITY_UNPROVEN');
  if(proof.valid!==valid||proof.missing_bars!==missing||proof.closed_count!==window.filter(r=>r.closed).length||proof.warmup_available_closed_bars!==warmup||canonical(proof.blocked_reasons)!==canonical(reasons)||proof.state!==(reasons.length?'BLOCKED':'VERIFIED'))return false;
  const payload={schema:'chart-data-snapshot/1',source:'binance_usdm_live_trade_price',environment:'live_public',product:'USD-M',price_type:'LAST_PRICE',symbol,interval,stream_epoch:epoch,generation,data_revision:proof.data_revision,market,quality,rows:window.map(canonicalRow)};
  return sha256(canonical(payload))===proof.snapshot_hash&&sha256(canonical({interval,times:window.map(r=>r.time)}))===proof.grid_hash;
 }catch{return false;}
}
