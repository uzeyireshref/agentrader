export type ScheduleWindow={days:number[];start:string;end:string};
export type AlertSchedule={schema:'alert-notification-schedule/1';mode:'always'|'custom';timezone:string;windows:ScheduleWindow[]};
export type NotificationGate={schema:string;allowed:boolean;reason:string;timezone:string;local_time?:string};
export const dayNames=['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'];
export function localZone(){try{return Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';}catch{return 'UTC';}}
export function schedulePreset(mode:string,timezone:string):AlertSchedule{
 return {schema:'alert-notification-schedule/1',mode:mode==='always'?'always':'custom',timezone,windows:mode==='always'?[]:[{days:mode==='custom'?[0,1,2,3,4,5,6]:[0,1,2,3,4],start:mode==='weekdays'?'00:00':'09:00',end:mode==='weekdays'?'24:00':'18:00'}]};
}
export function scheduleMode(s:AlertSchedule){
 if(s.mode==='always')return 'always';
 for(const mode of ['weekdays','workdays'])if(JSON.stringify(s.windows)===JSON.stringify(schedulePreset(mode,s.timezone).windows))return mode;
 return 'custom';
}
export function scheduleError(s:AlertSchedule|undefined){
 if(!s)return '';
 try{new Intl.DateTimeFormat('tr-TR',{timeZone:s.timezone});}catch{return 'Geçerli bir saat dilimi seçin.';}
 if(!s.timezone.trim())return 'Saat dilimi boş bırakılamaz.';
 if(s.mode==='always')return '';
 if(!s.windows.length||s.windows.length>7)return '1–7 saat aralığı ekleyin.';
 for(const [i,w] of s.windows.entries()){
  if(!w.days.length)return `${i+1}. aralık için en az bir gün seçin.`;
  if(!/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(w.start)||!/^(([01][0-9]|2[0-3]):[0-5][0-9]|24:00)$/.test(w.end)||w.start===w.end)return `${i+1}. aralığın başlangıç ve bitiş saatlerini kontrol edin.`;
 }
 return '';
}
export function scheduleSummary(s:AlertSchedule|undefined){
 if(!s||s.mode==='always')return '7/24';
 return s.windows.map(w=>`${w.days.map(d=>dayNames[d]).join(', ')} · ${w.start}–${w.end}`).join(' / ')+' · '+s.timezone;
}
