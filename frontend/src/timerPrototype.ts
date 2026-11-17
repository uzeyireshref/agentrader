export type TimerDraft={action:'Kur'|'Yenile'|'Sorgula'|'Devre dışı';symbol:string;countdown:string;heartbeat:string;lease:string;timerId:string;acknowledged:boolean};
export function timerDraftError(d:TimerDraft){
 if(d.action!=='Kur')return /^tmr-[a-f0-9]{40}$/.test(d.timerId)?'':'Geçerli timer kimliği gerekli: tmr- ve 40 küçük hex karakter.';
 if(!/^[A-Z0-9]{2,20}USDT$/.test(d.symbol))return 'Geçerli USDT sembolü gerekli.';
 if(!d.acknowledged)return 'Sembol çapında iptal etkisini açıkça kabul edin.';
 if([d.countdown,d.heartbeat,d.lease].some(v=>!/^\d+$/.test(v)||!Number.isSafeInteger(Number(v))))return 'Timer süreleri tamsayı milisaniye olmalı.';
 const [c,h,l]=[d.countdown,d.heartbeat,d.lease].map(Number);
 if(c<1000||c>86400000||h<1000||h>Math.min(60000,Math.floor(c/2))||l<h||l>600000)return 'Süre 1 sn–24 saat; heartbeat 1 sn–min(60 sn, sürenin yarısı); lease heartbeat–10 dakika olmalı.';
 return '';
}
