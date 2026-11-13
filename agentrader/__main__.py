import argparse
import json
import logging
import sys
import os
from decimal import Decimal

from .config import Config
from .exchange import BASE_URL, DemoExchange, ExchangeError
from .orders import order_cycle
from .positions import position_cycle
from .execution import DurableExchange, reconcile
from .state import StateStore
from .locking import execution_lock
from .risk import RiskLimits
from .watchdog import Watchdog, watch_loop


def diagnose(config, symbol, account=False):
    exchange = DemoExchange(config)
    report = {"environment": "demo", "product": "USD-M Futures",
              "base_url": BASE_URL, "read_only": True}
    exchange.get("/fapi/v1/ping")
    report["connection"] = "ok"
    report["time"] = exchange.sync_time()
    info = exchange.get("/fapi/v1/exchangeInfo")
    selected = next((s for s in info["symbols"] if s["symbol"] == symbol), None)
    if selected is None:
        raise ExchangeError(f"Sembol demo ortamında bulunamadı: {symbol}")
    report["symbol"] = {key: selected.get(key) for key in
                        ("symbol", "status", "contractType", "baseAsset", "quoteAsset", "filters")}
    report["account"] = {"status": "skipped", "reason": "Hesap kontrolü için --account kullanın."}
    if account:
        data = exchange.get("/fapi/v3/account")
        account_config = exchange.get('/fapi/v1/accountConfig')
        orders = exchange.get("/fapi/v1/openOrders")
        mode = exchange.get("/fapi/v1/positionSide/dual")
        report["account"] = {
            "status": "ok", "can_trade": account_config.get("canTrade"),
            "position_mode": "hedge" if mode["dualSidePosition"] else "one-way",
            "balances": [{k: a.get(k) for k in ("asset", "walletBalance", "availableBalance")}
                         for a in data["assets"] if Decimal(a["walletBalance"]) != 0],
            "positions": [{k: p.get(k) for k in ("symbol", "positionSide", "positionAmt", "unrealizedProfit")}
                          for p in data["positions"] if Decimal(p["positionAmt"]) != 0],
            "open_order_count": len(orders),
        }
    return report


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if len(sys.argv)>1 and sys.argv[1]=='web':
        from .web_cli import main as web_main
        return web_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='service':
        from .service_cli import main as service_main
        return service_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='notifications':
        from .notification_cli import main as notification_main
        return notification_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='orders':
        from .order_cli import main as order_main
        return order_main(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1]=='settings':
        from .settings_cli import main as settings_main
        return settings_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'capabilities':
        from .capability_cli import main as capability_main
        return capability_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'grid':
        from .grid_cli import main as grid_main
        return grid_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'plans':
        from .plan_cli import main as plan_main
        return plan_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == 'market':
        from .market_cli import main as market_main
        return market_main(sys.argv[2:])
    parser = argparse.ArgumentParser(description="Binance USD-M Futures demo araçları")
    parser.add_argument("command", choices=["web", "diagnose", "plans", "market", "grid", "capabilities", "settings", "orders", "order-cycle", "position-cycle", "recover", "managed-open", "watchdog", "managed-close", "managed-finalize"], help="Alt komutlar: plans, orders, market, grid, capabilities veya settings --help")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--account", action="store_true", help="Demo hesap bilgilerini de oku")
    parser.add_argument("--execute-demo", action="store_true", help="Demo limit emrini gönder, sorgula ve iptal et")
    parser.add_argument('--clear-halt', action='store_true', help='Yalnızca recover: temiz demo hesapta kalıcı durdurmayı kaldır')
    parser.add_argument('--risk-profile', default='risk-demo.json', help='Demo risk sınırları JSON dosyası')
    parser.add_argument('--iterations', type=int, default=1, help='Watchdog tur sayısı; 0 sürekli')
    parser.add_argument('--interval', type=int, default=5, help='Watchdog turları arası saniye (1–60)')
    parser.add_argument('--crash-after-ready', action='store_true', help='Yalnızca demo kesinti testi: koruma kurulduktan sonra süreci aniden bitir')
    parser.add_argument('--test-only', action='store_true', help='Yalnızca eski, açıkça istenen demo altyapı deneyleri; plan onayı yerine geçmez')
    args = parser.parse_args()
    if args.execute_demo and args.command in ('order-cycle', 'position-cycle', 'managed-open') and not args.test_only:
        parser.error('Yeni işlem için plans akışını kullanın. Eski altyapı deneyleri ayrıca --test-only gerektirir.')
    if args.clear_halt and args.command != 'recover':
        parser.error('--clear-halt yalnızca recover ile kullanılabilir.')
    if args.execute_demo and args.command not in ('order-cycle', 'position-cycle', 'managed-open', 'watchdog', 'managed-close'):
        parser.error('--execute-demo yalnızca emir/pozisyon deneyiyle kullanılabilir.')
    if args.crash_after_ready and (args.command != 'managed-open' or not args.execute_demo):
        parser.error('--crash-after-ready yalnızca managed-open --execute-demo ile kullanılabilir.')
    if args.iterations < 0 or not 1 <= args.interval <= 60:
        parser.error('iterations >= 0 ve interval 1–60 olmalı.')
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        config = Config.load()
        if args.command == 'diagnose':
            report = diagnose(config, args.symbol.upper(), args.account)
        elif args.command in ('managed-open', 'watchdog', 'managed-close', 'managed-finalize'):
            with execution_lock():
                store = StateStore()
                try:
                    exchange = DemoExchange(config)
                    watchdog = Watchdog(exchange, store, RiskLimits.load(args.risk_profile))
                    watchdog.engine.test_only = args.test_only
                    if args.command == 'managed-finalize':
                        report = watchdog.finalize_flat()
                    elif args.command == 'managed-open':
                        report = (watchdog.open(args.symbol.upper()) if args.execute_demo
                                  else position_cycle(config, args.symbol.upper()))
                        if args.crash_after_ready:
                            if report['status'] != 'protected':
                                raise ValueError('Koruma doğrulanmadı; çökme testi yapılmadı.')
                            store.event('demo_process_crash_requested', report)
                            print(json.dumps(report, ensure_ascii=False), flush=True)
                            os._exit(73)
                    else:
                        for result in watch_loop(watchdog, args.execute_demo, args.iterations,
                                                 args.interval, close=args.command == 'managed-close'):
                            print(json.dumps(result, ensure_ascii=False), flush=True)
                        return 1 if result['status'] == 'alarm' else 0
                finally:
                    store.close()
        elif args.command == 'recover' or args.execute_demo:
            with execution_lock():
                store = StateStore()
                try:
                    exchange = DemoExchange(config)
                    recovery = reconcile(exchange, store, args.clear_halt if args.command == 'recover' else False)
                    if args.command == 'recover':
                        report = recovery
                    else:
                        if not recovery['ready']:
                            raise ValueError('Uzlaştırma tamamlanmadı: ' + str(recovery['halt_reason']))
                        cycle = position_cycle if args.command == 'position-cycle' else order_cycle
                        limits = RiskLimits.load(args.risk_profile)
                        try:
                            report = cycle(config, args.symbol.upper(), True,
                                           exchange_factory=lambda _: DurableExchange(exchange, store, limits, test_only=args.test_only))
                        except Exception:
                            store.halt('Demo deneyi hata verdi; recover ile kontrol edin.')
                            raise
                        report['recovery'] = reconcile(exchange, store)
                finally:
                    store.close()
        else:
            cycle = position_cycle if args.command == 'position-cycle' else order_cycle
            report = cycle(config, args.symbol.upper(), args.execute_demo)
    except (ValueError, ExchangeError, OSError) as exc:
        logging.error("%s", exc)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
