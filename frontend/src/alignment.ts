import type {Candle} from './types';
import type {Drawing} from './drawings';

export type XY={x:number;y:number};
export type EngineReference={time:(time:number)=>number|null;price:(price:number)=>number|null};
/** Independent reference: native exact-time coordinates, linear scan for in-between UTC. */
export function referenceTime(rows:Candle[],time:number,native:EngineReference['time']):number|null{
 if(!rows.length||time<rows[0].time||time>rows.at(-1)!.time)return null;
 const exact=native(time);if(exact!==null&&Number.isFinite(exact))return exact;
 for(let i=1;i<rows.length;i++){if(rows[i].time>time){const left=native(rows[i-1].time),right=native(rows[i].time);return left===null||right===null?null:left+(right-left)*(time-rows[i-1].time)/(rows[i].time-rows[i-1].time);}}
 return null;
}
function number(element:Element|null,name:string):number|null{const value=element?.getAttribute(name);if(value===null||value===undefined||value==='')return null;const n=Number(value);return Number.isFinite(n)?n:null;}
export function auditDrawing(item:Drawing,group:SVGGElement|null,rows:Candle[],engine:EngineReference,offset:XY,size:{width:number;height:number}){
 const samples:{part:string;error_px:number}[]=[];let skipped=0;
 const check=(part:string,actual:XY|null,expected:{x:number|null;y:number|null})=>{if(expected.x===null||expected.y===null||expected.x<0||expected.x>size.width||expected.y<0||expected.y>size.height){skipped++;return;}if(!actual){samples.push({part,error_px:Infinity});return;}samples.push({part,error_px:Math.hypot(actual.x+offset.x-expected.x,actual.y+offset.y-expected.y)});};
 const xy=(selector:string,x:string,y:string):XY|null=>{const el=group?.style.display==='none'?null:group?.querySelector(selector)??null,a=number(el,x),b=number(el,y);return a===null||b===null?null:{x:a,y:b};};
 const g=item.geometry,coords=g.anchors.map(a=>({x:referenceTime(rows,a.time,engine.time),y:engine.price(Number(a.price))}));
 if(['text','note','price_label'].includes(g.kind)){check('anchor',xy('.annotation-anchor','cx','cy'),coords[0]);}
 else if(g.kind==='horizontal'){check('left',xy('.shape-line','x1','y1'),{x:0,y:coords[0].y});check('right',xy('.shape-line','x2','y2'),{x:size.width,y:coords[0].y});}
 else if(g.kind==='trend'){check('anchor0',xy('.shape-trend','x1','y1'),coords[0]);check('anchor1',xy('.shape-trend','x2','y2'),coords[1]);}
 else if(['ray','extended_line','horizontal_ray'].includes(g.kind)){
  const a=coords[0],b=coords[1];
  for(const [part,xn,yn] of [['start','x1','y1'],['end','x2','y2']]){
   const actual=xy('.shape-line',xn,yn);
   if(!actual||a.x===null||a.y===null||(g.kind!=='horizontal_ray'&&(!b||b.x===null||b.y===null||b.x===a.x))){skipped++;continue;}
   const x=actual.x+offset.x;
   const y=g.kind==='horizontal_ray'?a.y:a.y+(x-a.x)*(b.y!-a.y)/(b.x!-a.x);
   check(part,actual,{x,y});
  }
 }
 else if(g.kind==='parallel_channel'){
  const [a,b,c]=coords;
  if([a,b,c].some(p=>p.x===null||p.y===null)||a.x===b.x)skipped+=6;
  else{const offsetY=c.y!-(a.y!+(b.y!-a.y!)*(c.x!-a.x!)/(b.x!-a.x!));for(const [name,offsetYPart] of [['base',0],['offset',offsetY],['middle',offsetY/2]] as const){check(name+' start',xy('[data-channel="'+name+'"]','x1','y1'),{x:a.x,y:a.y!+offsetYPart});check(name+' end',xy('[data-channel="'+name+'"]','x2','y2'),{x:b.x,y:b.y!+offsetYPart});}}
 }
 else if(g.kind==='long_plan'||g.kind==='short_plan'){
  for(const [selector,index] of [['.position-risk',1],['.position-reward',2]] as const){const rect=group?.style.display==='none'?null:group?.querySelector(selector)??null;const x=number(rect,'x'),y=number(rect,'y'),w=number(rect,'width'),h=number(rect,'height'),a=coords[0],b=coords[index];
   check(selector+' topLeft',x===null||y===null?null:{x,y},{x:a.x,y:a.y===null||b.y===null?null:Math.min(a.y,b.y)});
   check(selector+' bottomRight',x===null||y===null||w===null||h===null?null:{x:x+w,y:y+h},{x:coords[2].x,y:a.y===null||b.y===null?null:Math.max(a.y,b.y)});
  }
 }
 else if(g.kind==='zone'){const rect=group?.querySelector('.shape-zone')??null;const x=number(rect,'x'),y=number(rect,'y'),w=number(rect,'width'),h=number(rect,'height');const a=coords[0],b=coords[1];check('topLeft',x===null||y===null?null:{x,y},{x:a.x===null||b.x===null?null:(g.time_scope==='unbounded'?0:Math.min(a.x,b.x)),y:a.y===null||b.y===null?null:Math.min(a.y,b.y)});check('bottomRight',x===null||y===null||w===null||h===null?null:{x:x+w,y:y+h},{x:a.x===null||b.x===null?null:(g.time_scope==='unbounded'?size.width:Math.max(a.x,b.x)),y:a.y===null||b.y===null?null:Math.max(a.y,b.y)});}
 else if(g.kind==='fibonacci'||g.kind==='fibonacci_extension')for(const ratio of (g.levels??['0','0.236','0.382','0.5','0.618','0.786','1'])){const y=engine.price(Number(g.anchors[0].price)+(Number(g.anchors[1].price)-Number(g.anchors[0].price))*Number(ratio));if(y===null||Number(g.anchors[0].price)+(Number(g.anchors[1].price)-Number(g.anchors[0].price))*Number(ratio)<=0){skipped+=2;continue;}const x=g.time_scope==='unbounded'?0:coords.every(c=>c.x!==null)?Math.min(coords[0].x!,coords[1].x!):null;check('fib '+ratio+' left',xy('[data-fib="'+ratio+'"]','x1','y1'),{x,y});const right=g.time_scope==='right'||g.time_scope==='unbounded'?size.width:coords.every(c=>c.x!==null)?Math.max(coords[0].x!,coords[1].x!):null;check('fib '+ratio+' right',xy('[data-fib="'+ratio+'"]','x2','y2'),{x:right,y});}
 return {drawing_id:item.drawing_id,kind:g.kind,checked:samples.length,skipped,max_error_px:samples.length?Math.max(...samples.map(s=>s.error_px)):null,passed:samples.length>0&&samples.every(s=>s.error_px<=1),samples:samples.map(s=>({...s,error_px:Number.isFinite(s.error_px)?s.error_px:null,missing:!Number.isFinite(s.error_px)}))};
}

