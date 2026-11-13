import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeDefinition,alarmPayload,defaultCondition,isBand,isMovement,operators,operandName} from '../src/alertConditions.ts';
test('legacy price alert migrates losslessly to one compound condition without changing the saved definition',()=>{
 const d={name:'Legacy',symbol:'BTCUSDT',interval:'15m',operator:'cross_down',price:'123.45',frequency:'once',expires_at:null,message:'Note'},before=structuredClone(d),v=normalizeDefinition(d);
 assert.equal(v.schema,'technical-alert/2');assert.equal(v.match,'all');assert.deepEqual(v.conditions,[{...defaultCondition(),operator:'cross_down',right:{type:'value',value:'123.45'}}]);assert.deepEqual(d,before);
 const copy=normalizeDefinition(v);copy.conditions[0].right={type:'value',value:'99'};assert.deepEqual(v.conditions[0].right,{type:'value',value:'123.45'});
});
test('condition editor discriminates channel bounds, movement lookback and all 17 operators',()=>{
 assert.equal(Object.keys(operators).length,17);for(const op of ['inside','outside','enter','exit'])assert.equal(isBand(op),true);for(const op of ['move_up','move_down','move_up_pct','move_down_pct','rising','falling'])assert.equal(isMovement(op),true);assert.equal(isBand('cross'),false);assert.equal(isMovement('cross'),false);assert.equal(operandName({type:'market',field:'volume'}),'Hacim');assert.equal(operandName({type:'value',value:'-0.01'}),'-0.01');
});

test('multi-timeframe definitions retain independent condition intervals and clone snapshots',()=>{
 const d=normalizeDefinition({schema:'technical-alert/3',name:'MTF',symbol:'BTCUSDT',interval:'15m',frequency:'bar_close',expires_at:null,message:'',match:'all',conditions:[{...defaultCondition(),interval:'1h'},{...defaultCondition(),interval:'15m'}]});
 assert.equal(d.schema,'technical-alert/3');assert.deepEqual(d.conditions.map(c=>c.interval),['1h','15m']);const copy=normalizeDefinition(d);copy.conditions[0].interval='4h';assert.equal(d.conditions[0].interval,'1h');
});

test('intrabar payload resolves every condition interval and roundtrips without altering legacy close mode',()=>{
 const base=normalizeDefinition({name:'Live',symbol:'BTCUSDT',interval:'5m',operator:'above',price:'100',frequency:'once',expires_at:null,message:''});
 const live=alarmPayload({...base,evaluation:'intrabar',frequency:'minute'},'Live');assert.equal(live.schema,'technical-alert/4');assert.equal(live.conditions[0].interval,'5m');assert.equal(normalizeDefinition(live).frequency,'minute');assert.equal(live.evaluation,'intrabar');
 const close=alarmPayload({...live,evaluation:undefined,frequency:'bar_close'},'Close');assert.equal(close.schema,'technical-alert/3');assert(!('evaluation' in close));assert.equal(close.frequency,'bar_close');const old=alarmPayload(base,'Old');assert.equal(old.schema,'technical-alert/2');assert.equal(old.frequency,'once');assert(!('evaluation' in old));
});
