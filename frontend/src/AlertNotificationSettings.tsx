import type {AlertNotifications} from './useAlertNotifications';
export default function AlertNotificationSettings({notifications:n}:{notifications:AlertNotifications}){
 return <section className="alert-notification-settings" aria-label="Alarm bildirim tercihleri"><h3>Bildirim tercihleri</h3><p>Bu tarayıcının genel tercihleridir; alarmın Kanallar seçimiyle birlikte uygulanır. Değişiklikler hemen saklanır.</p>
 <label className="alert-notification-option"><input type="checkbox" checked={n.prefs.inApp} onChange={e=>n.update({inApp:e.target.checked})}/><span>Uygulama içi bildirim<small>Grafik üzerinde yeni tetikleme kartı göster.</small></span></label>
 <label className="alert-notification-option"><input type="checkbox" checked={n.prefs.sound} onChange={e=>void n.toggleSound(e.target.checked)}/><span>Sesli uyarı<small>{n.prefs.sound&&!n.soundReady?'Bu sekmede sesi başlatmak için Sesi dene düğmesine basın.':'Yeni tetiklemelerde kısa bir uyarı sesi çal.'}</small></span></label>
 <button type="button" className="alert-secondary" onClick={()=>void n.testSound()}>Sesi dene</button>
 <label className="alert-notification-option"><input type="checkbox" checked={n.prefs.desktop&&n.permission==='granted'} disabled={n.permission==='unsupported'} onChange={e=>void n.toggleDesktop(e.target.checked)}/><span>Masaüstü bildirimi<small>{n.permission==='denied'?'İzin engellendi. Tarayıcının site ayarlarından bildirimlere izin verin.':n.permission==='unsupported'?'Bu tarayıcı veya bağlantı masaüstü bildirimini desteklemiyor.':n.permission==='granted'?'Tarayıcı izni verildi.':'Etkinleştirirken tarayıcı izni istenir.'}</small></span></label>
 <p className="alert-context-note">Bildirimler için bu uygulamanın bir sekmesi açık kalmalı. Tarayıcı arka plan kısıtlamaları bildirimi geciktirebilir. Sunucu açıkken tetiklemeler kalıcı geçmişe kaydedilmeye devam eder.</p>
 {n.deliveryError&&<p className="alert-error" role="status">{n.deliveryError}</p>}{n.storageError&&<p className="alert-error" role="status">{n.storageError}</p>}{n.error&&<p className="alert-error" role="status">{n.error}</p>}
 </section>;
}
