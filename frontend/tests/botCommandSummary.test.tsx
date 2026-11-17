import {test} from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import BotCommandSummary from '../src/BotCommandSummary';
import type {CommandResult} from '../src/botApi';
const render=(operation:string,scope:Record<string,unknown>,parameters:Record<string,unknown>)=>renderToStaticMarkup(<BotCommandSummary command={{command_id:'cmd-demo',state:'PREPARED',request:{operation,scope,parameters}} as CommandResult}/>);
test('review exposes account-wide and cross-product effects in ordinary language',()=>{
 const account=render('CANCEL_ACCOUNT_ORDERS',{account_wide:true},{include_foreign:true});
 assert.match(account,/Hesabın tamamı/);assert.match(account,/hesabın tamamını etkiler/);assert.match(account,/Diğer istemcilerin emirleri/);
 const shared=render('SET_POSITION_MODE',{affected_products:['USD-M','COIN-M']},{enabled:true});
 assert.match(shared,/USD-M/);assert.match(shared,/COIN-M/);assert.match(shared,/Hedge/);
});
test('review preserves exact quantities and clearly identifies every batch plan version',()=>{
 assert.match(render('INCREASE_POSITION',{symbol:'BTCUSDT'},{quantity:'0.000000000000000001',price_floor:'100',price_ceiling:'101'}),/0\.000000000000000001/);
 const batch=render('BATCH_CREATE_ORDERS',{symbols:['BTCUSDT','ETHUSDT']},{plans:[{plan_id:'one',version:2},{plan_id:'two',version:3}]});
 assert.match(batch,/one · sürüm 2/);assert.match(batch,/two · sürüm 3/);assert.match(batch,/ayrı değerlendirilir/);
});
test('timer review explains lease/countdown effects and distinguishes normal from algo identities',()=>{
 const timer=render('SET_CANCEL_TIMER',{symbol:'BTCUSDT'},{countdown_ms:120000,lease_ms:60000,heartbeat_ms:10000});
 assert.match(timer,/120 saniye/);assert.match(timer,/60 saniye/);assert.match(timer,/geri sayım devam eder/);
 const orders=render('CANCEL_SELECTED_ORDERS',{symbol:'BTCUSDT'},{targets:[{namespace:'NORMAL',client_id:'normal-id'},{namespace:'ALGO',client_id:'algo-id'}]});
 assert.match(orders,/Normal · normal-id/);assert.match(orders,/Koşullu \/ Algo · algo-id/);
});
