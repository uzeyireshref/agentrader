import type {Drawing} from './drawings';
import type {BotDraft} from './botPrototype';
import {positionMetrics} from './position';
export function draftFromDrawing(draft:BotDraft,d:Drawing):BotDraft{
 if(d.deleted||!Number.isSafeInteger(d.revision)||d.revision<1)throw Error('Çizim silinmiş veya revizyonu geçersiz.');
 positionMetrics(d.geometry);
 return {...draft,kind:'SINGLE',orderType:'LIMIT',options:undefined,targets:undefined,breakEven:'',trailing:undefined,symbol:d.geometry.symbol,side:d.geometry.kind==='long_plan'?'Long':'Short',entry:d.geometry.anchors[0].price,stop:d.geometry.anchors[1].price,target:d.geometry.anchors[2].price,source:{drawingId:d.drawing_id,revision:d.revision,workspace:d.workspace_id},execution:draft.execution?{...draft.execution,condition:'IMMEDIATE'}:undefined};
}
