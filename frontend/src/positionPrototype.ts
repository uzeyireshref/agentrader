export type PositionAction='Artır'|'Azalt'|'Kapat'|'Tersine çevir'|'Trailing';
export type PositionActionDraft={quantity:string;floor:string;ceiling:string;reduction:'QUANTITY'|'PERCENT';value:string;activation:string;callback:string;workingType:'MARK_PRICE'|'CONTRACT_PRICE';planId:string;version:string;digest:string;trailingAction?:'Oluştur'|'Sorgula'|'İptal';createId?:string};
export const initialPositionAction:PositionActionDraft={quantity:'0.001',floor:'89500',ceiling:'90500',reduction:'PERCENT',value:'25',activation:'92000',callback:'1',workingType:'MARK_PRICE',planId:'',version:'1',digest:''};
const positive=(s:string)=>/^\d+(\.\d+)?$/.test(s)&&Number.isFinite(Number(s))&&Number(s)>0;
// Only checks the displayed synthetic long position; never an executable command.
export function positionActionError(action:PositionAction,d:PositionActionDraft){
 if(action==='Artır'){
  if(![d.quantity,d.floor,d.ceiling].every(positive))return 'Miktar ve fiyat aralığı pozitif sayılar olmalı.';
  if(Number(d.floor)>Number(d.ceiling))return 'Alt fiyat üst fiyatı aşamaz.';
  if(Number(d.floor)<=88000||Number(d.ceiling)>=94000)return 'Örnek pozisyonun stop/hedef sınırları içinde bir fiyat aralığı seçin.';
 }
 if(action==='Azalt'){
  if(!positive(d.value))return 'Pozitif bir azaltma değeri girin.';
  if(d.reduction==='PERCENT'&&Number(d.value)>100)return 'Azaltma yüzdesi en fazla 100 olabilir.';
  if(d.reduction==='QUANTITY'&&Number(d.value)>.01)return 'Azaltma örnek pozisyonun 0,01 BTC miktarını aşamaz.';
 }
 if(action==='Trailing'){
  if(d.trailingAction&&d.trailingAction!=='Oluştur')return /^cmd-[a-f0-9]{40}$/.test(d.createId??'')?'':'Aynı native trailing oluşturma komutunun cmd- ve 40 hex karakterli kimliği gerekli.';
  if(!positive(d.quantity)||Number(d.quantity)>.01)return 'Trailing miktarı 0 ile 0,01 BTC arasında olmalı.';
  if(!positive(d.activation)||Number(d.activation)<=90000)return 'Örnek Long pozisyon için aktivasyonu 90.000 üzerinde seçin; gerçek piyasa kontrolü ayrıca gerekir.';
  if(!positive(d.callback)||Number(d.callback)<.1||Number(d.callback)>20)return 'Callback %0,1–20 aralığında olmalı.';
 }
 if(action==='Tersine çevir'&&(!/^[A-Za-z0-9_-]{1,64}$/.test(d.planId)||!/^\d+$/.test(d.version)||!Number.isSafeInteger(Number(d.version))||Number(d.version)<1||!/^[a-f0-9]{64}$/.test(d.digest)))return 'Önceden hazırlanmış karşı planın kimliği, pozitif sürümü ve 64 karakterli digest değeri gerekli.';
 return '';
}
