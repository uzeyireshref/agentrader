import {familyKinds,type FamilyKind} from './channelFamily';
import {useEffect,useRef,useState} from 'react';
import type {IChartApi,ISeriesApi} from 'lightweight-charts';
import type {ToolKind} from './chartCommands';
import {drawingManagement,drawingVisible,type Anchor,type Drawing,type Geometry} from './drawings';
import type {Candle,Interval} from './types';
import {creationPreview,drawingPriceExtent,cursorPrice} from './creationPreview';
import {supportsView,type ViewScale} from './viewScale';
import {magnetPrice} from './indicators';
import {ProjectionPrimitive} from './ProjectionPrimitive';
import DrawingLayer from './DrawingLayer';

type Props={dragGeometry?:Geometry|null;host:HTMLElement|null;chart:IChartApi|null;series:ISeriesApi<'Candlestick'>|null;rows:Candle[];symbol:string;interval:Interval;tick:string;tool:ToolKind;first:Anchor|null;second:Anchor|null;viewScale:ViewScale;items:Drawing[];selected:string|null;disabled:boolean;magnet:boolean};
const ignore=()=>{};
const ignoreChange=async()=>{};
export default function DrawingInteraction(props:Props){
 const latest=useRef(props);latest.current=props;
 const [cursor,setCursor]=useState<Anchor|null>(null),[hovered,setHovered]=useState<string|null>(null);
 const axis=useRef<HTMLDivElement>(null),pointer=useRef<{x:number;y:number}|null>(null),mouseLabel=useRef<HTMLDivElement>(null),range=useRef<HTMLDivElement>(null),low=useRef<HTMLSpanElement>(null),high=useRef<HTMLSpanElement>(null),guide=useRef<HTMLDivElement>(null),plugin=useRef<ProjectionPrimitive|null>(null);
 const draft=props.disabled?null:creationPreview(props.tool,props.symbol,props.first,props.second,cursor);
 const draftRef=useRef(draft);draftRef.current=draft;
 const hoverRef=useRef(hovered);hoverRef.current=hovered;
 useEffect(()=>{setCursor(null);setHovered(null);pointer.current=null;},[props.symbol,props.interval,props.tool,props.viewScale]);
 useEffect(()=>{
  const {host,chart,series}=props,surface=host?.parentElement;
  if(!host||!chart||!series||!surface)return;
  let frame=0;
  const draw=()=>{
   const p=latest.current,size=chart.paneSize(0),at=pointer.current;
   if(axis.current){axis.current.style.left=size.width+'px';axis.current.style.width=series.priceScale().width()+'px';axis.current.style.height=size.height+'px';}
   const valid=!!at&&at.x>=0&&at.x<size.width&&at.y>=0&&at.y<size.height&&!p.disabled;
   const value=valid?cursorPrice(series.coordinateToPrice(at!.y),p.tick):null;
   if(mouseLabel.current){mouseLabel.current.hidden=value===null;if(value!==null){mouseLabel.current.textContent=value;mouseLabel.current.style.top=Math.max(10,Math.min(size.height-10,at!.y))+'px';}}
   if(guide.current){guide.current.hidden=value===null;guide.current.style.width=size.width+'px';if(at)guide.current.style.top=at.y+'px';}
   const item=p.items.find(d=>d.drawing_id===(hoverRef.current??p.selected)&&drawingVisible(d,p.interval)&&supportsView(d.geometry.kind,p.viewScale,d.geometry.schema));
   const geometry=draftRef.current??p.dragGeometry??item?.geometry,extent=geometry?drawingPriceExtent(geometry,p.rows,p.viewScale==='LOG'?{to:price=>-(series.priceToCoordinate(price)??NaN),from:value=>series.coordinateToPrice(-value)??NaN}:undefined):null;
   const ys=extent?.map(price=>series.priceToCoordinate(price));
   const visible=!!ys&&ys.every(y=>y!==null&&Number.isFinite(y))&&!p.disabled;
   if(range.current){range.current.hidden=!visible;if(visible){const top=Math.max(0,Math.min(...ys as number[])),bottom=Math.min(size.height,Math.max(...ys as number[]));range.current.hidden=bottom<0||top>size.height;range.current.style.top=top+'px';range.current.style.height=Math.max(2,bottom-top)+'px';}}
   const color=draftRef.current?null:item?drawingManagement(item).color:null;if(axis.current)axis.current.style.setProperty('--range-color',color??'var(--accent)');
   for(const [node,index] of [[low.current,0],[high.current,1]] as const){if(!node)continue;const y=ys?.[index];node.hidden=!visible||y===null||y===undefined||y<0||y>size.height||(index===1&&extent?.[0]===extent?.[1]);if(visible&&extent&&y!==null&&y!==undefined){node.textContent=cursorPrice(extent[index],p.tick)??'';node.style.top=Math.max(10,Math.min(size.height-10,y))+'px';}}
  };
  const updateCursor=()=>{
   frame=0;const p=latest.current,at=pointer.current,size=chart.paneSize(0);
   if(!at||at.x<0||at.x>=size.width||at.y<0||at.y>=size.height||p.disabled){setCursor(null);draw();return;}
   const logical=chart.timeScale().coordinateToLogical(at.x),row=logical===null?undefined:p.rows[Math.round(logical)];let price:number|null=series.coordinateToPrice(at.y);
   if(row&&price!==null&&price>0){if(p.magnet)price=magnetPrice(row,price,v=>series.priceToCoordinate(v),at.y);const label=cursorPrice(price,p.tick);if(label){const next={time:row.time,price:label};setCursor(old=>old?.time===next.time&&old.price===next.price?old:next);}else setCursor(null);}else setCursor(null);
   draw();
  };
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(updateCursor);};
  const move=(e:PointerEvent)=>{if(!e.isPrimary)return;const target=e.target instanceof Element?e.target:null;if(target?.closest('.floating-drawing-toolbar,.drawing-settings-popup,.pane-legend')){leave();return;}const r=host.getBoundingClientRect();pointer.current={x:e.clientX-r.left,y:e.clientY-r.top};const id=target?.closest('[data-drawing]')?.getAttribute('data-drawing')??null;hoverRef.current=id;setHovered(id);schedule();};
  const leave=()=>{pointer.current=null;hoverRef.current=null;setHovered(null);setCursor(null);draw();};
  const primitive=new ProjectionPrimitive(draw);plugin.current=primitive;series.attachPrimitive(primitive);
  surface.addEventListener('pointermove',move);surface.addEventListener('pointerleave',leave);surface.addEventListener('pointercancel',leave);window.addEventListener('blur',leave);
  draw();return()=>{cancelAnimationFrame(frame);surface.removeEventListener('pointermove',move);surface.removeEventListener('pointerleave',leave);surface.removeEventListener('pointercancel',leave);window.removeEventListener('blur',leave);series.detachPrimitive(primitive);plugin.current=null;};
 },[props.host,props.chart,props.series]);
 useEffect(()=>{plugin.current?.invalidate();},[draft,props.items,props.selected,hovered,props.disabled,props.rows,props.viewScale,props.dragGeometry]);
 const previewItems:Drawing[]=draft?[{drawing_id:'creation-preview',workspace_id:'',revision:0,updated_at:0,deleted:false,geometry:draft}]:[];
 return <><div className="creation-preview" aria-hidden="true"><DrawingLayer transient={familyKinds.includes(props.tool as FamilyKind)} viewScale={props.viewScale} symbol={props.symbol} chart={props.chart} series={props.series} rows={props.rows} items={previewItems} selected={draft?'creation-preview':null} select={ignore} change={ignoreChange} interval={props.interval} tick={props.tick} disabled/></div><div ref={guide} className="drawing-cursor-guide" hidden/><div ref={axis} className="drawing-price-axis" aria-hidden="true"><div ref={range} className="drawing-price-range" hidden/><span ref={low} className="drawing-price-bound" hidden/><span ref={high} className="drawing-price-bound" hidden/><div ref={mouseLabel} className="drawing-mouse-price" data-testid="drawing-mouse-price" hidden/></div></>;
}
