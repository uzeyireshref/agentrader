import {defaultExecution,defaultGrid,type BotDraft} from './botPrototype';

/** Live plans start with no example prices or implicit financial budget. */
export function createLiveBotDraft(symbol='BTCUSDT'):BotDraft {
 return {symbol,side:'Long',kind:'SINGLE',entry:'',stop:'',target:'',amount:'',
  grid:{...defaultGrid,lower:'',upper:'',budget:'',upperStop:''},
  execution:{...defaultExecution,trigger:''}};
}
