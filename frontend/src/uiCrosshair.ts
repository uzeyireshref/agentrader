import type {Candle} from './types';
export type UiCrosshair={time:number|null;price:string|null;pane:number|null;hover_candle:Record<string,unknown>|null};
export const emptyCrosshair=():UiCrosshair=>({time:null,price:null,pane:null,hover_candle:null});
export function currentUiCrosshair(rows:Candle[],hover:UiCrosshair):UiCrosshair{
 if(hover.time===null||hover.hover_candle===null)return hover;
 const row=rows.find(r=>r.time===hover.time);if(!row)return emptyCrosshair();
 const candle:Record<string,unknown>={time:row.time,closed:row.closed};
 for(const field of ['open','high','low','close','volume','quote_volume'] as const)candle[field]=typeof row.exact?.[field]==='string'?row.exact[field]:String(row[field]);
 return {...hover,hover_candle:candle};
}
