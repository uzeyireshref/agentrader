"""Review legacy execution provenance; apply only explicit local attestation."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.shared.legacy_execution import attest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--account-ref',required=True)
    parser.add_argument('--context',choices=['usdm-demo'],required=True)
    parser.add_argument('--apply-local',action='store_true')
    args=parser.parse_args()
    print(json.dumps(attest(args.database,args.owner,args.account_ref,context=args.context,apply=args.apply_local)))
