export type AlertEvent={id:string;name:string;symbol:string;close:string;candle_time:number;created_at:number;message:string};
export type NotificationPreferences={inApp:boolean;sound:boolean;desktop:boolean};
export const notificationKey='agentrader.alert-notifications.v1';
export const receiptKey='agentrader.alert-receipts.v1';
export const defaultPreferences:NotificationPreferences={inApp:true,sound:false,desktop:false};
export type Receipts={seen:string[];unread:string[]};
export function preferences(raw:string|null):NotificationPreferences{
 try{const v=JSON.parse(raw??'null');return {inApp:typeof v?.inApp==='boolean'?v.inApp:true,sound:v?.sound===true,desktop:v?.desktop===true};}catch{return {...defaultPreferences};}
}
export function receipts(raw:string|null):Receipts|null{
 try{const v=JSON.parse(raw??'null');if(!Array.isArray(v?.seen)||!Array.isArray(v?.unread))return null;return {seen:v.seen.filter((x:unknown)=>typeof x==='string').slice(-1000),unread:v.unread.filter((x:unknown)=>typeof x==='string').slice(-100)};}catch{return null;}
}
export function validEvent(v:unknown):v is AlertEvent{
 const e=v as AlertEvent;return !!e&&typeof e.id==='string'&&e.id.length>0&&['name','symbol','close','message'].every(k=>typeof (e as unknown as Record<string,unknown>)[k]==='string')&&Number.isFinite(e.created_at)&&Number.isFinite(e.candle_time);
}
// First installation baselines history. Later polls claim each event before delivery.
export function collectEvents(previous:Receipts|null,events:AlertEvent[],now:number){
 const seen=new Set(previous?.seen??[]),unread=new Set(previous?.unread??[]),fresh:AlertEvent[]=[];
 for(const e of [...events].reverse()){
  if(seen.has(e.id))continue;seen.add(e.id);
  if(previous){unread.add(e.id);if(e.created_at>=now-120&&e.created_at<=now+5)fresh.push(e);}
 }
 return {state:{seen:[...seen].slice(-1000),unread:[...unread].slice(-100)},fresh};
}
export class AlertSound{
 private context:AudioContext|null=null;
 async enable(){
  if(!this.context||this.context.state==='closed')this.context=new AudioContext();
  await this.context.resume();if(this.context.state!=='running')throw Error('AUDIO_BLOCKED');
 }
 play(){
  const c=this.context;if(!c||c.state!=='running')throw Error('AUDIO_BLOCKED');
  for(const [offset,hz] of [[0,740],[.18,990]]){const o=c.createOscillator(),g=c.createGain(),t=c.currentTime+offset;o.frequency.value=hz;g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(.12,t+.015);g.gain.exponentialRampToValueAtTime(.001,t+.15);o.connect(g);g.connect(c.destination);o.start(t);o.stop(t+.17);o.onended=()=>{o.disconnect();g.disconnect();};}
 }
 close(){void this.context?.close().catch(()=>{});this.context=null;}
}
