import {test} from 'node:test';
import assert from 'node:assert/strict';
import {selectedChannels,inheritChannels,channelsSummary,type ChannelPolicy} from '../src/alertChannels.ts';
import {collectEvents,eventChannels,type AlertEvent} from '../src/alertNotifications.ts';
import {alarmPayload,normalizeDefinition} from '../src/alertConditions.ts';
const policy=(changes={})=>({schema:'alert-notification-channels/1',mode:'custom',inApp:false,sound:false,desktop:false,...changes} as ChannelPolicy);
const event=(id:string,p:unknown):AlertEvent=>({id,name:id,symbol:'BTCUSDT',close:'100',message:'',created_at:1000,candle_time:1,definition:{notification_channels:p}});
test('channel selection inherits old preferences but malformed explicit policies fail closed',()=>{
 assert.deepEqual(selectedChannels(undefined),{inApp:true,sound:true,desktop:true});assert.deepEqual(selectedChannels(inheritChannels()),selectedChannels(undefined));
 for(const p of [null,{},policy({sound:1}),{...inheritChannels(),sound:true}])assert.deepEqual(selectedChannels(p),{inApp:false,sound:false,desktop:false});assert.equal(channelsSummary(policy()),'Yalnızca geçmiş');
});
test('per-channel selection and browser master preferences form an intersection',()=>{
 const e=event('sound',policy({sound:true}));assert.deepEqual(eventChannels(e,{inApp:true,sound:true,desktop:true}),{inApp:false,sound:true,desktop:false});assert.deepEqual(eventChannels(e,{inApp:true,sound:false,desktop:true}),{inApp:false,sound:false,desktop:false});
});
test('history-only records are claimed silently while selected channels retain unread receipts',()=>{
 const result=collectEvents({seen:[],unread:[]},[event('history',policy()),event('sound',policy({sound:true})),event('desktop',policy({desktop:true}))],1000);
 assert.deepEqual(result.fresh.map(e=>e.id),['desktop','sound']);assert.deepEqual(result.state.unread,['desktop','sound']);assert(result.state.seen.includes('history'));
 const muted={...event('muted',policy({sound:true})),notification_gate:{schema:'alert-notification-gate/1',allowed:false,reason:'OUTSIDE_SCHEDULE',timezone:'UTC'}};assert.equal(collectEvents(result.state,[muted],1000).fresh.length,0);
});
test('legacy-to-live-to-close editing retains channel snapshots without changing saved events',()=>{
 const p=policy({sound:true});const d=normalizeDefinition({name:'A',symbol:'BTCUSDT',interval:'5m',operator:'above',price:'100',frequency:'once',expires_at:null,message:'',notification_channels:p});
 const live=alarmPayload({...d,evaluation:'intrabar'},'Live');assert.deepEqual(live.notification_channels,p);live.notification_channels=inheritChannels();assert.deepEqual(d.notification_channels,p);assert.deepEqual(alarmPayload({...live,evaluation:undefined,frequency:'bar_close'},'Close').notification_channels,inheritChannels());
});
