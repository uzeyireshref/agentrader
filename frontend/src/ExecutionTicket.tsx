import {defaultExecution,type BotDraft,type ExecutionDraft} from './botPrototype';

export default function ExecutionTicket({draft,onChange}:{draft:BotDraft;onChange:(patch:Partial<BotDraft>)=>void}){
 const e=draft.execution??defaultExecution;
 const update=(patch:Partial<ExecutionDraft>)=>onChange({execution:{...e,...patch}});
 return <fieldset className="bot-grid-fields"><legend>Hesap ve başlatma</legend><div className="bot-field-grid">
 <label>Kaldıraç<input required inputMode="numeric" value={e.leverage} onChange={event=>update({leverage:event.target.value})}/></label>
 <label>Marjin modu<select value={e.margin} onChange={event=>update({margin:event.target.value as ExecutionDraft['margin']})}><option value="ISOLATED">Isolated</option><option value="CROSSED">Cross</option></select></label>
 <label>Pozisyon modu<select disabled={draft.kind==='NEUTRAL'} value={draft.kind==='NEUTRAL'?'hedge':e.positionMode} onChange={event=>update({positionMode:event.target.value as ExecutionDraft['positionMode']})}><option value="one-way">One-way</option><option value="hedge">Hedge</option></select></label>
 <label>Sapma toleransı · bps<input required inputMode="decimal" value={e.driftBps} onChange={event=>update({driftBps:event.target.value})}/></label>
 {(draft.kind!=='SINGLE'||draft.orderType==='MARKET')&&<><label>Başlatma koşulu<select value={e.condition} onChange={event=>update({condition:event.target.value as ExecutionDraft['condition']})}><option value="IMMEDIATE">Anında piyasa başlangıcı</option><option value="MARK_AT_OR_BELOW">Mark fiyatı eşit veya altında</option><option value="MARK_AT_OR_ABOVE">Mark fiyatı eşit veya üstünde</option></select></label>{e.condition!=='IMMEDIATE'&&<label>Tetik fiyatı · USDT<input required inputMode="decimal" value={e.trigger} onChange={event=>update({trigger:event.target.value})}/></label>}</>}
 </div><p className="bot-note">Bu seçimler hesap ayarını değiştirmez. Gerçek hesap modu, kaldıraç basamağı ve marjin uygunluğu hesap bağlandığında ayrıca doğrulanacak.{draft.kind!=='SINGLE'?' Grid döngüsü artırma ve yeniden giriş izni gerektirir; bu taslak izin veya yürütme yetkisi üretmez.':''}</p></fieldset>;
}
