import {useEffect,useRef,useState} from 'react';
import type {Preview} from './SignalPreview';
import {bindingHash} from './bindings';
import {canonical,sha256} from './evidence';

type Review={schema:'chart-plan-review/1';plan:Record<string,unknown>;plan_digest:string;source_binding_hash:string;preview_hash:string;preview_version:number;event_id:string;workspace:string;account_ref:string;risk_profile_hash:string;expires_at:number;checked_at:number;account_preflight:Record<string,unknown>;review_hash:string;state:string;approval_until:number|null;executed:false;order_authority:false};
type Job={request_id:string;state:string;expires_at?:number;result:null|{state:string;approval_until:number;plan_digest:string;review_hash:string;executed:false;order_requests:0};error_code:string|null};
const planStates:Record<string,string>={PENDING_APPROVAL:'Onay bekliyor',AUTHORIZED:'Onaylı',EXECUTING:'Giriş işleniyor',MANAGING:'Pozisyon yönetiliyor',NEEDS_REVIEW:'Yerel durum kontrolü gerekiyor',CLOSED:'Tamamlandı',EXPIRED:'Süresi doldu',CANCELED:'İptal edildi',REJECTED:'Reddedildi',SUPERSEDED:'Yeni sürüm var'};
export function validApprovalJob(value:unknown,requestId:string,review:Review):value is Job{
 const v=value as Job;
 return !!v&&v.request_id===requestId&&['PENDING','RUNNING','APPROVED','FAILED','EXPIRED','NEEDS_REVIEW'].includes(v.state)
  &&Number.isFinite(v.expires_at)&&(v.error_code===null||typeof v.error_code==='string')
  &&(v.state==='APPROVED'?!!v.result&&v.result.state==='AUTHORIZED'&&v.result.plan_digest===review.plan_digest
    &&v.result.review_hash===review.review_hash&&v.result.executed===false&&v.result.order_requests===0
    &&Number.isFinite(v.result.approval_until)&&v.result.approval_until>0&&v.result.approval_until<=review.expires_at:v.result===null);
}
export function validChartReview(value:unknown,preview:Preview):value is Review{
 try{
  const v=value as Review,{review_hash,state,approval_until,executed,order_authority,...scope}=v;
  const {plan_id,version,...execution}=v.plan;
  const {plan_id:ignored,version:ignoredVersion,...original}=preview.plan as unknown as Record<string,unknown>;
  return v.schema==='chart-plan-review/1'&&v.workspace==='main'&&v.event_id===preview.event_id&&v.preview_hash===preview.content_hash&&v.preview_version===preview.version
   &&executed===false&&order_authority===false&&typeof state==='string'&&Number.isFinite(v.expires_at)&&Number.isFinite(v.checked_at)
   &&/^[a-f0-9]{64}$/.test(v.account_ref)&&/^[a-f0-9]{64}$/.test(v.source_binding_hash)&&/^[a-f0-9]{64}$/.test(v.risk_profile_hash)
   &&typeof plan_id==='string'&&/^chart-[a-f0-9]{32}$/.test(plan_id)&&version===1
   &&bindingHash(execution)===bindingHash(original)&&sha256(canonical(v.plan))===v.plan_digest&&bindingHash(scope)===review_hash;
 }catch{return false;}
}

export default function ChartPlanApproval({preview,disabled}:{preview:Preview;disabled:boolean}){
 const [open,setOpen]=useState(false),[session,setSession]=useState<{enabled:boolean;authenticated:boolean}|null>(null),[secret,setSecret]=useState('');
 const [review,setReview]=useState<Review|null>(null),[worker,setWorker]=useState(false),[checked,setChecked]=useState(false),[ttl,setTtl]=useState(60);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[job,setJob]=useState<Job|null>(null),[now,setNow]=useState(Date.now()/1000);
 const serial=useRef(0),alive=useRef(true),locked=useRef(false),pending=useRef<{request_id:string;review_hash:string;plan_digest:string;preview_hash:string;account_ref:string;ttl_seconds:number}|null>(null);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;serial.current++;};},[]);
 useEffect(()=>{serial.current++;setReview(null);setChecked(false);setJob(null);pending.current=null;},[preview.content_hash]);
 useEffect(()=>{if(!open)return;const t=setInterval(()=>setNow(Date.now()/1000),1000);return()=>clearInterval(t);},[open]);
 async function load(allowNew=false){
  const seq=++serial.current;setError('');
  try{
   const s=await fetch('/api/session',{credentials:'same-origin'});if(!s.ok)throw Error();const status=await s.json();
   if(!alive.current||seq!==serial.current)return;setSession(status);
   if(!status.enabled||!status.authenticated){setReview(null);setWorker(false);return;}
   const r=await fetch('/api/chart-plans?'+new URLSearchParams({workspace:'main',event_id:preview.event_id}),{credentials:'same-origin'});
   if(!r.ok)throw Error();const data=await r.json();if(data.review&&!validChartReview(data.review,preview))throw Error();
   if(alive.current&&seq===serial.current){setReview(data.review);setWorker(data.worker_ready===true);setChecked(false);
    if(allowNew&&data.review?.state==='PENDING_APPROVAL'&&job&&['FAILED','EXPIRED','NEEDS_REVIEW'].includes(job.state)){setJob(null);pending.current=null;}
   }
  }catch{if(alive.current&&seq===serial.current){setReview(null);setError('Yerel plan incelemesi doğrulanamadı. Oturumu ve plan sürümünü yenile.');}}
 }
 useEffect(()=>{if(open)void load();},[open,preview.content_hash]);
 async function pair(){
  if(locked.current)return;locked.current=true;setBusy(true);setError('');
  try{const r=await fetch('/api/session',{method:'POST',headers:{Authorization:'Bearer '+secret},credentials:'same-origin'});if(!r.ok)throw Error();await load();}
  catch{if(alive.current)setError('Yerel erişim anahtarı doğrulanamadı.');}
  finally{locked.current=false;if(alive.current){setSecret('');setBusy(false);}}
 }
 async function approve(){
  if(!review||!checked||disabled||locked.current||review.expires_at<=Date.now()/1000||review.state!=='PENDING_APPROVAL'||!worker)return;
  locked.current=true;setBusy(true);setError('');const seq=serial.current;
  const request=pending.current??{request_id:crypto.randomUUID(),review_hash:review.review_hash,plan_digest:review.plan_digest,preview_hash:review.preview_hash,account_ref:review.account_ref,ttl_seconds:ttl};pending.current=request;
  try{
   const r=await fetch('/api/chart-plans/'+String(review.plan.plan_id)+'/approval-requests',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(request)});
   if(!r.ok)throw Error();const value=await r.json();if(!validApprovalJob(value,request.request_id,review))throw Error();
   if(alive.current&&seq===serial.current){setJob(value);if(value.state==='APPROVED')void load();}
  }catch{if(alive.current&&seq===serial.current)setError('Onay isteğinin sonucu doğrulanamadı. Aynı isteği tekrar sorgula; yeni emir gönderilmez.');}
  finally{locked.current=false;if(alive.current)setBusy(false);}
 }
 useEffect(()=>{
  if(!open||!job||!['PENDING','RUNNING'].includes(job.state))return;
  const seq=serial.current,t=setTimeout(async()=>{
   try{const r=await fetch('/api/chart-approvals/'+job.request_id,{credentials:'same-origin'});if(!r.ok)throw Error();const value=await r.json();if(!review||!validApprovalJob(value,job.request_id,review))throw Error();
    if(alive.current&&seq===serial.current){setJob(value);if(value.state==='APPROVED')void load();}
   }catch{if(alive.current&&seq===serial.current)setError('Onay sonucu okunamadı; plan durumunu yenile.');}
  },1000);return()=>clearTimeout(t);
 },[open,job,review]);
 const usable=preview.state==='PREVIEW_ONLY'&&preview.expires_at>now&&!disabled;
 return <details onToggle={e=>setOpen(e.currentTarget.open)}><summary>Yerel demo planını incele ve onayla</summary>{open&&<section className="chart-plan-approval" aria-label="Demo planı kullanıcı onayı">
  <p>Onay belirli demo hesabı, plan ve süre içindir. Bu ekranda emir gönderilmez; yürütme ayrı terminal komutudur.</p>
  {session?.enabled===false&&<p>Yerel onay oturumu kapalı. Sunucu için AGENTRADER_WEB_TOKEN tanımlanmalı; demo hesap anahtarları tarayıcıya girilmez.</p>}
  {session?.enabled&&!session.authenticated&&<form onSubmit={e=>{e.preventDefault();void pair();}}><label>Yerel erişim anahtarı<input type="password" autoComplete="off" value={secret} onChange={e=>setSecret(e.target.value)} disabled={busy}/></label><button disabled={busy||!secret}>Yerel oturumu aç</button></form>}
  {session?.authenticated&&!review&&<><p>Bu önizleme için yerel hesap incelemesi hazırlanmalı:</p><code>python -m agentrader web review-preview main {preview.event_id} {preview.version}</code></>}
  {review&&<>
   <p>Plan {String(review.plan.plan_id)} · v1 · {planStates[review.state]??'Durum yeniden okunmalı'}</p><p title={review.account_ref}>Demo hesap kimliği: {review.account_ref.slice(0,16)}…</p>
   <p>Plan özeti: <code>{review.plan_digest}</code></p><p>Son hesap kontrolü: {new Date(review.checked_at*1000).toLocaleString('tr-TR')} · Onay işçisi: {worker?'hazır':'kapalı veya meşgul'}</p>
   <details><summary>Tam plan ve hesap/risk sonucu</summary><pre>{JSON.stringify({plan:review.plan,account_preflight:review.account_preflight},null,2)}</pre></details>
   <p>Onay sırasında hesap, risk ve grafik kaynağı yeniden kontrol edilir. Yürütme bu onayı tek giriş için kullanabilir.</p>
   <fieldset disabled={busy||!usable||!worker||review.state!=='PENDING_APPROVAL'||review.expires_at<=now||!!job}>
    <label>Onay süresi<select value={ttl} onChange={e=>setTtl(Number(e.target.value))}><option value={30}>30 saniye</option><option value={60}>1 dakika</option><option value={120}>2 dakika</option></select></label>
    <label className="approval-consent"><input type="checkbox" checked={checked} onChange={e=>setChecked(e.target.checked)}/>Planı ve demo hesap kimliğini kontrol ettim</label>
    <button disabled={!checked} onClick={()=>void approve()}>{job?.state==='APPROVED'?'Onay kaydedildi':job?'Onay kontrol ediliyor…':busy?'Onay isteniyor…':pending.current?'Aynı onay isteğini tekrar sorgula':'Bu demo planına süreli onay ver'}</button>
   </fieldset>
   {!worker&&<p>Onay için ayrı yerel işçi çalışmalı: <code>python -m agentrader web approval-worker</code></p>}
   {review.expires_at<=now&&<p>Planın süresi doldu; yeni sinyal gerekiyor.</p>}
  </>}
  {job&&<p role="status">{job.state==='APPROVED'?(job.result!.approval_until>now?'Demo planı onaylandı; emir gönderilmedi.':'Kaydedilmiş onayın süresi doldu.') :job.state==='PENDING'?'Onay isteği kuyruğa alındı; henüz onaylanmadı.':job.state==='RUNNING'?'Hesap ve kaynak yeniden kontrol ediliyor.':'Onay tamamlanmadı: '+job.state}</p>}
  {error&&<p role="alert">{error}</p>}<button disabled={busy} onClick={()=>void load(true)}>Yerel plan durumunu yenile</button>
 </section>}</details>;
}
