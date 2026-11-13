import {useEffect,useRef,useState} from 'react';
import {AlertSound,collectEvents,notificationKey,preferences,receiptKey,receipts,validEvent,type AlertEvent,type NotificationPreferences,type Receipts} from './alertNotifications';

export function useAlertNotifications(){
 const read=(key:string)=>{try{return localStorage.getItem(key);}catch{return null;}};
 const [prefs,setPrefs]=useState(()=>preferences(read(notificationKey))),[unread,setUnread]=useState(()=>receipts(read(receiptKey))?.unread.length??0),[toasts,setToasts]=useState<AlertEvent[]>([]),[error,setError]=useState(''),[deliveryError,setDeliveryError]=useState(''),[storageError,setStorageError]=useState(''),[permission,setPermission]=useState<string>(()=>typeof Notification==='undefined'?'unsupported':Notification.permission),[soundReady,setSoundReady]=useState(false);
 const prefRef=useRef(prefs);prefRef.current=prefs;const sound=useRef<AlertSound|null>(null),memory=useRef<Receipts|null>(receipts(read(receiptKey))),storageOK=useRef(true),active=useRef(true);
 const write=(key:string,value:unknown)=>{try{localStorage.setItem(key,JSON.stringify(value));}catch{storageOK.current=false;setStorageError('Tarayıcı depolaması kullanılamıyor. Tercihler ve tekrar bildirimi engelleme yalnızca bu sekmede korunur.');}};
 const locked=async<T,>(fn:()=>T):Promise<T>=>navigator.locks? navigator.locks.request(receiptKey,fn):fn();
 const update=(patch:Partial<NotificationPreferences>)=>{const v={...prefRef.current,...patch};prefRef.current=v;setPrefs(v);write(notificationKey,v);};
 const enableSound=async()=>{try{sound.current??=new AlertSound();await sound.current.enable();setSoundReady(true);setDeliveryError('');return true;}catch{setSoundReady(false);setDeliveryError('Ses başlatılamadı. Tarayıcı ses iznini kontrol edip Sesi dene düğmesine basın.');return false;}};
 const toggleSound=async(value:boolean)=>{if(!value){update({sound:false});return;}if(await enableSound())update({sound:true});};
 const testSound=async()=>{if(await enableSound())try{sound.current!.play();}catch{setDeliveryError('Ses çalınamadı.');}};
 const toggleDesktop=async(value:boolean)=>{
  if(!value){update({desktop:false});return;}
  if(typeof Notification==='undefined'||!window.isSecureContext){setPermission('unsupported');return;}
  try{const p=Notification.permission==='default'?await Notification.requestPermission():Notification.permission;setPermission(p);update({desktop:p==='granted'});}catch{setDeliveryError('Masaüstü bildirimi izni alınamadı.');update({desktop:false});}
 };
 const markRead=async()=>{await locked(()=>{const s=(storageOK.current?receipts(read(receiptKey)):null)??memory.current??{seen:[],unread:[]};const v={...s,unread:[]};memory.current=v;write(receiptKey,v);setUnread(0);});setToasts([]);};
 useEffect(()=>{
  active.current=true;let stopped=false,timer:ReturnType<typeof setTimeout>;const abort=new AbortController();
  const poll=async()=>{
   try{
    const r=await fetch('/api/alerts',{signal:abort.signal});if(!r.ok)throw Error();const d=await r.json();
    if(d.schema!=='price-alerts/1'||d.order_authority!==false||!Array.isArray(d.events)||!d.events.every(validEvent))throw Error();
    if(stopped)return;
    const fresh=await locked(()=>{if(stopped)return [];const previous=(storageOK.current?receipts(read(receiptKey)):null)??memory.current;const result=collectEvents(previous,d.events,Date.now()/1000);memory.current=result.state;write(receiptKey,result.state);setUnread(result.state.unread.length);return result.fresh;});
    if(stopped)return;setError(d.runtime_error?'Alarm izleyicisi hata bildirdi.':'');
    if(fresh.length){const p=prefRef.current;if(p.inApp)setToasts(old=>[...fresh.reverse(),...old].slice(0,3));
     if(p.sound)try{sound.current!.play();}catch{setSoundReady(false);setDeliveryError('Alarm sesi çalınamadı. Sesi dene düğmesiyle bu sekmede sesi etkinleştirin.');}
     if(p.desktop&&typeof Notification!=='undefined'){
      setPermission(Notification.permission);
      if(Notification.permission==='granted')try{const e=fresh[0],n=new Notification(fresh.length>1?`${fresh.length} alarm tetiklendi`:e.name,{body:`${e.symbol} · ${e.close}${e.message?' · '+e.message:''}`,tag:'agentrader-alert-'+e.id});const timeout=window.setTimeout(()=>n.close(),15000);n.onclose=()=>clearTimeout(timeout);n.onerror=()=>{if(active.current)setDeliveryError('Masaüstü bildirimi gösterilemedi. Alarm geçmişi korunuyor.');};n.onclick=()=>{window.focus();window.dispatchEvent(new Event('agentrader:alert-history'));n.close();};}catch{setDeliveryError('Masaüstü bildirimi gösterilemedi. Alarm geçmişi korunuyor.');}
     }
    }
   }catch{if(!stopped)setError('Alarm bildirimleri güncellenemiyor. Bağlantı yeniden denenecek.');}
   finally{if(!stopped)timer=setTimeout(()=>void poll(),3000);}
  };
  const sync=()=>{setPrefs(preferences(read(notificationKey)));setUnread(receipts(read(receiptKey))?.unread.length??0);if(typeof Notification!=='undefined')setPermission(Notification.permission);};
  const storage=(e:StorageEvent)=>{if(e.key===notificationKey||e.key===receiptKey||e.key===null)sync();};
  window.addEventListener('storage',storage);window.addEventListener('focus',sync);void poll();
  return()=>{stopped=true;active.current=false;abort.abort();clearTimeout(timer);window.removeEventListener('storage',storage);window.removeEventListener('focus',sync);sound.current?.close();sound.current=null;};
 },[]);
 return {prefs,unread,toasts,error,deliveryError,storageError,permission,soundReady,update,toggleSound,testSound,toggleDesktop,markRead,dismiss:(id:string)=>setToasts(v=>v.filter(e=>e.id!==id))};
}
export type AlertNotifications=ReturnType<typeof useAlertNotifications>;
