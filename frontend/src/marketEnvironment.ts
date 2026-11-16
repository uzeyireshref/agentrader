// Pinned alongside agentrader/shared/market_environment.py. No client environment toggle.
export const marketSource='binance_usdm_demo_trade_price';
export const marketEnvironment='demo_public';
export function isDemoMarket(value:unknown):boolean {
 const v=value as Record<string,unknown>|null;
 return !!v&&v.source===marketSource&&v.environment===marketEnvironment&&v.product==='USD-M'&&v.price_type==='LAST_PRICE';
}
