/** Incomplete creations must not survive an interrupted interaction. */
export function installCreationCancellation(surface:HTMLElement,cancel:()=>void):()=>void{
 const hidden=()=>{if(document.hidden)cancel();};
 const secondary=(event:PointerEvent)=>{if(!event.isPrimary)cancel();};
 window.addEventListener('blur',cancel);
 window.addEventListener('pointercancel',cancel,true);
 document.addEventListener('visibilitychange',hidden);
 surface.addEventListener('pointerdown',secondary,true);
 surface.addEventListener('contextmenu',cancel);
 return()=>{window.removeEventListener('blur',cancel);window.removeEventListener('pointercancel',cancel,true);document.removeEventListener('visibilitychange',hidden);surface.removeEventListener('pointerdown',secondary,true);surface.removeEventListener('contextmenu',cancel);};
}
