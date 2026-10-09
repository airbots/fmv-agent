import argparse
import json
import os
import uuid
from pathlib import Path
from fmv.platform.store import Store
from fmv.platform.worker import process

def main():
    parser=argparse.ArgumentParser(prog='fmv-platform')
    commands=parser.add_subparsers(dest='command',required=True)
    s=commands.add_parser('submit'); s.add_argument('task_json')
    s=commands.add_parser('submit-ticker');s.add_argument('ticker');s.add_argument('--discount-rate',type=float);s.add_argument('--terminal-growth',type=float);s.add_argument('--growth',type=float,nargs='+')
    commands.add_parser('run-once')
    batch=commands.add_parser('run-pending');batch.add_argument('--max-tasks',type=int,default=3)
    commands.add_parser('status')
    args=parser.parse_args()
    root=Path(os.environ.get('FMV_RUNTIME',Path.cwd()/'runtime'))
    db=Store(root/'state.db')
    if args.command=='submit':
        data=json.loads(Path(args.task_json).read_text())
        task_id=data.get('id') or str(uuid.uuid4())
        db.submit(task_id,data['ticker'],data);print('Submitted',task_id)
    elif args.command=='submit-ticker':
        task_id=str(uuid.uuid4())
        data={'ticker':args.ticker,'type':'sec_valuation'}
        supplied=[args.discount_rate is not None,args.terminal_growth is not None,args.growth is not None]
        if any(supplied) and not all(supplied): parser.error('Provide all forecast parameters or none for model-assisted hypotheses')
        if all(supplied):
            data['assumptions']={'discount_rate':args.discount_rate,'terminal_growth':args.terminal_growth,'growth_rates':args.growth}
        db.submit(task_id,args.ticker.upper(),data);print('Submitted',task_id)
    elif args.command=='run-pending':
        if not 1 <= args.max_tasks <= 20:
            parser.error('--max-tasks must be between 1 and 20')
        failures=0
        for _ in range(args.max_tasks):
            task=db.claim()
            if task is None: break
            try:
                result=process(db,task,root/'artifacts',os.environ.get('FMV_MODEL','deepseek-r1:32b'),os.environ.get('FMV_SKIP_LLM')!='1')
                print('Result',result['ticker'],result['valuation']['fair_value_per_share'])
            except Exception as exc:
                failures+=1
                print('Task',task['id'],'needs review:',exc)
        if failures: raise SystemExit(1)
    elif args.command=='run-once':
        task=db.claim()
        if task:
            try:
                result=process(db,task,root/'artifacts',os.environ.get('FMV_MODEL','deepseek-r1:32b'),os.environ.get('FMV_SKIP_LLM')!='1')
                print('Result',result['ticker'],result['valuation']['fair_value_per_share'])
            except Exception as e:
                print('Task needs attention:',e)
                raise SystemExit(1)
        else: print('No pending tasks')
    else:
        for row in db.tasks():print(json.dumps(row))
if __name__=='__main__':main()
