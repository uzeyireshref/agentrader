import type {IChartApi,ISeriesApi} from 'lightweight-charts';
export type PanePreset='balanced'|'price-focus';
export type PaneSeries=Pick<ISeriesApi<'Line'>,'getPane'>;
const volumeScale=new WeakMap<ISeriesApi<'Histogram'>,{automatic:boolean;range:{from:number;to:number}|null}>();
/** Price always owns pane0; optional panes are resolved from their live series. */
export function arrangeVolume(chart:IChartApi,volume:ISeriesApi<'Histogram'>,visible:boolean){
 if(!visible){if(volume.getPane().paneIndex()!==0)volumeScale.set(volume,{automatic:volume.priceScale().options().autoScale,range:volume.priceScale().getVisibleRange()});volume.applyOptions({visible:false,priceScaleId:'volume-hidden'});if(volume.getPane().paneIndex()!==0)volume.moveToPane(0);return;}
 if(volume.getPane().paneIndex()===0){volume.moveToPane(chart.panes().length);const index=volume.getPane().paneIndex();if(index!==1)chart.swapPanes(1,index);}
 volume.applyOptions({visible:true,priceScaleId:'right'});volume.priceScale().applyOptions({mode:0});
 const saved=volumeScale.get(volume);if(saved){if(!saved.automatic&&saved.range)volume.priceScale().setVisibleRange(saved.range);else volume.priceScale().applyOptions({autoScale:true});volumeScale.delete(volume);}
}
export function applyPaneLayout(price:PaneSeries,volume:PaneSeries|null,rsi:PaneSeries|null,preset:PanePreset){
 price.getPane().setStretchFactor(preset==='price-focus'?7:4);
 if(volume&&volume.getPane().paneIndex()!==0)volume.getPane().setStretchFactor(1);
 if(rsi)rsi.getPane().setStretchFactor(preset==='price-focus'?1:1.5);
}
