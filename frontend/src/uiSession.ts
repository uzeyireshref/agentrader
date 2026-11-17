/** Transient client reports; neither a market proof nor an order permission. */
export const chartUiVisibility=(documentVisible:boolean,chartVisible=true):'visible'|'hidden'=>documentVisible&&chartVisible?'visible':'hidden';
export type UiPolicy={schema_version:'chart-ui-policy/1';server_instance_id:string;ttl_seconds:number;min_publish_interval_ms:number;heartbeat_seconds:number;authentication_required:boolean};
export type UiSnapshot=Record<string,unknown>;
export type UiEnvelope={schema_version:'chart-ui-session/1';server_instance_id:string;sequence:number;client_time_ms:number;visibility:'visible'|'hidden';client_status:'CONNECTED'|'OFFLINE'|'CLOSED';snapshot:UiSnapshot};
export type UiReply={status:number;body?:{error?:{code?:string};sequence?:number}};
type Environment={visibility:'visible'|'hidden';online:boolean;clientTime:number};
type Options={policy:UiPolicy;collect:()=>UiSnapshot;environment:()=>Environment;send:(id:string,key:string,value:UiEnvelope,keepalive:boolean)=>Promise<UiReply>;refreshPolicy?:()=>Promise<UiPolicy|null>;identity?:(id:string,status:string)=>void;random?:()=>{id:string;key:string}};

function randomIdentity(){const bytes=crypto.getRandomValues(new Uint8Array(32));return {id:'ui-'+crypto.randomUUID(),key:[...bytes].map(v=>v.toString(16).padStart(2,'0')).join('')};}
export class UiPublisher{
 private id='';private key='';private sequence=0;private busy=false;private stopped=false;private dirty=true;
 private signature='';private lastAttempt=-Infinity;private retryAt=0;
 constructor(private options:Options){this.rotate();}
 get sessionId(){return this.id;}
 markDirty(){this.dirty=true;}
 resume(){if(this.stopped){this.stopped=false;this.retryAt=0;this.rotate();}this.markDirty();}
 private status(status:string){this.options.identity?.(this.id,status);}
 private rotate(){const fresh=(this.options.random??randomIdentity)();this.id=fresh.id;this.key=fresh.key;this.sequence=0;this.signature='';this.lastAttempt=-Infinity;this.dirty=true;this.status('CONNECTING');}
 private envelope(status:UiEnvelope['client_status']):UiEnvelope{const env=this.options.environment();return {schema_version:'chart-ui-session/1',server_instance_id:this.options.policy.server_instance_id,sequence:++this.sequence,client_time_ms:env.clientTime,visibility:env.visibility,client_status:status,snapshot:this.options.collect()};}
 private async issue(value:UiEnvelope,now:number,keepalive=false){
  const id=this.id,key=this.key;this.lastAttempt=now;this.signature=JSON.stringify({snapshot:value.snapshot,visibility:value.visibility,client_status:value.client_status});
  try{
   const reply=await this.options.send(id,key,value,keepalive);
   if(id!==this.id||value.sequence!==this.sequence||this.stopped)return;
   if(reply.status>=200&&reply.status<300){this.status(value.visibility==='hidden'?'HIDDEN':value.client_status==='OFFLINE'?'OFFLINE':'READY');return;}
   this.signature='';
   const code=reply.body?.error?.code;
   if(code==='UI_SESSION_SERVER_RESTARTED'){
    const policy=await this.options.refreshPolicy?.();if(policy)this.options.policy=policy;this.rotate();
   }else if(['UI_SESSION_EXPIRED','UI_SESSION_CLOSED','UI_SESSION_UNKNOWN','UI_SESSION_SEQUENCE_CONFLICT','UI_PUBLISHER_MISMATCH'].includes(code??'')){
    // Retire an uncertain old identity so a delayed first request cannot reappear as visible.
    const retired={...value,sequence:++this.sequence,visibility:'hidden' as const,client_status:'CLOSED' as const};
    void this.options.send(id,key,retired,true).catch(()=>{});this.rotate();
   }else this.status(reply.status===401||reply.status===403?'UNAUTHORIZED':'DISCONNECTED');
   this.dirty=true;this.retryAt=now+(reply.status===429?1000:5000);
  }catch{if(!this.stopped&&id===this.id&&value.sequence===this.sequence){this.signature='';this.status('DISCONNECTED');this.dirty=true;this.retryAt=now+5000;}}
 }
 async step(now:number){
  const env=this.options.environment();if(this.stopped||this.busy||env.visibility!=='visible'||!env.online||now<this.retryAt||now-this.lastAttempt<this.options.policy.min_publish_interval_ms)return;
  const heartbeat=now-this.lastAttempt>=this.options.policy.heartbeat_seconds*1000;
  if(!this.dirty&&!heartbeat)return;
  const state=this.options.collect(),signature=JSON.stringify({snapshot:state,visibility:env.visibility,client_status:'CONNECTED'});this.dirty=false;
  if(signature===this.signature&&!heartbeat)return;
  this.busy=true;
  try{await this.issue({...this.envelope('CONNECTED'),snapshot:state},now);}finally{this.busy=false;}
 }
 async restrict(now:number,status:'OFFLINE'|'CLOSED'|undefined=undefined){
  if(this.stopped)return;
  const env=this.options.environment();
  if(!status&&env.visibility==='visible'&&env.online){this.markDirty();return;}
  const value=this.envelope(status??(env.online?'CONNECTED':'OFFLINE'));
  if(status==='CLOSED'){this.stopped=true;value.visibility='hidden';this.status('CLOSED');}
  await this.issue(value,now,true);
 }
}
