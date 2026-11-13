import type {ViewScale} from './viewScale';
export default function ViewScaleControl({mode,ready,onChange}:{mode:ViewScale;ready:boolean;onChange:(mode:ViewScale)=>void}){
 return <label className="view-scale-control"><span>Fiyat ekseni</span><select aria-label="Fiyat ekseni türü" title="Ölçek türü değişince görünür mumlar otomatik sığdırılır." disabled={!ready} value={mode} onChange={e=>onChange(e.target.value as ViewScale)}><option value="LINEAR">Lineer</option><option value="LOG">Logaritmik</option></select></label>;
}
