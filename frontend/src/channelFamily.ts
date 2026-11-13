import {timeToLogical,type Anchor,type Geometry} from './drawings';
import type {Candle} from './types';

export const familyKinds=['parallel_channel','flat_channel','disjoint_channel','regression_channel','pitchfork','schiff_pitchfork','modified_schiff_pitchfork','inside_pitchfork'] as const;
export type FamilyKind=typeof familyKinds[number];
export type FamilyLineStyle={color:string;width:number;style:'solid'|'dashed'|'dotted'};
export type FamilyOptions={line_styles?:Record<string,FamilyLineStyle>;extend:'none'|'left'|'right'|'both';median:boolean;background:boolean;fill_opacity:number;prices:boolean;levels:string[];source:'open'|'high'|'low'|'close'|'hl2'|'hlc3'|'ohlc4';upper_deviation:string;lower_deviation:string;upper_enabled:boolean;lower_enabled:boolean;pearson:boolean};
export const familyNames:Record<FamilyKind,string>={parallel_channel:'Paralel kanal',flat_channel:'Düz üst/alt kanal',disjoint_channel:'Ayrışan kanal',regression_channel:'Regresyon kanalı',pitchfork:'Pitchfork',schiff_pitchfork:'Schiff Pitchfork',modified_schiff_pitchfork:'Modified Schiff Pitchfork',inside_pitchfork:'Inside Pitchfork'};
export const isFamily=(g:Geometry)=>g.schema==='chart-channel-family/1';
export const isPitchfork=(kind:string)=>['pitchfork','schiff_pitchfork','modified_schiff_pitchfork','inside_pitchfork'].includes(kind);
export const familyDefaults=(kind:string):FamilyOptions=>({extend:isPitchfork(kind)?'right':'none',median:!['flat_channel','disjoint_channel'].includes(kind),background:true,fill_opacity:.2,prices:false,levels:['0.5','1'],source:'close',upper_deviation:'2',lower_deviation:'2',upper_enabled:true,lower_enabled:true,pearson:false});
type Point={x:number;y:number};
type Segment={a:Point;b:Point;mode:FamilyOptions['extend'];role:string};
export type FamilyModel={lines:Segment[];fill:[Point,Point,Point,Point]|null;handles:Point[];pearson?:number;deviation?:number;message?:string};
const add=(a:Point,b:Point):Point=>({x:a.x+b.x,y:a.y+b.y});
const sub=(a:Point,b:Point):Point=>({x:a.x-b.x,y:a.y-b.y});
const scale=(a:Point,k:number):Point=>({x:a.x*k,y:a.y*k});
const middle=(a:Point,b:Point)=>scale(add(a,b),.5);
const degenerate=(a:Point,b:Point)=>a.x===b.x&&a.y===b.y;
export function validateFamily(g:Geometry){
 if(!isFamily(g))return;
 if(!familyKinds.includes(g.kind as FamilyKind)||g.anchors.length!==(g.kind==='regression_channel'?2:3))throw Error('Araç noktaları eksik.');
 const [a,b,c]=g.anchors.map(a=>({x:a.time,y:Number(a.price)}));
 if(g.anchors.some(a=>!Number.isSafeInteger(a.time)||a.time<=0||a.time>32503680000||!Number.isFinite(Number(a.price))||Number(a.price)<=0))throw Error('Noktaların zamanı ve fiyatı geçerli olmalı.');
 if(a.x===b.x)throw Error('İlk iki nokta farklı mumlarda olmalı.');
 if(isPitchfork(g.kind)){
  if(degenerate(b,c))throw Error('İkinci ve üçüncü noktalar farklı olmalı.');
  const origin=g.kind==='schiff_pitchfork'?{x:a.x,y:(a.y+b.y)/2}:g.kind==='modified_schiff_pitchfork'?middle(a,b):a;
  if(g.kind==='inside_pitchfork'?degenerate(c,middle(a,b)):degenerate(origin,middle(b,c)))throw Error('Median yönü sıfır olamaz.');
 }else if(g.kind!=='regression_channel'){const offset=c.y-(a.y+(b.y-a.y)*(c.x-a.x)/(b.x-a.x));if(g.kind==='parallel_channel'&&(offset===0||Math.min(a.y+offset,b.y+offset)<=0)||a.y===b.y&&b.y===c.y||g.kind==='disjoint_channel'&&c.y+b.y-a.y<=0)throw Error('Kanal genişliği ve sınır fiyatları geçerli olmalı.');}
 const o=g.options??familyDefaults(g.kind);
 if(!['none','left','right','both'].includes(o.extend)||!Number.isFinite(o.fill_opacity)||o.fill_opacity<0||o.fill_opacity>1||o.levels.length>9||new Set(o.levels.map(Number)).size!==o.levels.length||o.levels.some(v=>!/^\d+(?:\.\d{1,12})?$/.test(v)||Number(v)<=0||Number(v)>10)||[o.upper_deviation,o.lower_deviation].some(v=>!/^\d+(?:\.\d{1,12})?$/.test(v)||Number(v)>10))throw Error('Kanal seçeneklerini kontrol et.');
 const styles=o.line_styles??{};if(Object.keys(styles).length>24||Object.entries(styles).some(([role,v])=>!(/^(median|base|offset|upper|lower|level:-?\d+(?:\.\d+)?)$/.test(role))||!/^#[0-9a-f]{6}$/i.test(v.color)||!Number.isInteger(v.width)||v.width<1||v.width>8||!['solid','dashed','dotted'].includes(v.style)))throw Error('Çizgi stillerini kontrol et.');
 if((g.text??'').length>1000||(g.text??'').split('\n').length>8)throw Error('Not en fazla 1000 karakter ve 8 satır olabilir.');
}

/** A new three-click channel fixes the width handle at the second bar. */
export function familyGeometry(kind:FamilyKind,symbol:string,anchors:Anchor[]):Geometry{
 const fixed=anchors.map(a=>({...a}));if(!isPitchfork(kind)&&kind!=='regression_channel'&&fixed[2])fixed[2].time=fixed[1].time;
 return {schema:'chart-channel-family/1',kind,symbol,price_source:'LAST_PRICE',anchors:fixed,label:familyNames[kind],options:familyDefaults(kind),text:''};
}
const source=(r:Candle,key:FamilyOptions['source'])=>key==='hl2'?(r.high+r.low)/2:key==='hlc3'?(r.high+r.low+r.close)/3:key==='ohlc4'?(r.open+r.high+r.low+r.close)/4:r[key];
/** Own OLS display contract: residual sample deviation, no bot query authority. */
function regression(g:Geometry,rows:Candle[],o:FamilyOptions):FamilyModel{
 const times=g.anchors.map(a=>a.time).sort((a,b)=>a-b),start=rows.findIndex(r=>r.time===times[0]),end=rows.findIndex(r=>r.time===times[1]);
 if(start<0||end<start+1)throw Error('Regresyon için iki nokta arasındaki mum geçmişi gerekli.');
 const sample=rows.slice(start,end+1);if(sample.some((r,i)=>!Number.isFinite(r.time)||i>0&&r.time<=sample[i-1].time||[source(r,o.source),r.high,r.low].some(v=>!Number.isFinite(v)||v<=0)))throw Error('Regresyon için geçerli ve sıralı mum geçmişi gerekli.');
 const n=sample.length,values=sample.map(r=>source(r,o.source)),mx=(n-1)/2,my=values.reduce((a,b)=>a+b,0)/n;
 let xx=0,xy=0,yy=0;for(let i=0;i<n;i++){xx+=(i-mx)**2;xy+=(i-mx)*(values[i]-my);yy+=(values[i]-my)**2;}
 const slope=xy/xx,intercept=my-slope*mx,residual=values.reduce((s,y,i)=>s+(y-intercept-slope*i)**2,0),deviation=Math.sqrt(residual/(n-1));
 const up=o.upper_enabled?deviation*Number(o.upper_deviation):Math.max(...sample.map((r,i)=>r.high-intercept-slope*i));
 const down=o.lower_enabled?deviation*Number(o.lower_deviation):Math.max(...sample.map((r,i)=>intercept+slope*i-r.low));
 const a={x:start,y:intercept},b={x:end,y:intercept+slope*(n-1)},u1={x:a.x,y:a.y+up},u2={x:b.x,y:b.y+up},l1={x:a.x,y:a.y-down},l2={x:b.x,y:b.y-down};
 const lines:Segment[]=[{a:u1,b:u2,mode:o.extend,role:'upper'},{a:l1,b:l2,mode:o.extend,role:'lower'}];if(o.median)lines.unshift({a,b,mode:o.extend,role:'median'});
 return {lines,fill:[u1,u2,l2,l1],handles:g.anchors[0].time<g.anchors[1].time?[a,b]:[b,a],pearson:yy===0?0:-xy/Math.sqrt(xx*yy),deviation};
}
export type FamilyAxis={to:(price:number)=>number;from:(value:number)=>number};
export function familyModel(g:Geometry,rows:Candle[],axis?:FamilyAxis):FamilyModel{
 validateFamily(g);const o=g.options??familyDefaults(g.kind);if(g.kind==='regression_channel')return regression(g,rows,o);
 const finish=(model:FamilyModel):FamilyModel=>{if(!axis)return model;const point=(p:Point):Point=>({x:p.x,y:axis.from(p.y)});return {...model,lines:model.lines.map(l=>({...l,a:point(l.a),b:point(l.b)})),handles:model.handles.map(point),fill:model.fill?model.fill.map(point) as [Point,Point,Point,Point]:null};};
 const p=g.anchors.map(a=>{const x=timeToLogical(rows,a.time);if(x===null)throw Error('Çizim için mum geçmişi gerekli.');const y=axis?axis.to(Number(a.price)):Number(a.price);if(!Number.isFinite(y))throw Error('SCALE');return {x,y};}),[a,b,c]=p;
 const line=(a:Point,b:Point,role:string,mode=o.extend):Segment=>({a,b,role,mode});
 if(isPitchfork(g.kind)){
  const m=middle(b,c),origin=g.kind==='schiff_pitchfork'?{x:a.x,y:(a.y+b.y)/2}:g.kind==='modified_schiff_pitchfork'?middle(a,b):a;
  const direction=g.kind==='inside_pitchfork'?sub(c,middle(a,b)):sub(m,origin),half=sub(c,m),lines:Segment[]=[];
  if(o.median){lines.push(line(g.kind==='inside_pitchfork'?m:origin,g.kind==='inside_pitchfork'?add(m,direction):m,'median'));lines.push(line(b,c,'connector','none'));if(g.kind!=='pitchfork')lines.push(line(a,b,'connector','none'));if(g.kind==='inside_pitchfork')lines.push(line(middle(a,b),c,'connector','none'));}
  for(const level of o.levels.map(Number).sort((a,b)=>a-b))for(const sign of [-1,1]){const start=add(m,scale(half,level*sign));lines.push(line(start,add(start,direction),'level:'+sign*level));}
  const outside=o.levels.length?Math.max(...o.levels.map(Number)):0,upper=add(m,scale(half,outside)),lower=add(m,scale(half,-outside));
  return finish({lines,fill:outside?[upper,add(upper,direction),add(lower,direction),lower]:null,handles:p});
 }
 let d:Point,end:Point;
 if(g.kind==='parallel_channel'){const offset=c.y-(a.y+(b.y-a.y)*(c.x-a.x)/(b.x-a.x));d={x:a.x,y:a.y+offset};end={x:b.x,y:b.y+offset};}
 else if(g.kind==='flat_channel'){d={x:a.x,y:c.y};end={x:b.x,y:c.y};}
 else {d={x:a.x,y:c.y+b.y-a.y};end={x:b.x,y:c.y};}
 const lines=[line(a,b,'base'),line(d,end,'offset')];if(o.median)lines.push(line(middle(a,d),middle(b,end),'median'));
 return finish({lines,fill:[a,b,end,d],handles:[a,b,end,d]});
}

/** Clip the independently derived geometry to the viewport, including future rays. */
export function clipFamilyLine(a:Point,b:Point,width:number,height:number,mode:FamilyOptions['extend']):[Point,Point]|null{
 if(![a.x,a.y,b.x,b.y,width,height].every(Number.isFinite)||degenerate(a,b))return null;
 let lo=mode==='left'||mode==='both'?-Infinity:0,hi=mode==='right'||mode==='both'?Infinity:1;
 for(const [origin,delta,max] of [[a.x,b.x-a.x,width],[a.y,b.y-a.y,height]]){if(delta===0){if(origin<0||origin>max)return null;continue;}const t1=-origin/delta,t2=(max-origin)/delta;lo=Math.max(lo,Math.min(t1,t2));hi=Math.min(hi,Math.max(t1,t2));}
 return lo<=hi&&Number.isFinite(lo)&&Number.isFinite(hi)?[{x:a.x+(b.x-a.x)*lo,y:a.y+(b.y-a.y)*lo},{x:a.x+(b.x-a.x)*hi,y:a.y+(b.y-a.y)*hi}]:null;
}
