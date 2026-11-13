import {useState} from 'react';
import {channelAt,channelDistance} from './channel';
import {positionText} from './position';
import type {Geometry} from './drawings';
import type {Candle,Interval} from './types';
export default function ChannelReadout({geometry,rows,interval}:{geometry:Geometry;rows:Candle[];interval:Interval}){
 const [price,setPrice]=useState('');
 try{const time=Math.max(...geometry.anchors.slice(0,2).map(a=>a.time)),b=channelAt(geometry,rows,time,interval);let comparison='';if(price){try{const distance=channelDistance(b,price.replace(',','.'));comparison=(distance.n===0n?'İçeride · ':'Dışarıda · ')+'Sınıra mesafe '+positionText(distance);}catch{comparison='Geçerli pozitif bir kontrol fiyatı gir.';}}
 return <section className="channel-readout" aria-label="Paralel kanal özeti"><b>Kanalın bitiş zamanında</b><time>{new Date(time*1000).toISOString().replace('T',' ').slice(0,19)} UTC</time><dl>{[['Alt sınır',b.lower],['Orta çizgi',b.middle],['Üst sınır',b.upper],['Genişlik',b.width]].map(([label,v])=><div key={String(label)}><dt>{String(label)}</dt><dd>{positionText(v as typeof b.lower)}</dd></div>)}</dl><label>Kontrol fiyatı<input aria-label="Kanal kontrol fiyatı" value={price} placeholder="İsteğe bağlı" inputMode="decimal" onChange={e=>setPrice(e.target.value)}/></label>{comparison&&<p role="status">{comparison}</p>}<small>İlk iki noktanın zaman aralığı geçerli. Mesafe fiyat birimindedir; sınıra eşit fiyat içeride sayılır. Hesap yalnız kesintisiz yüklenmiş mumlarla yapılır.</small></section>;
 }catch(e){return <p className="channel-unavailable" role="status">Kanal hesabı kullanılamıyor: {e instanceof Error?e.message:'veri bekleniyor'}</p>;}
}
