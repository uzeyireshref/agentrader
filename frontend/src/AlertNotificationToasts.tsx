import type {AlertNotifications} from './useAlertNotifications';
import Icon from './ChartIcon';
export default function AlertNotificationToasts({notifications:n,onHistory}:{notifications:AlertNotifications;onHistory:()=>void}){
 return <aside className="alert-toast-stack" aria-label="Yeni alarm bildirimleri" aria-live="polite" aria-relevant="additions">{n.toasts.map(e=><article className="alert-toast" key={e.id}><Icon name="bell"/><div><strong>{e.name}</strong><p>{e.symbol} · {e.close}</p>{e.message&&<p className="alert-toast-message">{e.message}</p>}<button onClick={onHistory}>Geçmişi aç</button></div><button className="alert-icon-button" aria-label={e.name+' bildirimini kapat'} onClick={()=>n.dismiss(e.id)}><Icon name="close"/></button></article>)}</aside>;
}
