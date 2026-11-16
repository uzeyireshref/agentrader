"""Verify current source hashes and the deliberately limited local release scope."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.acceptance.release import verify


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'reports/exchange-development-20261115/reliability-priority-validation.json')
    args=parser.parse_args(argv);result=verify(ROOT,args.report)
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0 if result['status']=='LOCAL_SCOPE_VERIFIED_EXTERNAL_ACCEPTANCE_PENDING' else 1


if __name__=='__main__':raise SystemExit(main())
