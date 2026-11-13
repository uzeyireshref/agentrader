import {useRef,type ReactNode} from 'react';
import Icon from './ChartIcon';
/** Native disclosure: keyboard accessible, closes on focus exit and Escape. */
export default function ShellMenu({label,icon,children,rail=false}:{label:string;icon:string;children:ReactNode;rail?:boolean}){
 const ref=useRef<HTMLDetailsElement>(null);
 return <details ref={ref} className={'shell-menu'+(rail?' rail-menu':'')} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))e.currentTarget.open=false;}} onKeyDown={e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();e.currentTarget.open=false;e.currentTarget.querySelector('summary')?.focus();}}}>
  <summary aria-label={label} title={label}><Icon name={icon}/>{!rail&&<span>{label}</span>}<Icon name="chevron"/></summary>
  <div className="shell-menu-content" onClick={e=>{if((e.target as HTMLElement).closest('button')&&ref.current)ref.current.open=false;}}>{children}</div>
 </details>;
}
