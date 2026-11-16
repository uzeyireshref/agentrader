(()=>{
const box=document.createElement('aside');box.id='b5-final';box.style.cssText='position:sticky;top:0;z-index:1001;padding:12px;background:#233133;color:white;font:14px system-ui';
box.innerHTML=`<b>B5 son masaüstü kontrolleri — sentetik test</b><ol>
<li>“Başlat”a bas. Grafik odaktayken sırayla <b>+ − ← → End Tab Shift+Tab</b> tuşlarını kullan. Odak çerçevesini gözle.</li>
<li>Soldaki Coin ara alanına tıkla, BTC yaz; ← ve End tuşlarını kullan. Yazı alanında çalışmalı, grafik oynamamalı.</li>
<li>Grafikteki “Hizalamayı ölç” ile normal ölçüm al. Uygulamanın tam ekran düğmesiyle gir; çıkış düğmesiyle çık. Yeniden gir, RSI'ı aç/kapat, “Hizalamayı ölç”e bas, <b>Escape</b> ile çık ve tekrar ölç. F11 kullanma.</li>
<li>Pencereyi biraz daraltıp genişlet; kırpılma/çizim kayması olup olmadığına bak. Sonra aşağıdaki gözlemlerini işaretleyip kaydet.</li></ol>
<button id="b5-start">Başlat</button>
<label><input id="b5-focus" type="checkbox">Odak görünür, Tab ile çıkıp dönebiliyorum</label>
<label><input id="b5-visible" type="checkbox">Tam ekran/çıkış/RSI/resize kontrolleri görünür ve kullanılabilir; çizimler kaymıyor</label>
<button id="b5-save">Sonucu kaydet</button><p id="b5-state">Hazır</p>`;
document.body.prepend(box);
let run=null;const state=()=>{const n=native();if(!n?.chart)return null;const a=document.activeElement;return {bundle:document.querySelector('script[type=module]')?.getAttribute('src'),range:n.chart.timeScale().getVisibleLogicalRange(),spacing:n.chart.timeScale().options().barSpacing,fullscreen:!!document.fullscreenElement,focus:a?{tag:a.tagName,label:a.getAttribute('aria-label'),id:a.id,outline:getComputedStyle(a).outlineStyle}:null,width:innerWidth,height:innerHeight,dpr:devicePixelRatio,candles:n.view.candles.length,drawings:document.querySelectorAll('[data-drawing]').length};};
const note=(kind,extra={})=>{if(run)run.events.push({kind,at:performance.now(),state:state(),...extra});};
document.getElementById('b5-start').onclick=()=>{run={started_at:new Date().toISOString(),harness_smoke:!!window.__labHarness,events:[]};const n=native();n.chart.timeScale().setVisibleLogicalRange({from:200,to:280});n.series.priceScale().applyOptions({autoScale:true});document.querySelector('[role=region][aria-label="Fiyat grafiği"]').focus();setTimeout(()=>note('start'),200);document.getElementById('b5-state').textContent='Kayıt açık. Adımları sırayla yap; sonunda Sonucu kaydet.';};
window.addEventListener('keydown',e=>{if(!run)return;const before=state(),target=e.target?.getAttribute?.('aria-label');setTimeout(()=>note('key',{key:e.key,shift:e.shiftKey,trusted:e.isTrusted,target,before}),180);},{capture:true});
window.addEventListener('click',e=>{if(!run||e.target?.closest?.('#b5-final'))return;const button=e.target?.closest?.('button');if(button){const before=state();setTimeout(()=>note('click',{label:button.getAttribute('aria-label')||button.textContent,trusted:e.isTrusted,before}),250);}},true);
document.addEventListener('fullscreenchange',()=>setTimeout(()=>note('fullscreenchange'),350));
window.addEventListener('resize',()=>setTimeout(()=>note('resize'),250));
window.addEventListener('focusin',()=>setTimeout(()=>note('focus'),40));
const observer=new MutationObserver(()=>{if(!run)return;const pre=document.querySelector('[aria-label="Çizim hizalama kontrolü"] pre');if(pre){try{const v=JSON.parse(pre.textContent);if(run.last_measurement!==v.observed_at){run.last_measurement=v.observed_at;note('alignment',{measurement:v});}}catch{}}});observer.observe(document.querySelector('#root'),{subtree:true,childList:true,characterData:true});
document.getElementById('b5-save').onclick=async()=>{if(!run)return;note('finish');const data=run;data.visual_user_attestation={focus_and_tab:document.getElementById('b5-focus').checked,fullscreen_controls_resize_drawings:document.getElementById('b5-visible').checked};data.finished_at=new Date().toISOString();const response=await fetch('/lab/acceptance-trace',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!response.ok){document.getElementById('b5-state').textContent='Kaydedilemedi';return;}const receipt=await response.json();run=null;document.getElementById('b5-state').textContent='Kaydedildi: '+receipt.name;};
})();
