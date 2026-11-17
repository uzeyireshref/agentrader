import {test} from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import BotReview from '../src/BotReview.tsx';
import {initialBotDraft,updateBotDraft} from '../src/botPrototype.ts';

test('market review never describes a reference as fixed execution price or shows limit options',()=>{
 const d=updateBotDraft(initialBotDraft,{orderType:'MARKET'});
 const html=renderToStaticMarkup(<BotReview draft={d}/>);
 assert.match(html,/Risk referansı/);assert.match(html,/dolum garantisi değildir/);
 assert.doesNotMatch(html,/Süre \/ STP|Limit fiyatı/);
});
test('price matching review explicitly omits a fixed price and displays the method',()=>{
 const html=renderToStaticMarkup(<BotReview draft={{...initialBotDraft,options:{tif:'IOC',stp:'EXPIRE_BOTH',expires:'',priceMatch:'OPPONENT_5'}}}/>);
 assert.match(html,/OPPONENT_5/);assert.match(html,/sabit emir fiyatı gönderilmez/);
 assert.match(html,/Risk referansı/);assert.match(html,/IOC/);
});
