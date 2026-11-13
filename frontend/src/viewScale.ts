import {PriceScaleMode,type ISeriesApi} from 'lightweight-charts';
export type ViewScale='LINEAR'|'LOG';
export const scalePolicySchema='chart-scale-policy/1';
export const logBlockedKinds=['trend','ray','extended_line','parallel_channel'];
export const supportsView=(kind:string,mode:ViewScale,schema?:string)=>mode==='LINEAR'||schema==='chart-channel-family/1'||['text','note','price_label','cursor','line','horizontal','horizontal_ray','zone','fibonacci','fibonacci_extension','long_plan','short_plan','ruler'].includes(kind);
export const scaleBlockMessage='Log görünümde eğimli çizim BLOCKED. Fiyatlar korunur; görmek ve düzenlemek için lineer görünüme dön.';
export function readViewScale(storage?:Pick<Storage,'getItem'>):ViewScale{try{const value=JSON.parse((storage??localStorage).getItem('agentrader.chartView')??'null');return value?.schema==='chart-view/1'&&value.price_scale==='LOG'?'LOG':'LINEAR';}catch{return 'LINEAR';}}
export function saveViewScale(mode:ViewScale,storage?:Pick<Storage,'setItem'>){try{(storage??localStorage).setItem('agentrader.chartView',JSON.stringify({schema:'chart-view/1',price_scale:mode}));}catch{/* Browser storage is optional. */}}
type ScaleSeries=Pick<ISeriesApi<'Candlestick'>,'priceScale'>;
export function nativeViewScale(series:ScaleSeries):ViewScale|null{const mode=series.priceScale?.().options().mode??0;return mode===0?'LINEAR':mode===1?'LOG':null;}
/** View-only change: never writes anchors, calculations, or a drawing revision. */
export function applyViewScale(series:ScaleSeries,mode:ViewScale){
 // Refit on view changes. The installed native engine does not safely convert
 // customized price ranges through the public mode/setVisibleRange combination.
 series.priceScale().applyOptions({mode:mode==='LOG'?PriceScaleMode.Logarithmic:PriceScaleMode.Normal,autoScale:true});
}
