import type {LiveSession,PlanRow} from './botApi';

/** A plan id alone is not an executable reference: every selection pins a version. */
export const planSelectionKey=(row:PlanRow)=>`${row.plan.plan_id}@${row.plan.version}`;

export function batchPlanRows(plans:PlanRow[],selected:string[]):PlanRow[]{
 if(!selected.length||selected.length>5||new Set(selected).size!==selected.length)
  throw Error('1–5 farklı plan sürümü seçin.');
 const rows=selected.map(key=>plans.find(row=>planSelectionKey(row)===key));
 if(rows.some(row=>!row||row.state!=='AUTHORIZED'))
  throw Error('Seçili plan sürümü artık yetkili değil veya bulunamadı. Hesabı yenileyip planları yeniden seçin.');
 const found=rows as PlanRow[];
 if(found.some(row=>row.plan.execution?.strategy!=='SINGLE'))throw Error('Toplu giriş yalnız tek işlem planlarını destekler.');
 if(new Set(found.map(row=>row.plan.symbol)).size!==found.length)
  throw Error('Toplu giriş için her planda farklı bir sözleşme seçin.');
 return found;
}

export function reversePlanRows(plans:PlanRow[],session?:LiveSession):PlanRow[]{
 return plans.filter(row=>row.plan.execution?.strategy==='SINGLE'&&
  ['PENDING_APPROVAL','PENDING_ACTIVATION'].includes(row.state)&&
  (!session||(row.plan.symbol===session.symbol&&row.plan.direction!==session.plan.direction)));
}
