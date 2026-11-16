"""Chart-only production adapter CLI. Reads its token from process environment."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from agentrader.integration.chart_bot import ChartBot,BotError


def main(argv=None):
    parser=argparse.ArgumentParser(description='Kısıtlı bot grafik adaptörü; emir veya hesap erişimi yok')
    parser.add_argument('--url',default='http://127.0.0.1:8765')
    parser.add_argument('--bot-id',default=os.environ.get('AGENTRADER_CHART_BOT_ID','chart-bot'))
    parser.add_argument('--strategy-id',default=os.environ.get('AGENTRADER_CHART_STRATEGY_ID','default'))
    parser.add_argument('--workspace',default='main');parser.add_argument('--journal',type=Path,required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('discover');commands.add_parser('identity');commands.add_parser('resume')
    watch=commands.add_parser('strategy-watch');watch.add_argument('--state',type=Path,required=True);watch.add_argument('--symbol',default='BTCUSDT');watch.add_argument('--interval',default='1m');watch.add_argument('--seconds',type=int,default=180);watch.add_argument('--poll',type=float,default=1);watch.add_argument('--trace',type=Path)
    for name in ('snapshot','own'):
        p=commands.add_parser(name);p.add_argument('symbol');p.add_argument('interval')
    run=commands.add_parser('run');run.add_argument('request_file',type=Path)
    args=parser.parse_args(argv)
    try:
        bot=ChartBot(args.url,os.environ.get('AGENTRADER_CHART_BOT_TOKEN',''),bot_id=args.bot_id,strategy_id=args.strategy_id,journal=args.journal,workspace_id=args.workspace)
        if args.command=='strategy-watch':
            from agentrader.integration.chart_strategy import DrawingStrategy
            if not 1<=args.seconds<=600 or not .5<=args.poll<=10:raise BotError('INVALID_STRATEGY_DURATION')
            if args.trace:
                trace=args.trace.resolve()
                if trace in (args.state.resolve(),args.journal.resolve()):raise BotError('STRATEGY_TRACE_MUST_BE_SEPARATE')
                trace.parent.mkdir(parents=True,exist_ok=True)
                class Trace:
                    def request(self,method,path,body=None):
                        status,value=bot.http.request(method,path,body)
                        row=dict(at=time.time(),method=method,path=path,status=status,request=body,response_sha256=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),response_schema=value.get('schema_version'),order_authority=False)
                        with trace.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
                        return status,value
                bot._transport=Trace()
            strategy=DrawingStrategy(bot,args.state,symbol=args.symbol,interval=args.interval);until=time.monotonic()+args.seconds
            while time.monotonic()<until:
                try:result=strategy.step()
                except BotError as error:result=dict(state='PENDING' if error.pending else 'REJECTED',reason=error.code,order_authority=False)
                print(json.dumps(result,ensure_ascii=False),flush=True)
                time.sleep(min(args.poll,max(0,until-time.monotonic())))
            return 0
        elif args.command=='identity':result=bot.identify()
        elif args.command=='discover':result=bot.discover()
        elif args.command=='snapshot':result=bot.snapshot(args.symbol,args.interval)
        elif args.command=='own':result=bot.find_own(args.symbol,args.interval)
        elif args.command=='resume':result=bot.resume_pending()
        else:
            raw=args.request_file.read_bytes()
            if len(raw)>65536:raise BotError('BOT_REQUEST_TOO_LARGE')
            def invalid(*args):raise BotError('INVALID_BOT_TASK')
            def pairs(items):
                result={}
                for k,v in items:
                    if k in result:raise BotError('INVALID_BOT_TASK')
                    result[k]=v
                return result
            task=json.loads(raw.decode('utf-8'),parse_constant=invalid,object_pairs_hook=pairs)
            if not isinstance(task,dict) or set(task)!={'action','arguments'} or not isinstance(task['arguments'],dict):raise BotError('INVALID_BOT_TASK')
            methods={name:getattr(bot,name) for name in ('create','update','delete','save_note','delete_note','operations','get','notes','history','calculate','indicator_queries','export_package','paste_package')}
            if task['action'] not in methods:raise BotError('BOT_ACTION_FORBIDDEN')
            result=methods[task['action']](**task['arguments'])
        print(json.dumps(dict(state='SUCCEEDED',result=result,order_authority=False),ensure_ascii=False,indent=2));return 0
    except BotError as error:
        print(json.dumps(dict(state='PENDING' if error.pending else 'REJECTED',error=dict(code=error.code,http_status=error.status),order_authority=False)));return 2 if error.pending else 1
    except (OSError,ValueError,TypeError):
        print(json.dumps(dict(state='REJECTED',error=dict(code='INVALID_BOT_TASK_OR_JOURNAL'),order_authority=False)));return 1
