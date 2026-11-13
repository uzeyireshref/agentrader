import type {Geometry} from './drawings';
export const annotationKinds=['text','note','price_label'];
export const isAnnotation=(g:Geometry)=>annotationKinds.includes(g.kind);
export function annotationText(kind:string,text:string):string{
 const normalized=text.replace(/\r\n?/g,'\n');
 if(Array.from(normalized).length>(kind==='price_label'?80:1000)||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(normalized)||normalized.split('\n').length>(kind==='price_label'?1:8)||normalized.split('\n').some(line=>Array.from(line).length>256)||kind!=='price_label'&&!normalized.trim())throw Error('Metin/not en fazla 8 satır ve 1000 karakter; fiyat başlığı tek satır ve 80 karakter olmalı.');
 return normalized;
}
let measure:((s:string)=>number)|null=null;
function measuredWidth(text:string){if(!measure){try{const context=typeof OffscreenCanvas==='undefined'?null:new OffscreenCanvas(1,1).getContext('2d');if(context){context.font='12px Arial';measure=s=>context.measureText(s).width;}}catch{/* Deterministic fallback for non-browser tests. */}measure??=s=>Array.from(s).length*7;}return measure(text);}
/** Plain text only. Wrapping/ellipsis never changes the persisted body. */
export function annotationLines(g:Geometry,width=230,measureText=measuredWidth,maxLines=12){
 const body=(g.text??'').replace(/\t/g,'    '),text=g.kind==='price_label'?(body?body+'\n':'')+g.anchors[0].price:body,lines:string[]=[];
 for(const paragraph of text.split('\n')){let line='';for(const char of Array.from(paragraph)){if(line&&measureText(line+char)>width){lines.push(line);line='';}line+=char;}lines.push(line);}
 const truncated=lines.length>maxLines,visible=lines.slice(0,maxLines);if(truncated)visible[maxLines-1]=Array.from(visible[maxLines-1]).slice(0,-1).join('')+'…';
 return {lines:visible,width:Math.min(width+20,Math.max(64,...visible.map(measureText))+20),height:visible.length*16+18,truncated};
}
