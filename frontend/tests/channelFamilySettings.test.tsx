import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {act,useState} from 'react';
import type {Geometry} from '../src/drawings';
import {familyDefaults} from '../src/channelFamily';
import ChannelFamilySettings from '../src/ChannelFamilySettings';

const dom=new JSDOM('<body></body>',{url:'http://localhost/'});
Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true});
const {createRoot}=await import('react-dom/client');
async function fixture(kind:Geometry['kind']='pitchfork'){
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host);let current:Geometry;
 const changes:Geometry[]=[];
 function Harness(){const [geometry,setGeometry]=useState<Geometry>({schema:'chart-channel-family/1',kind,symbol:'BTCUSDT',price_source:'LAST_PRICE',label:'Araç',text:'',options:familyDefaults(kind),anchors:[{time:1800000000,price:'100'},{time:1800000900,price:'120'},{time:1800001800,price:'110'}]});current=geometry;return <form><ChannelFamilySettings geometry={geometry} disabled={false} onChange={value=>{changes.push(value);setGeometry(value);}}/><button type="submit">Kaydet</button></form>;}
 await act(async()=>root.render(<Harness/>));
 const input=(label:string)=>Array.from(host.querySelectorAll<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>('[aria-label]')).find(node=>node.getAttribute('aria-label')===label)!;
 const fill=async(label:string,value:string)=>{const target=input(label),prototype=target instanceof dom.window.HTMLTextAreaElement?dom.window.HTMLTextAreaElement.prototype:target instanceof dom.window.HTMLSelectElement?dom.window.HTMLSelectElement.prototype:dom.window.HTMLInputElement.prototype;await act(async()=>{Object.getOwnPropertyDescriptor(prototype,'value')!.set!.call(target,value);target.dispatchEvent(new dom.window.Event(target instanceof dom.window.HTMLSelectElement?'change':'input',{bubbles:true}));});};
 return {host,input,fill,changes,current:()=>current!,close:async()=>{await act(async()=>root.unmount());host.remove();}};
}

test('family settings preserve invalid ratio draft and block submit without changing valid geometry',async()=>{
 const f=await fixture();try{const before=structuredClone(f.current().options!.levels);await f.fill('Pitchfork seviye oranları','0.5; 0.50');assert.equal(f.current().options!.levels.join(),before.join());assert.equal(f.input('Pitchfork seviye oranları').value,'0.5; 0.50');assert.equal(f.host.querySelector('form')!.checkValidity(),false);await f.fill('Pitchfork seviye oranları','0.5; 1; 2');assert.deepEqual(f.current().options!.levels,['0.5','1','2']);assert.equal(f.host.querySelector('form')!.checkValidity(),true);}finally{await f.close();}
});
test('multiline text limit keeps invalid text visible and valid persisted draft intact',async()=>{
 const f=await fixture();try{await f.fill('Kanal ve pitchfork metni','Bir\nİki');assert.equal(f.current().text,'Bir\nİki');await f.fill('Kanal ve pitchfork metni',Array(9).fill('Satır').join('\n'));assert.equal(f.current().text,'Bir\nİki');assert.equal(f.host.querySelector('form')!.checkValidity(),false);}finally{await f.close();}
});
test('regression controls separate use-deviation from line visibility and validate coefficient',async()=>{
 const f=await fixture('regression_channel');try{await f.fill('Regresyon üst sapma katsayısı','-2');assert.equal(f.host.querySelector('form')!.checkValidity(),false);assert.equal(f.current().options!.upper_deviation,'2');await f.fill('Regresyon üst sapma katsayısı','1.5');assert.equal(f.current().options!.upper_deviation,'1.5');await act(async()=>f.input('Üst sınırda standart sapma kullan').click());assert.equal(f.current().options!.upper_enabled,false);assert.equal((f.input('Regresyon üst sapma katsayısı') as HTMLInputElement).disabled,true);await f.fill('Regresyon fiyat kaynağı','hlc3');assert.equal(f.current().options!.source,'hlc3');}finally{await f.close();}
});


test('each pitchfork side stores independent style and can return to shared toolbar style',async()=>{
 const f=await fixture();try{assert.ok(f.input('Seviye +0.5 için özel stil'),f.host.innerHTML);await act(async()=>f.input('Seviye +0.5 için özel stil').click());await f.fill('Seviye +0.5 kalınlığı','4');await f.fill('Seviye +0.5 çizgi stili','dashed');assert.deepEqual(f.current().options!.line_styles?.['level:0.5'],{color:'#2962ff',width:4,style:'dashed'});assert.equal(f.current().options!.line_styles?.['level:-0.5'],undefined);await act(async()=>f.input('Seviye +0.5 için özel stil').click());assert.equal(f.current().options!.line_styles?.['level:0.5'],undefined);}finally{await f.close();}
});
