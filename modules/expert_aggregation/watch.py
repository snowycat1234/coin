import argparse,time
from pathlib import Path
from .common import read

def display(state):
    p=state/'PROGRESS.json'
    if not p.exists():return '等待启动；尚未有已执行进度。'
    s=read(p);duration=int(time.time()-s['started']);minutes,seconds=divmod(duration,60);hours,minutes=divmod(minutes,60)
    lines=[f"专家组合 | {s['status']} | 模块 {s['stage']}/{s['stages']} | 本次 {hours:02}:{minutes:02}:{seconds:02}",s['label']]
    tasks=read(state/'TASKS.json') if (state/'TASKS.json').exists() else []
    completed=s.get('completed',0);total=s.get('total',len(tasks));actual=0
    lines.append(f"已审计账户 {completed}/{total} | 并行工作进程 {s['workers']} | 真实逐分钟进度如下")
    for task in tasks:
        f=state/'progress'/(task['id']+'.json')
        if not f.exists():continue
        v=read(f);cur=v['current'];n=v['total'];actual+=cur;width=18;done=int(width*cur/n) if n else 0
        age=int(time.time()-v['updated'])
        lines.append(f"{'█'*done}{'░'*(width-done)} {100*cur/n:5.1f}% {cur:>6}/{n} {task['id']} | {v['phase']} | 更新于{age}s前")
    if tasks:lines.append(f'已回放分钟合计 {actual:,}/{525600*len(tasks):,}（各自独立钱包，不相加收益）')
    if s.get('error'):lines.append('错误：'+s['error']+'；查看 '+str(state/'FAILURE.json'))
    if s.get('classification'):lines.append('研究结论：'+s['classification'])
    lines.append('报告 '+str(state/'delivery/REPORT.md')+' | 日志 '+str(state/'service.log'))
    return '\n'.join(lines)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',type=Path,required=True);parser.add_argument('--once',action='store_true');args=parser.parse_args()
    while True:
        print(('' if args.once else '\033[2J\033[H')+display(args.state),flush=True)
        if args.once:return
        try:time.sleep(3)
        except KeyboardInterrupt:return

if __name__=='__main__':main()
