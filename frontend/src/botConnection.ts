import type {BotStatus} from './botApi';
export function workerCanRead(status:BotStatus|null|undefined):boolean{
 return Boolean(status?.enabled&&status.worker==='FRESH'&&!status.error_code);
}
export function workerIssue(status:BotStatus|null|undefined):string|null{
 if(!status?.enabled)return 'Bot bağlantısı kapalı.';
 if(status.worker!=='FRESH')return 'Hesap bağlantısı kapalı. Bağlantı sağlandığında veriler otomatik yenilenecek.';
 const issues:Record<string,string>={EXECUTION_BUSY:'İşlem motoru başka bir süreçte kullanılıyor. Yeni talep göndermeden bağlantının hazır olmasını bekleyin.',BOT_MONITOR_UNAVAILABLE:'Oturum takibi doğrulanamadı. Kayıtlı oturumları inceleyin.',BOT_STORAGE_UNAVAILABLE:'İşlem kayıtlarına erişilemiyor. Bağlantı düzelene kadar yeni talep gönderilmez.',DEMO_CREDENTIALS_REQUIRED:'Demo hesap bağlantısı yapılandırılmamış.'};
 return status.error_code?(issues[status.error_code]??'Hesap bağlantısında hata var. Ayrıntı kodu: '+status.error_code):null;
}
