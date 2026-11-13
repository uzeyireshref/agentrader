import {applyPacket,type ChartState,type Packet} from './types.ts';
/** A transport heartbeat alone must never clear a failed chart paint. */
export class RenderRecovery {
 private invalid=false;
 get pending(){return this.invalid;}
 run(full:boolean,paint:(full:boolean)=>void):boolean{
  try{paint(full||this.invalid);this.invalid=false;return true;}
  catch{this.invalid=true;return false;}
 }
}
export function applyRenderedPacket(state:ChartState,packet:Packet,recovery:RenderRecovery,paint:(next:ChartState,full:boolean)=>void):ChartState{
 const next=applyPacket(state,packet);if(next===state)return state;
 const changed=next.generation!==state.generation||next.sequence!==state.sequence;
 if((changed||recovery.pending)&&!recovery.run(packet.type==='snapshot',full=>paint(next,full)))return {...next,status:'RENDER_ERROR'};
 return next;
}
