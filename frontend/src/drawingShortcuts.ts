type Actions={blocked:boolean;creating:boolean;cancel:()=>void;canUndo:boolean;canRedo:boolean;undo:()=>Promise<void>;redo:()=>Promise<void>;remove:()=>Promise<void>;hasSelection:boolean};
/** Scoped to this terminal; native text editing and modal keyboard handling win. */
export function installDrawingShortcuts(surface:HTMLElement,latest:()=>Actions){
 const key=(e:KeyboardEvent)=>{
  if(e.defaultPrevented||e.isComposing||e.altKey)return;
  const target=e.target instanceof Element?e.target:null;
  if(!target||!surface.contains(target)||target.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"]),[role="textbox"],[role="combobox"]')||document.querySelector('dialog[open],[role="dialog"][aria-modal="true"]'))return;
  const a=latest();if(a.blocked)return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){
   e.preventDefault();if(a.creating){a.cancel();return;}if(e.shiftKey){if(a.canRedo)void a.redo();}else if(a.canUndo)void a.undo();return;
  }
  if(e.ctrlKey&&!e.metaKey&&!e.shiftKey&&e.key.toLowerCase()==='y'){e.preventDefault();if(a.creating)a.cancel();else if(a.canRedo)void a.redo();return;}
  if(!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&['Delete','Backspace'].includes(e.key)&&a.hasSelection&&!a.creating){e.preventDefault();void a.remove();}
 };
 surface.addEventListener('keydown',key);return()=>surface.removeEventListener('keydown',key);
}
