"""Explicit-site launcher for the byte-preserved collector pipeline."""
import argparse,os,runpy,sys
from pathlib import Path
from modules.collector_research.validation import runtime

def main():
    p=argparse.ArgumentParser(description='Collect/normalize/label/train the four-family collector package')
    p.add_argument('--work-dir',required=True)
    p.add_argument('--resource-policy',choices=['local','server'],default='local')
    p.add_argument('pipeline_args',nargs=argparse.REMAINDER)
    a=p.parse_args();module=Path(__file__).resolve().parent
    settings=dict(collector_root=str(module),collector_work=str(Path(a.work_dir).resolve()),
        source_run=str(Path(a.work_dir).resolve()/'automation/source'),run_dir=str(Path(a.work_dir).resolve()/'automation/control'),
        resource_policy=a.resource_policy,workers=None,minimum_days=30,publish_source_report=False,audit_device='auto')
    os.environ['COIN_VALIDATION_SETTINGS']=__import__('json').dumps(settings);runtime.load_settings();resources=runtime.kernel_guard()
    if Path(a.work_dir).resolve().is_relative_to(runtime.REPO):raise ValueError('work-dir must be outside the checkout')
    os.environ.setdefault('NUM_THREADS',str(resources['cpu_count'] if a.resource_policy=='server' else 4))
    os.environ.setdefault('DEVICE','cuda' if a.resource_policy=='server' else 'cpu')
    if a.resource_policy=='local' and os.environ['DEVICE']!='cpu':raise ValueError('Local execution keeps GPU disabled')
    sys.argv=['pipeline.cli',*a.pipeline_args];runpy.run_module('pipeline.cli',run_name='__main__')

if __name__=='__main__':main()
