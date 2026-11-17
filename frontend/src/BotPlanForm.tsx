import {useRef,useState,useId} from 'react';
import {draftValidation} from './botDraftValidation';
import GridTicket from './GridTicket';
import ExecutionTicket from './ExecutionTicket';
import SingleManagement from './SingleManagement';
import PlanTrailing from './PlanTrailing';
import LimitTicketOptions from './LimitTicketOptions';
import {defaultGrid,updateBotDraft,type BotDraft} from './botPrototype';

export default function BotPlanForm({draft,onDraft,onPreview,symbols=[],pending=false,canPreview=true,canSave=true}:{draft:BotDraft;onDraft:(d:BotDraft)=>void;onPreview:(mode?:'SAVE_PLAN'|'PREVIEW_PLAN_AUTHORIZATION')=>void;symbols?:string[];pending?:boolean;canPreview?:boolean;canSave?:boolean}){
 const [submitted,setSubmitted]=useState(false);
 const formRef=useRef<HTMLFormElement>(null),errorId=useId();
 const validation=draftValidation(draft),errors=submitted?validation.fields:{};
 const submit=(mode?:'SAVE_PLAN'|'PREVIEW_PLAN_AUTHORIZATION')=>{
  setSubmitted(true);
  if(validation.message){
   requestAnimationFrame(()=>{
    const form=formRef.current;
    const invalid=form?.querySelector<HTMLElement>('[aria-invalid="true"]');
    const target=invalid??form?.querySelector<HTMLElement>('[data-validation-summary]');
    let parent=target?.parentElement;while(parent){if(parent instanceof HTMLDetailsElement)parent.open=true;parent=parent.parentElement;}
    target?.focus();
   });
   return;
  }
  onPreview(mode);
 };
 const update=(patch:Partial<BotDraft>)=>onDraft(updateBotDraft(draft,patch));
 return <aside className="bot-ticket"><header><h2>Yeni Demo planı</h2><span className="bot-ticket-status">Ön kontrol ve açık onay gerekli</span></header><form ref={formRef} noValidate onSubmit={e=>{e.preventDefault();submit();}}>{submitted&&validation.message&&<p className="bot-field-error bot-validation-summary" data-validation-summary tabIndex={-1} role="alert">{validation.message}</p>}<fieldset className="bot-live-fieldset" disabled={pending}><section className="bot-plan-step bot-plan-identity" aria-label="Strateji ve sözleşme"><div className="bot-ticket-section-title"><span>01</span> Strateji ve sözleşme</div><label>Plan türü<select name="plan-kind" value={draft.kind} onChange={e=>update({kind:e.target.value as BotDraft['kind'],grid:draft.grid??{...defaultGrid}})}>{[['SINGLE','Tek işlem'],['GRID','Yönlü grid'],['NEUTRAL','Nötr grid']].map(([value,label])=><option value={value} key={value}>{label}</option>)}</select></label><label>Sözleşme<select name="symbol" value={draft.symbol} onChange={e=>update({symbol:e.target.value})}>{Array.from(new Set([draft.symbol,...symbols])).map(s=><option key={s}>{s}</option>)}</select></label><div hidden={draft.kind==='NEUTRAL'} className="bot-direction" role="group" aria-label="Demo işlem yönü">{(['Long','Short'] as const).map(side=><button type="button" key={side} aria-pressed={draft.side===side} onClick={()=>update({side})}>{side}</button>)}</div>
 </section><section className="bot-plan-step bot-plan-risk" aria-label="Giriş ve risk"><div className="bot-ticket-section-title"><span>02</span> Giriş ve risk</div>{draft.kind!=='SINGLE'?<GridTicket draft={draft} onChange={update} errors={errors} errorId={errorId}/>:<><label>Emir türü<select name="order-type" value={draft.orderType??'LIMIT'} onChange={e=>update({orderType:e.target.value as BotDraft['orderType']})}><option value="LIMIT">Limit</option><option value="MARKET">Market</option></select></label><div className="bot-field-grid">{([['entry',draft.orderType==='MARKET'||draft.options?.priceMatch?'Risk referans fiyatı · USDT':'Limit fiyatı · USDT'],['amount','İşlem bütçesi · USDT'],['stop','Stop fiyatı · USDT'],['target','İlk hedef · USDT']] as const).map(([key,label])=><label key={key}>{label}<input aria-invalid={Boolean(errors[key])} aria-describedby={errors[key]?`${errorId}-${key}`:undefined} name={key} autoComplete="off" inputMode="decimal" required value={draft[key]} onChange={e=>update({[key]:e.target.value})}/>{errors[key]&&<small className="bot-field-error" id={`${errorId}-${key}`}>{errors[key]}</small>}</label>)}</div><SingleManagement draft={draft} onChange={update}/>{draft.orderType!=='MARKET'&&<LimitTicketOptions draft={draft} onChange={update}/>}</>}
 </section><section className="bot-plan-step bot-plan-options" aria-label="İleri ayarlar"><div className="bot-ticket-section-title"><span>03</span> İleri ayarlar</div><details><summary>Hesap ve başlatma ayarları</summary><ExecutionTicket draft={draft} onChange={update}/></details><PlanTrailing draft={draft} onChange={update}/><div className="bot-ticket-submit"><small>Önce hesap kontrolü, ardından ayrı işlem onayı.</small><button disabled={!canPreview} type="submit" className="bot-primary">{pending?'Ön kontrol bekleniyor…':'Hesapta ön kontrol yap'}</button></div><details><summary>Toplu giriş ve ters yön için hazırlık</summary><p>Taslak kaydı emir göndermez ve yetki vermez. Toplu giriş ayrıca süreli plan yetkisi ve toplu işlem onayı gerektirir.</p><button type="button" disabled={!canSave} onClick={()=>submit('SAVE_PLAN')}>Plan taslağını kaydet</button><button type="button" disabled={!canPreview||draft.kind!=='SINGLE'} onClick={()=>submit('PREVIEW_PLAN_AUTHORIZATION')}>Toplu giriş yetkisini incele</button></details></section></fieldset></form></aside>;
}
