/** Bounded by the current drawing list; discard when SVG structure changes. */
export class ProjectionCache {
 private groups=new Map<string,{node:SVGGElement;signature:string;elements:Map<string,Element[]>}>();
 clear(){this.groups.clear();}
 group(svg:SVGSVGElement,id:string,attribute:'data-drawing'|'data-drawing-handles'='data-drawing'){const key=attribute+':'+id;let entry=this.groups.get(key);if(!entry){const node=svg.querySelector<SVGGElement>('['+attribute+'="'+id+'"]');if(!node)return null;entry={node,signature:'',elements:new Map()};this.groups.set(key,entry);}return entry;}
 project(entry:NonNullable<ReturnType<ProjectionCache['group']>>,signature:string){if(entry.signature===signature)return false;entry.signature=signature;return true;}
 set(entry:NonNullable<ReturnType<ProjectionCache['group']>>,selector:string,values:Record<string,number>){if(!entry.elements.has(selector))entry.elements.set(selector,Array.from(entry.node.querySelectorAll(selector)));const nodes=entry.elements.get(selector)!;for(const node of nodes)for(const [key,value]of Object.entries(values)){const text=String(value);if(node.getAttribute(key)!==text)node.setAttribute(key,text);}}
}
