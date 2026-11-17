import {test} from 'node:test';
import assert from 'node:assert/strict';
import {initialPositionAction,positionActionError} from '../src/positionPrototype.ts';

test('increase must remain inside the synthetic protection envelope',()=>{
 assert.equal(positionActionError('Artır',initialPositionAction),'');
 for(const patch of [{quantity:'0'},{floor:'91000',ceiling:'90000'},{floor:'88000'},{ceiling:'94000'}])assert.notEqual(positionActionError('Artır',{...initialPositionAction,...patch}),'');
});
test('reduction cannot exceed the observed example amount or 100 percent',()=>{
 assert.equal(positionActionError('Azalt',initialPositionAction),'');
 assert.notEqual(positionActionError('Azalt',{...initialPositionAction,value:'101'}),'');
 assert.equal(positionActionError('Azalt',{...initialPositionAction,value:'100'}),'');
 assert.notEqual(positionActionError('Azalt',{...initialPositionAction,reduction:'QUANTITY',value:'0.02'}),'');
});
test('native trailing checks callback boundaries, quantity and example activation',()=>{
 for(const callback of ['0.1','20'])assert.equal(positionActionError('Trailing',{...initialPositionAction,callback}),'');
 for(const patch of [{callback:'0.09'},{callback:'20.01'},{quantity:'0.02'},{activation:'90000'}])assert.notEqual(positionActionError('Trailing',{...initialPositionAction,...patch}),'');
});
test('reverse requires an explicit existing-plan reference rather than an implicit opposite entry',()=>{
 assert.notEqual(positionActionError('Tersine çevir',initialPositionAction),'');
 assert.equal(positionActionError('Tersine çevir',{...initialPositionAction,planId:'opposite-plan',version:'1',digest:'a'.repeat(64)}),'');
 assert.notEqual(positionActionError('Tersine çevir',{...initialPositionAction,planId:'opposite-plan',version:'0',digest:'a'.repeat(64)}),'');
});

test('native trailing query and cancel require the original create command identity',()=>{
 for(const trailingAction of ['Sorgula','İptal'] as const){
 assert.notEqual(positionActionError('Trailing',{...initialPositionAction,trailingAction,createId:'123'}),'');
 assert.equal(positionActionError('Trailing',{...initialPositionAction,trailingAction,createId:'cmd-'+'b'.repeat(40)}),'');
 }
});
