import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {arrangeDrawingLabels} from '../src/drawingLabels';

function fixture(){
 const dom=new JSDOM('<svg xmlns="http://www.w3.org/2000/svg"><g data-drawing="first"><line x1="10" y1="20" x2="40" y2="20"/><text class="drawing-title" x="10" y="20">First</text></g><g data-drawing="second"><line x1="10" y1="20" x2="40" y2="20"/><text class="drawing-title" x="10" y="20">Second</text></g></svg>');
 const svg=dom.window.document.querySelector('svg') as unknown as SVGSVGElement;
 const labels=[...svg.querySelectorAll('text')] as SVGTextElement[];
 for(const label of labels)Object.assign(label,{getBBox:()=>({x:Number(label.getAttribute('x')),y:Number(label.getAttribute('y'))-12,width:60,height:14})});
 return {dom,svg,labels,layout:(selected:string[]=[],hovered:string|null=null)=>arrangeDrawingLabels(svg,800,500,new Set(selected),hovered)};
}
test('decorative label collisions respect stable order without modifying line/anchor geometry',()=>{
 const f=fixture(),before=[...f.svg.querySelectorAll('line')].map(n=>n.outerHTML);
 assert.equal(f.layout(),1);assert.equal(f.labels[0].style.visibility,'');assert.equal(f.labels[1].style.visibility,'hidden');
 assert.deepEqual([...f.svg.querySelectorAll('line')].map(n=>n.outerHTML),before);
 assert.equal(f.labels[1].getAttribute('x'),'10');assert.equal(f.labels[1].textContent,'Second');
});
test('selection or hover makes its label readable and suppresses lower priority text',()=>{
 const f=fixture();f.layout();f.layout(['second']);assert.equal(f.labels[1].style.visibility,'');assert.equal(f.labels[0].style.visibility,'hidden');
 f.layout([], 'first');assert.equal(f.labels[0].style.visibility,'');assert.equal(f.labels[1].style.visibility,'hidden');
 f.layout(['first','second']);assert.ok(f.labels.every(l=>l.style.visibility===''));
});
test('pan/zoom geometry changes restore a previously suppressed label',()=>{
 const f=fixture();f.layout();assert.equal(f.labels[1].style.visibility,'hidden');
 f.labels[1].setAttribute('y','90');assert.equal(f.layout(),0);assert.equal(f.labels[1].style.visibility,'');
 assert.equal(f.labels[1].hasAttribute('data-label-collision'),false);
});
test('annotation text is never suppressed and its box reserves space for ordinary labels',()=>{
 const f=fixture();f.labels[0].classList.add('annotation-body');const rect=f.dom.window.document.createElementNS('http://www.w3.org/2000/svg','rect');rect.classList.add('annotation-box');Object.assign(rect,{getBBox:()=>({x:5,y:5,width:100,height:40})});f.labels[0].parentElement!.append(rect);
 assert.equal(f.layout(),1);assert.equal(f.labels[0].style.visibility,'');assert.equal(f.labels[1].style.visibility,'hidden');
 f.layout(['second']);assert.equal(f.labels[1].style.visibility,'');
});
test('unavailable SVG bounds and offscreen/hidden labels fail open and do not suppress visible content',()=>{
 const f=fixture();Object.assign(f.labels[0],{getBBox:()=>{throw Error('SVG provider unavailable')}});assert.equal(f.layout(),0);
 Object.assign(f.labels[0],{getBBox:()=>({x:-1000,y:0,width:60,height:14})});assert.equal(f.layout(),0);
 Object.assign(f.labels[0],{getBBox:()=>({x:10,y:8,width:60,height:14})});(f.labels[0].parentElement as unknown as SVGElement).style.display='none';assert.equal(f.layout(),0);
});
test('repeated unchanged layouts do not generate SVG mutations',()=>{
 const f=fixture();f.layout();const observer=new f.dom.window.MutationObserver(()=>{});observer.observe(f.svg,{attributes:true,subtree:true});
 for(let i=0;i<20;i++)f.layout();assert.equal(observer.takeRecords().length,0);observer.disconnect();
});
test('existing per-tool hidden text is not resurrected by the global policy',()=>{
 const f=fixture();f.labels[0].style.display='none';f.layout();assert.equal(f.labels[0].style.display,'none');assert.equal(f.labels[1].style.visibility,'');
});
