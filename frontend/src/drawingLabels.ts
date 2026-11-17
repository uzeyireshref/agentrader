type Box={x:number;y:number;width:number;height:number};
type Candidate={node:SVGTextElement;group:SVGGElement;box:Box;priority:number;order:number};

function visible(element:Element,root:SVGSVGElement):boolean{
 for(let e:Element|null=element;e&&e!==root;e=e.parentElement){
  const style=(e as SVGElement).style;
  if(style?.display==='none'||e.getAttribute('display')==='none')return false;
 }
 return true;
}
function bounds(element:SVGGraphicsElement,root:SVGSVGElement):Box|null{
 // Screen rectangles include nested family-group transforms and multiline tspans.
 const rect=element.getBoundingClientRect(),origin=root.getBoundingClientRect();
 if(rect.width>0&&rect.height>0)return {x:rect.x-origin.x,y:rect.y-origin.y,width:rect.width,height:rect.height};
 // Headless/missing-font SVG providers may not expose geometry: fail open.
 try{const b=element.getBBox();if(b.width>0&&b.height>0){
  const m=element.getCTM?.();
  if(m){const points=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>({x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f}));const x=Math.min(...points.map(p=>p.x)),y=Math.min(...points.map(p=>p.y));return {x,y,width:Math.max(...points.map(p=>p.x))-x,height:Math.max(...points.map(p=>p.y))-y};}
  return {x:b.x,y:b.y,width:b.width,height:b.height};
 }}catch{/* unavailable geometry is not proof of overlap */}
 return null;
}
function suppress(node:SVGTextElement,hidden:boolean){
 if(hidden){if(node.getAttribute('data-label-collision')!=='hidden'){node.setAttribute('data-label-collision','hidden');node.style.visibility='hidden';}}
 else if(node.hasAttribute('data-label-collision')){node.removeAttribute('data-label-collision');node.style.removeProperty('visibility');}
}
const overlap=(a:Box,b:Box)=>a.x<b.x+b.width+3&&a.x+a.width+3>b.x&&a.y<b.y+b.height+3&&a.y+a.height+3>b.y;

/** Suppress decorative text only. Anchors, shapes, hit areas, persisted values and annotation bodies never move. */
export function arrangeDrawingLabels(root:SVGSVGElement,width:number,height:number,selected:ReadonlySet<string>,hovered:string|null=null):number{
 const candidates:Candidate[]=[],occupied:Box[]=[],groups=[...root.querySelectorAll<SVGGElement>('g[data-drawing]')];
 for(const group of groups){
  const id=group.getAttribute('data-drawing')!,priority=selected.has(id)?3:hovered===id?2:1;
  if(visible(group,root))for(const node of group.querySelectorAll<SVGGraphicsElement>('.annotation-box')){const box=bounds(node,root);if(box)occupied.push(box);}
  for(const node of group.querySelectorAll<SVGTextElement>('text')){
   if(node.classList.contains('annotation-body')||node.classList.contains('family-unavailable')){suppress(node,false);continue;}
   const box=visible(node,root)&&node.textContent?.trim()?bounds(node,root):null;
   if(!box){suppress(node,false);continue;}
   // Offscreen labels cannot suppress a visible label or produce large grid allocations.
   if(box.x+box.width<0||box.y+box.height<0||box.x>width||box.y>height){suppress(node,false);continue;}
   candidates.push({node,group,box,priority,order:candidates.length});
  }
 }
 candidates.sort((a,b)=>b.priority-a.priority||a.order-b.order);
 const cells=new Map<string,Box[]>(),keys=(b:Box)=>{const out:string[]=[];for(let x=Math.floor(Math.max(0,b.x-3)/64);x<=Math.floor(Math.min(width,b.x+b.width+3)/64);x++)for(let y=Math.floor(Math.max(0,b.y-3)/32);y<=Math.floor(Math.min(height,b.y+b.height+3)/32);y++)out.push(x+','+y);return out;};
 const add=(b:Box)=>{for(const k of keys(b)){const cell=cells.get(k);if(cell)cell.push(b);else cells.set(k,[b]);}};
 for(const box of occupied)add(box);
 let hidden=0;
 for(const c of candidates){const blocked=c.priority<2&&keys(c.box).some(k=>cells.get(k)?.some(box=>overlap(c.box,box)));
  suppress(c.node,blocked);if(blocked)hidden++;else add(c.box);
 }
 return hidden;
}
