import {useEffect,useRef,useState} from 'react';
import {useVisiblePolling} from './useVisiblePolling';
import {runBotJob,draftForServer,preflightDiagnosticMessage,type BotAnalytics} from './botApi';
import {draftError,type BotDraft} from './botPrototype';

function constraintLabel(code:string):string{
 const labels:Record<string,string>={
  ACCOUNT_SETTINGS_MISMATCH:'Seçilen kaldıraç veya teminat modu borsa hesabından farklı. Senaryo seçtiğiniz ayarlarla hesaplandı; hesap ayarı değiştirilmedi.',
  ACCOUNT_MODE_MISMATCH:'Seçilen pozisyon modu borsa hesabından farklı. Bu yalnız bir taslak senaryosudur; hesap modu değiştirilmedi.',
  CROSS_PORTFOLIO_REQUIRED:'Çapraz portföy etkisi tam doğrulanmadığı için likidasyon tahmini gösterilmiyor.',
  LIQUIDATION_UNAVAILABLE:'Likidasyon için gerekli basamak veya teminat bilgisi doğrulanamadı; tahmini değer üretilmedi.',
  ENTRY_CONDITION_WAITING:'Başlatma koşulu henüz sağlanmadı. Gösterilen piyasa senaryosu güncel Mark fiyatını kullanır.',
 };
 return Object.hasOwn(labels,code)?labels[code]:preflightDiagnosticMessage({category:'PREFLIGHT',reason:code})??'Bu senaryo işleme uygunluk onayı değildir. Borsa filtreleri ve risk koşulları ayrı ön kontrolde denetlenecek.';
}

export default function BotPlanAnalytics({draft,active,enabled,readGate,onPending}:{draft:BotDraft;active:boolean;enabled:boolean;readGate?:{current:boolean};onPending?:(pending:boolean)=>void}){
 const key=JSON.stringify(draftForServer(draft)),valid=!draftError(draft);
 const latest=useRef(key),inFlight=useRef(false),next=useRef(0),mounted=useRef(true);
 latest.current=key;
 const [result,setResult]=useState<{key:string;data:BotAnalytics}|null>(null),[error,setError]=useState<{key:string;text:string}|null>(null),[pending,setPending]=useState(false),[now,setNow]=useState(Date.now());
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{next.current=Date.now()+1200;},[key,active,enabled]);
 useVisiblePolling(async()=>{
  setNow(Date.now());
  if(inFlight.current||readGate?.current||Date.now()<next.current)return;
  onPending?.(true);
  const requested=key;inFlight.current=true;setPending(true);next.current=Date.now()+5000;
  try{
   const job=await runBotJob<BotAnalytics>('ANALYZE_PLAN',{draft:JSON.parse(requested)});
   if(mounted.current&&latest.current===requested){
    if(job.state!=='SUCCEEDED'||!job.result)throw Error('Hesaplama tamamlanmadı; kayıtlı talebi inceleyin.');
    setResult({key:requested,data:job.result});setError(null);setNow(Date.now());
    next.current=Date.now()+5000;
   }
  }catch(e){if(mounted.current&&latest.current===requested){setError({key:requested,text:e instanceof Error?e.message:'Hesaplama doğrulanamadı.'});}next.current=Date.now()+30000;}
  finally{if(latest.current!==requested)next.current=Date.now()+1200;inFlight.current=false;onPending?.(false);if(mounted.current)setPending(false);}
 },()=>{},1000,active&&enabled&&valid);
 const data=result?.key===key?result.data:null;
 const age=data?Math.max(now,Date.now())/1000-Math.min(data.observed_at,(data.mark_local_time??data.mark_time)/1000):Infinity;
 const fresh=Boolean(data&&age>=0&&age<=15);
 const available=Boolean(data&&age>=0&&age<=60);
 const format=(v:string|undefined|null)=>v==null||!Number.isFinite(Number(v))?'—':new Intl.NumberFormat('tr-TR',{maximumFractionDigits:8,...(Number(v)!==0&&Math.abs(Number(v))<1e-8?{notation:'scientific' as const}:{})}).format(Number(v));
 const show=(v:string|undefined|null)=>available&&enabled?format(v):'—';
 const facts:[string,string|null|undefined][]=[[fresh?'Mark fiyatı · USDT':'Son hesaptaki Mark · USDT',data?.mark_price],['Seçilen bütçe · USDT',data?.requested_budget],['Nominal üst sınır · USDT',data?.notional_ceiling],['Başlangıç teminatı · USDT',data?.initial_margin],['İki yön masraf rezervi · USDT',data?.fee_reserve],['Stop risk rezervi · USDT',data?.stop_risk]];
 if(data?.theoretical&&!data.estimate_unavailable)facts.push(['Teorik miktar · baz varlık',data.theoretical_quantity],['Lot adımına göre miktar',data.rounded_quantity]);
 if(draft.kind==='SINGLE')facts.push(['Plan miktarı · baz varlık',data?.quantity],['Hedeflerde brüt kâr · USDT',data?.target_gross],['Hedef kârı − rezerv · USDT',data?.target_after_fee_reserve],['Brüt fiyat getirisi · %',data?.target_return_percent],['Rezerv sonrası ROE · %',data?.target_roe_percent],['Stop sonucu − rezerv · USDT',data?.stop_after_fee_reserve],['Getiri / risk',data?.reward_risk]);
 return <section className="bot-plan-analytics" data-fresh={fresh&&enabled} aria-label="Canlı plan hesaplaması"><header><h3>Canlı hesaplama</h3><small>{pending?'Güncelleniyor…':data?.estimate_unavailable&&enabled?'Sayısal tahmin üretilemedi':fresh&&enabled?'Taslak senaryosu hesaplandı':available&&enabled?'Son hesap · güncel değil':'Güncel hesaplama bekleniyor'}</small></header>
 {!valid?<p>Fiyat, bütçe ve risk alanlarını doldurun. Hesaplama otomatik başlayacak.</p>:!enabled?<p>Hesap bağlantısı hazır olduğunda hesaplama güncellenecek.</p>:data?.state==='WAITING_CONDITION'?<p>Başlatma koşulu henüz sağlanmadı; miktar ve risk sonucu hazır değil.</p>:<>
 {error?.key===key&&<p role="status" className="bot-field-error">{error.text}</p>}
 {available&&!fresh&&enabled&&<p role="status" className="bot-warning">Son hesap {Math.floor(age)} saniye önce. Aşağıdaki değerler güncel piyasa fiyatı değildir; yeni veri bekleniyor.</p>}
 {data?.state==='SCENARIO'&&<p className="bot-note">Taslak senaryosudur; işlem uygunluğu ayrı ön kontrolde belirlenir.</p>}
 {Boolean(data?.constraints?.length)&&<details className="bot-calculation-constraints"><summary>İşlem koşulları · {data?.constraints?.length} uyarı</summary>{data?.constraints?.map(code=><p className="bot-warning" key={code}>{constraintLabel(code)}</p>)}</details>}
 {data?.estimate_unavailable&&<p role="status">Neutral grid için miktar ve risk hesaplanamadı. İşlem koşullarını inceleyin.</p>}
 {data?.theoretical&&!data.estimate_unavailable&&<p className="bot-warning">Bu değerler teoriktir. Lot/minimum tutar veya risk koşulları geçilmeden emir miktarı olarak kullanılamaz.</p>}
 <dl>{facts.map(([label,value])=><div key={label}><dt>{label}</dt><dd>{show(value)}</dd></div>)}{data?.liquidation?.map(p=><div key={p.direction}><dt>{p.direction} tahmini likidasyon · USDT</dt><dd>{show(p.estimated_liquidation)}</dd></div>)}</dl>
 {data?.pnl_unavailable&&<p>priceMatch giriş fiyatı emir defterinde belirlenecek; kesin kâr ve ROE hesaplanamaz.</p>}{data&&data.strategy!=='SINGLE'&&<p>Grid için teminat ve likidasyon tam envanter senaryosudur. Kâr ve miktar, hücrelerin dolum yoluna bağlıdır; tek bir hedef kârı gösterilmez.</p>}
 </>}
 {data&&<p className="bot-note">Hesap verisi: {new Date(data.observed_at*1000).toLocaleTimeString('tr-TR')} · Hesaplama: {new Date((data.calculated_at??data.observed_at)*1000).toLocaleTimeString('tr-TR')}</p>}
 <p className="bot-note">Yeni sonuçtan 5 saniye sonra tekrar hesaplanır. 15 saniyeyi aşan sonuç “güncel değil” olarak işaretlenir; 60 saniyeden eski sonuç kaldırılır. Bu hesap emir veya işlem onayı değildir. Likidasyon model tahminidir{data?.margin_mode==='CROSSED'?'; çapraz modda kullanılabilir teminatın tamamı hesaba katılır':''}. Masraf rezervi motorun %0,1 × iki yön varsayımıdır; gerçek komisyon ve funding sonucu değiştirebilir.</p></section>;
}
