import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import './style.css';
const params=new URLSearchParams(location.search);
const FixtureLab=React.lazy(()=>import('./FixtureLab'));
createRoot(document.getElementById('root')!).render(params.get('diagnostics')==='1'&&params.get('fixture')==='1'?<React.Suspense fallback={<p>Referans grafiği yükleniyor…</p>}><FixtureLab/></React.Suspense>:<App/>);
