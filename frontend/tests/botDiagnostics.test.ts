import {test} from 'node:test';
import assert from 'node:assert/strict';
import {BotApiError,exchangeDiagnosticMessage,preflightDiagnosticMessage} from '../src/botApi';
test('preflight reasons explain only explicit typed rejections and leave unknown failures generic',()=>{
 for(const reason of ['GRID_BUDGET_TOO_SMALL','GRID_PRICE_OUTSIDE_BAND','ACCOUNT_NOT_ELIGIBLE','ACCOUNT_MODE_MISMATCH','ACCOUNT_SETTINGS_MISMATCH','ACCOUNT_NOT_FLAT','SNAPSHOT_STALE','COLLATERAL_INSUFFICIENT','BUDGET_TOO_SMALL','PRICE_OUTSIDE_PROTECTION','PRICE_DRIFT_EXCEEDED','NOTIONAL_LIMIT','POSITION_COUNT_LIMIT','TRADE_RISK_LIMIT','TOTAL_RISK_LIMIT','DAILY_LOSS_LIMIT','LIQUIDATION_BUFFER']){
  const diagnostic={category:'PREFLIGHT',reason,correlation_id:'job-test'};
  assert.ok(preflightDiagnosticMessage(diagnostic));
  assert.equal(new BotApiError('BOT_VALIDATION_OR_PREFLIGHT_REJECTED',diagnostic).message,preflightDiagnosticMessage(diagnostic));
  assert.match(new BotApiError('WORKER_INTERRUPTED',diagnostic).message,/yeniden gönderilmedi/);
 }
 for(const reason of ['UNKNOWN','__proto__','toString'])assert.equal(preflightDiagnosticMessage({category:'PREFLIGHT',reason}),null);
 assert.equal(preflightDiagnosticMessage({category:'EXCHANGE',reason:'DAILY_LOSS_LIMIT'}),null);
});
test('only a proven exchange rejection receives a specific explanation',()=>{
 for(const code of [-2019,-2027,-4061,-1111,-4164]){
  assert.ok(exchangeDiagnosticMessage({category:'EXCHANGE',delivery_status:'REJECTED',code}));
  for(const delivery_status of ['UNKNOWN','NOT_SENT','READ_FAILED'])assert.equal(exchangeDiagnosticMessage({category:'EXCHANGE',delivery_status,code}),null);
 }
 assert.equal(exchangeDiagnosticMessage({category:'EXCHANGE',delivery_status:'REJECTED',code:-1013}),null);
 assert.match(new BotApiError('BOT_EXCHANGE_UNAVAILABLE',{category:'EXCHANGE',delivery_status:'UNKNOWN',code:-2019}).message,/mevcut kimlikle/);
});
