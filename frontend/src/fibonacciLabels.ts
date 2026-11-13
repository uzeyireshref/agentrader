/** Keep ratio text readable without changing any Fibonacci line or price. */
export function visibleFibonacciLabels(levels:{level:number;y:number|null}[],spacing=12):Set<number>{
 const sorted=levels.filter((p):p is {level:number;y:number}=>p.y!==null&&Number.isFinite(p.y)).sort((a,b)=>a.y-b.y);
 if(!sorted.length)return new Set();
 const first=sorted[0],last=sorted.at(-1)!,visible=new Set([first.level]);
 if(last.y-first.y<spacing)return visible;
 let previous=first.y;
 for(const p of sorted.slice(1,-1)){if(p.y-previous>=spacing&&last.y-p.y>=spacing){visible.add(p.level);previous=p.y;}}
 visible.add(last.level);return visible;
}
