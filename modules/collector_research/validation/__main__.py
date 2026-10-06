import argparse
from . import runtime

def main():
    parser=argparse.ArgumentParser(description='Reuse frozen four-family predictions on common complete-data windows')
    parser.add_argument('action',choices=['snapshot','audit','run','status'])
    parser.add_argument('--collector-root',required=True)
    parser.add_argument('--collector-work',required=True)
    parser.add_argument('--source-run',required=True)
    parser.add_argument('--run-dir',required=True)
    parser.add_argument('--resource-policy',choices=['local','server'],default='local')
    parser.add_argument('--workers',type=int)
    parser.add_argument('--minimum-days',type=int,default=30)
    parser.add_argument('--audit-device',choices=['auto','cpu','cuda'],default='auto')
    parser.add_argument('--publish-source-report',action='store_true')
    parser.add_argument('--fraction-study')
    parser.add_argument('--percent-study')
    args=parser.parse_args()
    if args.minimum_days<2:parser.error('At least two days are needed to include the closing day')
    if args.workers is not None and args.workers<1:parser.error('workers must be positive')
    if args.action=='status':
        from pathlib import Path
        path=Path(args.run_dir)/'status.json'
        print(path.read_text() if path.exists() else '{"status":"NOT_STARTED"}');return
    runtime.configure(args)
    if args.action=='snapshot':
        if not args.fraction_study or not args.percent_study:parser.error('snapshot requires both explicit study directories')
        from .snapshot import snapshot
        snapshot(args.fraction_study,args.percent_study);return
    from .audit import plan
    if args.action=='audit':
        if (runtime.RUN/'NATIVE_RESULTS.json').exists():raise RuntimeError('Freeze is already used by account results; use a new run-dir to change the plan')
        from pipeline.common import exclusive_lock
        with exclusive_lock():result=plan(runtime.RUN,runtime.RUN/'plan-progress.json')
        print(f'Frozen {len(result["windows"])} windows, {result["eligible_days"]}/{result["requested_days"]} days, {result["total_cases"]} cases')
    else:
        from .runner import run
        run()

if __name__=='__main__':main()
