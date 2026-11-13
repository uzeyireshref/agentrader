export type ChannelSelection={inApp:boolean;sound:boolean;desktop:boolean};
export type ChannelPolicy={schema:'alert-notification-channels/1';mode:'inherit'}|({schema:'alert-notification-channels/1';mode:'custom'}&ChannelSelection);
export const inheritChannels=():ChannelPolicy=>({schema:'alert-notification-channels/1',mode:'inherit'});
export function selectedChannels(value:unknown):ChannelSelection{
 if(value===undefined)return {inApp:true,sound:true,desktop:true};
 const p=value as ChannelPolicy;
 if(p?.schema==='alert-notification-channels/1'&&p.mode==='inherit'&&Object.keys(p).length===2)return {inApp:true,sound:true,desktop:true};
 if(p?.schema==='alert-notification-channels/1'&&p.mode==='custom'&&Object.keys(p).length===5&&typeof p.inApp==='boolean'&&typeof p.sound==='boolean'&&typeof p.desktop==='boolean')return {inApp:p.inApp,sound:p.sound,desktop:p.desktop};
 return {inApp:false,sound:false,desktop:false};
}
export function channelsSummary(p:ChannelPolicy|undefined){
 if(!p||p.mode==='inherit')return 'Tarayıcı tercihlerini kullan';
 return [p.inApp?'Bildirim kartı':'',p.sound?'Ses':'',p.desktop?'Masaüstü':''].filter(Boolean).join(' · ')||'Yalnızca geçmiş';
}
