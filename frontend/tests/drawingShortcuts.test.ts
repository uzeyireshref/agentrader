import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {installDrawingShortcuts} from '../src/drawingShortcuts.ts';
test('drawing history/delete keys are scoped, preserve native form editing and cancel drafts',()=>{
 const dom=new JSDOM('<main><div tabindex="0"></div><input/><textarea></textarea></main><aside tabindex="0"></aside>');
 Object.assign(globalThis,{document:dom.window.document,Element:dom.window.Element});
 const surface=document.querySelector('main')!,chart=surface.querySelector('div')!,calls:string[]=[];
 const actions={blocked:false,creating:false,cancel:()=>calls.push('cancel'),canUndo:true,canRedo:true,undo:async()=>{calls.push('undo');},redo:async()=>{calls.push('redo');},remove:async()=>{calls.push('remove');},hasSelection:true};
 const stop=installDrawingShortcuts(surface,()=>actions);
 const key=(target:Element,key:string,extras:object={})=>{const e=new dom.window.KeyboardEvent('keydown',{key,bubbles:true,cancelable:true,...extras});target.dispatchEvent(e);return e.defaultPrevented;};
 assert.equal(key(chart,'z',{ctrlKey:true}),true);key(chart,'z',{metaKey:true,shiftKey:true});key(chart,'y',{ctrlKey:true});key(chart,'Delete');
 assert.deepEqual(calls,['undo','redo','redo','remove']);
 for(const target of [surface.querySelector('input')!,surface.querySelector('textarea')!,document.querySelector('aside')!]){assert.equal(key(target,'z',{ctrlKey:true}),false);assert.equal(key(target,'Backspace'),false);}
 actions.creating=true;key(chart,'z',{ctrlKey:true});assert.equal(calls.at(-1),'cancel');assert.equal(key(chart,'Delete'),false);
 actions.creating=false;actions.blocked=true;assert.equal(key(chart,'z',{ctrlKey:true}),false);
 actions.blocked=false;const dialog=document.createElement('dialog');dialog.setAttribute('open','');document.body.append(dialog);assert.equal(key(chart,'Delete'),false);dialog.remove();
 stop();assert.equal(key(chart,'Delete'),false);dom.window.close();
});
