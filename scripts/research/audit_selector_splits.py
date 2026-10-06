"""Inventory historical metadata and selection records without reading locks.

The audit grants no new data access. Unknown or previously inspected periods
never become an independent validation/test merely through a new split name.
"""
import argparse,hashlib,json,os,re
from pathlib import Path
from datetime import UTC,datetime
from quant.paths import ROOT,STATE

LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def inventory():
    paths=set()
    for folder in ('protocols','reports'):
        paths.update((ROOT/folder).rglob('*.json'))
    paths.update((ROOT/'docs').rglob('*.md'))
    # STATE is on the D-hosted VHD. Prune runtimes, raw storage and locks;
    # enumerate metadata manifests only, not datasets, models or label bodies.
    excluded=('env','venv','cache','node_modules','locked','holdout','raw','site-packages')
    for parent,dirs,files in os.walk(STATE,followlinks=False):
        dirs[:]=[n for n in dirs if not any(v in n.lower() for v in excluded) and not (Path(parent)/n).is_symlink()]
        for n in files:
            if 'manifest' in n.lower() and n.lower().endswith('.json') and n!='dataset_lock.json':paths.add(Path(parent)/n)
    paths.add(ROOT/'reports/experiment_registry.jsonl')
    return sorted(p for p in paths if p.is_file() and not p.is_symlink() and p.name!='dataset_lock.json')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='docs/DATA_SPLIT_AUDIT.md');ap.add_argument('--json',default='reports/DATA_SPLIT_AUDIT.json');a=ap.parse_args()
    assert os.environ.get('COIN_TASK_ID') and sha(ROOT/'state/dataset_lock.json')==LOCK_SHA
    records=[];mentions={};failed=[]
    for p in inventory():
        if p.stat().st_size>16_000_000:raise ValueError('Oversize metadata requires explicit audit: '+str(p))
        body=p.read_text(encoding='utf-8-sig');digest=sha(p)
        # Record every file actually read, including failed/partial historical
        # receipts. Date mentions are evidence links, never access permission.
        dates=sorted(set(re.findall(r'(?<!\d)(?:202[1-6])-[01]\d-[0-3]\d',body)))
        if p.suffix=='.json':
            try:json.loads(body);parsed='JSON'
            except json.JSONDecodeError:parsed='INVALID_PRESERVED_RECEIPT';failed.append(str(p))
        else:parsed='TEXT_SELECTION_OR_STATUS_RECORD'
        records.append(dict(path=str(p),sha256=digest,bytes=p.stat().st_size,parse=parsed,date_mentions=dates))
        for date in dates:mentions.setdefault(date,[]).append(str(p))
    rows=[
        ['2021-01-01 — 2022-01-01','已用作预热','BTC官方日线预热；非独立证据','仅许可特征预热；本次无标签','否','否'],
        ['2022-01-01 — 2024-01-01','已见','D099–D106策略、oracle与状态选择；TRAIN/DEVELOPMENT','是：本次唯一标签数据','只允许SEEN_CHRONOLOGICAL_VALIDATION；非真正独立OOS','否'],
        ['2024-01-01 — 2024-08-01','已见','D043完整213日策略开发/财务回放','仅既有授权开发；本runner不使用','不能冒称未见；本runner不使用','否'],
        ['2024-08-01 — 2024-09-01','来源缺口/被检查','BTC mark缺2分钟，完整547日来源被拒','本runner不使用；不能补零','否：未具完整来源','否'],
        ['2024-09-01 — 2025-07-01','已见','303日10币策略研究；SMA空头有保证金停止','仅完整合法输入的既有开发；本runner不使用','不能把停止前缀拼作共同完整对照','否'],
        ['2025-07-01 — 2026-03-01','已见或无法证明未见','既有ML/策略/carry研究；必须逐来源核角色','本runner不使用','不给独立validation资格','否：不能证明未受选择影响'],
        ['2026-03-01 — 2026-09-01','保留封存；正文未读','原FINAL LOCKED TEST；日期只引现有P04文档','否','否','保持封存候选；是否真正未见仍须未来启封前专项核验，未授权使用'],
        ['2026-09-01之后','公开采集/QA被观察','非冻结候选前向账户资格；连续性有断档','本runner不使用','不能自动称独立投资验证','不新建/启封test资格']]
    text=['# DATA SPLIT AUDIT','',
        '自动生成。来源是实际metadata/manifest、策略结果、decision log和experiment registry；文件清单/SHA在同名JSON。日期引用不授予权限。`state/dataset_lock.json`仅核SHA，未读取正文；不读取任何封存数据/模型/标签。',
        '', '|日期区间（结束不含）|是否已见|用途|是否允许训练|是否允许validation|是否仍可locked test|','|---|---|---|---|---|---|']
    text+=['|'+'|'.join(row)+'|' for row in rows]
    text+=['','## 本次冻结split','',
        'TRAIN/DEVELOPMENT为2022–2023。expanding chronological验证从2022-10-01开始，按季度到2024-01-01；各fold训练仅使用当时已成熟标签，并额外留至少H日embargo。该验证仍是已见历史内部验证，不能叫独立OOS。FINAL LOCKED TEST不消费，未测；不得因本次模型结果改日期或启封。',
        '',f'实际读取{len(records)}个metadata/manifest/文档/registry文件；{len(failed)}个历史JSON不完整，原字节保留并标INVALID，不作完成凭证。inventory排除运行时、raw、模型、locked/holdout目录；不以文件名含UNSEEN推定未见。',
        '2026-03至2026-09封存日期依据 docs/MODULE_P04.md，未解析锁正文；如元数据与原政策矛盾，封存权限仍不变。','']
    payload=dict(status='COMPLETE_CONSERVATIVE_METADATA_SPLIT_AUDIT_NO_LOCK_BODY',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
        generated_utc=datetime.now(UTC).isoformat(),records=records,intervals=rows,invalid_preserved_receipts=failed,lock_sha256=LOCK_SHA,locked_body_read=False,
        training_scope=['2022-01-01','2024-01-01'],validation_role='SEEN_CHRONOLOGICAL_INTERNAL_NOT_INDEPENDENT_OOS',final_test='NOT_AUTHORIZED_NOT_RUN')
    out=(ROOT/a.output).resolve();j=(ROOT/a.json).resolve();assert out.is_relative_to(ROOT/'docs') and j.is_relative_to(ROOT/'reports')
    with out.open('x',encoding='utf-8') as f:f.write('\n'.join(text))
    with j.open('x',encoding='utf-8') as f:json.dump(payload,f,indent=2,ensure_ascii=False);f.write('\n')
    print(json.dumps(dict(status=payload['status'],files=len(records),invalid=len(failed))))

if __name__=='__main__':main()
