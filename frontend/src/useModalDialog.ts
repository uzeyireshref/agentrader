import {useLayoutEffect,type RefObject} from 'react';
/** Close the captured native node before React detaches its ref/top-layer owner. */
export function useModalDialog(ref:RefObject<HTMLDialogElement|null>){
 useLayoutEffect(()=>{const node=ref.current,opener=document.activeElement instanceof HTMLElement?document.activeElement:null;node?.showModal();return()=>{node?.close();if(opener?.isConnected&&!document.querySelector('dialog[open]'))opener.focus({preventScroll:true});};},[]);
}
