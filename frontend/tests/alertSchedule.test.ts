import {test} from 'node:test';
import assert from 'node:assert/strict';
import {schedulePreset,scheduleError,scheduleMode,scheduleSummary} from '../src/alertSchedule.ts';
import {alarmPayload,normalizeDefinition} from '../src/alertConditions.ts';
import {collectEvents,type AlertEvent} from '../src/alertNotifications.ts';
test('presets represent weekdays/full day and explicit custom windows with a retained zone',()=>{
 for(const mode of ['always','weekdays','workdays','custom']){const s=schedulePreset(mode,'Asia/Baku');assert.equal(scheduleMode(s),mode);assert.equal(scheduleError(s),'');assert.equal(s.timezone,'Asia/Baku');}
 const s=schedulePreset('custom','UTC');s.windows[0]={days:[4],start:'22:00',end:'04:00'};assert.equal(scheduleError(s),'');assert.match(scheduleSummary(s),/22:00–04:00/);
 s.windows[0].days=[];assert.match(scheduleError(s),/gün/);s.windows[0].days=[0];s.windows[0].start='04:00';assert.match(scheduleError(s),/saat/);s.timezone='Bad/Timezone';assert.match(scheduleError(s),/dilimi/);
});
test('legacy and sampled definitions keep per-alert schedule snapshots when editing modes',()=>{
 const legacy={name:'Scheduled',symbol:'BTCUSDT',interval:'5m',operator:'above',price:'100',frequency:'once',expires_at:null,message:'',notification_schedule:schedulePreset('weekdays','Asia/Baku')};
 const v=normalizeDefinition(legacy),live=alarmPayload({...v,evaluation:'intrabar'},'Live');assert.deepEqual(live.notification_schedule,legacy.notification_schedule);live.notification_schedule!.timezone='UTC';assert.equal(legacy.notification_schedule.timezone,'Asia/Baku');
 const closed=alarmPayload({...live,evaluation:undefined,frequency:'bar_close'},'Closed');assert.equal(closed.notification_schedule!.timezone,'UTC');
});
test('muted events are claimed silently and cannot be replayed when a delivery window opens',()=>{
 const event=(id:string,allowed:boolean):AlertEvent=>({id,name:'Alarm',symbol:'BTCUSDT',close:'100',message:'',candle_time:1,created_at:1000,notification_gate:{schema:'alert-notification-gate/1',allowed,reason:allowed?'IN_SCHEDULE':'OUTSIDE_SCHEDULE',timezone:'UTC'}});
 const result=collectEvents({seen:[],unread:[]},[event('allowed',true),event('muted',false)],1000);assert.deepEqual(result.fresh.map(e=>e.id),['allowed']);assert.deepEqual(result.state.unread,['allowed']);assert(result.state.seen.includes('muted'));
 assert.equal(collectEvents(result.state,[event('muted',true)],1001).fresh.length,0);
 const missing={...event('missing',true),notification_gate:undefined,definition:{notification_schedule:{}}};assert.equal(collectEvents(result.state,[missing],1001).fresh.length,0);
});
