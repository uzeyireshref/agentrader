import type {Geometry} from './drawings';
import {clipFamilyLine,familyDefaults,type FamilyModel} from './channelFamily';
type Point={x:number;y:number};
const ns='http://www.w3.org/2000/svg';
/** Only this empty SVG subgroup is imperative; React owns selection and events. */
export function renderFamily(node:SVGGElement,handles:SVGGElement|null,g:Geometry,model:FamilyModel,project:(p:Point)=>Point|null,width:number,height:number){
 const content=node.querySelector('.family-shapes');if(!content)return;
 const options=g.options??familyDefaults(g.kind),nodes:SVGElement[]=[];
 const element=(tag:string,attrs:Record<string,string|number>)=>{const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));return e as SVGElement;};
 const edges=model.lines.map(l=>{const a=project(l.a),b=project(l.b);return a&&b?clipFamilyLine(a,b,width,height,l.mode):null;});
 if(options.background&&model.fill){
  const p=model.fill.map(project);if(p.every(Boolean)){
   const span=Math.max(width,height,...p.flatMap(q=>[Math.abs(q!.x),Math.abs(q!.y)]))*4+1;
   const reach=(a:Point,b:Point)=>{const dx=b.x-a.x,dy=b.y-a.y,k=span/Math.max(1,Math.hypot(dx,dy)),point=(t:number)=>({x:a.x+dx*t,y:a.y+dy*t});return [point(options.extend==='left'||options.extend==='both'?-k:0),point(options.extend==='right'||options.extend==='both'?k:1)];};
   const left=reach(p[0]!,p[1]!),right=reach(p[3]!,p[2]!);
   // The SVG viewport clips the polygon, retaining corners between two borders.
   nodes.push(element('polygon',{class:'channel-fill family-fill',points:[left[0],left[1],right[1],right[0]].map(p=>p.x+','+p.y).join(' '),'fill-opacity':options.fill_opacity,style:'fill-opacity:'+options.fill_opacity}));
  }
 }
 for(const [i,line]of model.lines.entries()){
  const edge=edges[i];if(!edge)continue;const attrs={x1:edge[0].x,y1:edge[0].y,x2:edge[1].x,y2:edge[1].y};
  const custom=options.line_styles?.[line.role];
  const customAttrs:Record<string,string|number>=custom?{style:`stroke:${custom.color};stroke-width:${custom.width};stroke-dasharray:${custom.style==='dashed'?'8 5':custom.style==='dotted'?'2 4':'none'}`}:{ };
  nodes.push(element('line',{...attrs,...customAttrs,class:'shape-line shape-trend family-line'+(line.role==='median'?' channel-middle':''),'data-family-role':line.role}));
  nodes.push(element('line',{...attrs,class:'hit-line','data-family-hit':line.role}));
 }
 const points=model.handles.map(project);
 if(handles)for(const [i,p]of points.entries()){const handle=handles.querySelector('[data-anchor="'+i+'"]') as SVGElement|null;if(handle){handle.style.display=p?'':'none';if(p){handle.setAttribute('cx',String(p.x));handle.setAttribute('cy',String(p.y));}}}
 if(options.prices)for(const [i,p]of points.entries()){if(!p||p.y<0||p.y>height)continue;const label=element('text',{class:'shape-label family-price',x:Math.max(6,Math.min(width-75,p.x+8)),y:Math.max(13,Math.min(height-4,p.y-8))});label.textContent=new Intl.NumberFormat('tr-TR',{maximumFractionDigits:8}).format(model.handles[i].y);nodes.push(label);}
 const text=[g.label,g.text??'',options.pearson&&model.pearson!==undefined?'R: '+model.pearson.toFixed(4):''].filter(Boolean).join('\n');
 const origin=points.find(Boolean);if(origin&&text){const label=element('text',{class:'shape-label family-title',x:Math.max(8,Math.min(width-200,origin.x+8)),y:Math.max(15,Math.min(height-20,origin.y-10))});for(const [i,line]of text.split('\n').entries()){const span=element('tspan',{x:label.getAttribute('x')!,dy:i?15:0});span.textContent=line;label.append(span);}nodes.push(label);}
 content.replaceChildren(...nodes);
}
