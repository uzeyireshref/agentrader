import type {IChartApi} from 'lightweight-charts';
/** Restore exactly the user's previous gesture options, once on every exit path. */
export function lockChartInteraction(chart:Pick<IChartApi,'options'|'applyOptions'>):()=>void{
 const options=structuredClone({handleScroll:chart.options().handleScroll,handleScale:chart.options().handleScale});
 chart.applyOptions({handleScroll:false,handleScale:false});
 let locked=true;return()=>{if(locked){locked=false;chart.applyOptions(options);}};
}
