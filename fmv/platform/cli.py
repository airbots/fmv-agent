import argparse
import json
import os
import uuid
from pathlib import Path
from fmv.platform.store import Store
from fmv.platform.worker import process

ROOT=Path(os.environ.get('FMV_RUNTIME',Path.cwd()/'runtime'))
def main():
    parser=argparse.ArgumentParser(prog='fmv-platform')
    commands=parser.add_subparsers(dest='command',required=True)
    s=commands.add_parser('submit'); s.add_argument('task_json')
    commands.add_parser('run-once')
    commands.add_parser('status')
    args=parser.parse_args()
    db=Store(ROOT/'state.db')
    if args.command=='submit':
        payload=json.loads(Path(args.task_json).read_text())
        id=payload.get('id') or str(uuid.uuid4())
        db.submit(id,payload['ticker'],payload)
        print('Submitted:',id)
    elif args.command=='run-once':
        task=db.claim()
        if task:
            result=process(db,task,ROOT/'artifacts',os.environ.get('FMV_MODEL','deepseek-r1:32b'),os.environ.get('FMV_SKIP_LLM')!='1')
            print('Completed:',result['task_id'],result['valuation']['fair_value_per_share'])
        else: print('No pending tasks')
    else:
        for row in db.tasks(): print(json.dumps(row))
if __name__=='__main__': main()
