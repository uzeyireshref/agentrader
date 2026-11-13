import type {ISeriesPrimitive,SeriesAttachedParameter,Time} from 'lightweight-charts';
import {createCoalescedTask} from './vendor/lwc-toolkit/coalesced-task.ts';
/** Coalesce chart invalidations after layout; nothing repeats while idle. */
export class ProjectionPrimitive implements ISeriesPrimitive<Time>{
 private update:()=>void=()=>{};
 private task;
 constructor(project:()=>void){this.task=createCoalescedTask(project);}
 attached(p:SeriesAttachedParameter<Time>){this.update=p.requestUpdate;this.update();}
 detached(){this.task.cancel();this.update=()=>{};}
 updateAllViews(){this.task.schedule();}
 invalidate(){this.update();}
}
