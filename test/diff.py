#!/usr/bin/env python3
"""
检测结果快照与差异比较工具 (方法三 + 方法四)

用法:
    python test/diff.py snapshot              # 对所有语料文件跑检测，保存快照
    python test/diff.py snapshot --label 修复前  # 带标签保存
    python test/diff.py compare               # 与最新快照对比（默认）
    python test/diff.py compare --against 修复前  # 与指定标签的快照对比
    python test/diff.py list                  # 列出所有已保存快照
    python test/diff.py show [标签]           # 查看快照详情

快照存放在 test/snapshots/ 目录。
语料文件列表读取自 test/corpus.txt。
"""

import json
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# 确保从项目根目录找到模块
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
SNAPSHOTS_DIR = Path(__file__).parent / 'snapshots'
CORPUS_FILE = Path(__file__).parent / 'corpus.txt'


def load_corpus() -> list[str]:
    """读取 corpus.txt，返回有效文件路径列表"""
    if not CORPUS_FILE.exists():
        print(f"[错误] 找不到语料列表文件: {CORPUS_FILE}")
        sys.exit(1)

    paths = []
    for line in CORPUS_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        p = Path(line)
        if not p.exists():
            print(f"  [跳过] 文件不存在: {line}")
            continue
        paths.append(str(p))
    return paths


def analyze_file(path: str, anonymizer) -> dict:
    """对单个文件运行检测，返回结构化结果"""
    try:
        # analyze_file 返回 {"action":..., "result": {"analysis": {"findings": {...}}}}
        # PDF 需要 use_ocr=True
        use_ocr = path.lower().endswith('.pdf')
        raw = anonymizer.analyze_file(path, use_ocr=use_ocr)
        if 'error' in raw:
            return {'ok': False, 'error': raw['error'], 'findings': {}, 'total': 0}
        findings_raw = raw.get('result', {}).get('analysis', {}).get('findings', {})
        # 统一成 {type: [text, ...]} 格式（去掉 context 包装）
        findings = {}
        for etype, items in findings_raw.items():
            texts = []
            for item in items:
                texts.append(item['text'] if isinstance(item, dict) else item)
            if texts:
                findings[etype] = sorted(set(texts))
        total = sum(len(v) for v in findings.values())
        return {'ok': True, 'findings': findings, 'total': total}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'findings': {}, 'total': 0}


def run_snapshot(label: Optional[str] = None) -> dict:
    """对所有语料文件运行检测，生成快照数据"""
    from anonymizer import LegalAnonymizer
    anonymizer = LegalAnonymizer()

    paths = load_corpus()
    if not paths:
        print("[错误] 语料文件列表为空或所有文件不存在")
        sys.exit(1)

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    snapshot = {
        'created_at': ts,
        'label': label or ts[:10],
        'files': {}
    }

    print(f"正在对 {len(paths)} 个文件进行检测...\n")
    for path in paths:
        short = Path(path).name
        print(f"  ▶ {short}", end='', flush=True)
        data = analyze_file(path, anonymizer)
        snapshot['files'][path] = data
        if data['ok']:
            print(f"  → {data['total']} 处")
        else:
            print(f"  → [错误] {data['error']}")

    return snapshot


def save_snapshot(snapshot: dict, label: Optional[str] = None) -> Path:
    """保存快照到文件"""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = (label or snapshot['label']).replace('/', '-').replace(' ', '_')
    ts_short = snapshot['created_at'].replace(':', '').replace(' ', '_')[:15]
    filename = f"{ts_short}_{safe_label}.json"
    out_path = SNAPSHOTS_DIR / filename
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')

    # 更新 latest 符号链接
    latest = SNAPSHOTS_DIR / 'latest.json'
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(filename)

    return out_path


def load_snapshot(label: Optional[str] = None) -> dict:
    """加载快照：不指定 label 则加载 latest"""
    if not label:
        p = SNAPSHOTS_DIR / 'latest.json'
        if not p.exists():
            print("[错误] 没有已保存的快照，请先运行: python test/diff.py snapshot")
            sys.exit(1)
        return json.loads(p.read_text(encoding='utf-8'))

    # 按标签查找
    candidates = list(SNAPSHOTS_DIR.glob('*.json'))
    for c in sorted(candidates, reverse=True):
        if c.name == 'latest.json':
            continue
        data = json.loads(c.read_text(encoding='utf-8'))
        if data.get('label') == label:
            return data

    print(f"[错误] 找不到标签为 '{label}' 的快照")
    print("已有快照：")
    cmd_list()
    sys.exit(1)


def diff_findings(old: dict, new: dict) -> dict:
    """比较两个 findings dict，返回 {added, removed, unchanged} 按类型"""
    all_types = set(old) | set(new)
    result = {}
    for t in sorted(all_types):
        old_set = set(old.get(t, []))
        new_set = set(new.get(t, []))
        added = sorted(new_set - old_set)
        removed = sorted(old_set - new_set)
        unchanged = len(old_set & new_set)
        result[t] = {
            'added': added,
            'removed': removed,
            'old_count': len(old_set),
            'new_count': len(new_set),
            'unchanged': unchanged,
        }
    return result


def cmd_snapshot(label: Optional[str] = None):
    """执行 snapshot 命令"""
    snapshot = run_snapshot(label)
    out_path = save_snapshot(snapshot, label)
    total = sum(d['total'] for d in snapshot['files'].values() if d['ok'])
    print(f"\n快照已保存: {out_path.name}")
    print(f"  标签: {snapshot['label']}")
    print(f"  时间: {snapshot['created_at']}")
    print(f"  文件数: {len(snapshot['files'])}  总检测: {total} 处")


def cmd_compare(against: Optional[str] = None):
    """执行 compare 命令"""
    from anonymizer import LegalAnonymizer
    anonymizer = LegalAnonymizer()

    baseline = load_snapshot(against)
    print(f"基准快照: {baseline['label']}  ({baseline['created_at']})\n")

    paths = load_corpus()
    if not paths:
        print("[错误] 语料文件列表为空")
        sys.exit(1)

    total_added = 0
    total_removed = 0

    for path in paths:
        short = Path(path).name
        old_data = baseline['files'].get(path)
        if old_data is None:
            print(f"⊕ {short}  [新增文件，基准中无记录]\n")
            continue

        print(f"▶ {short}", end='', flush=True)
        new_data = analyze_file(path, anonymizer)

        if not new_data['ok']:
            print(f"  → [错误] {new_data['error']}")
            continue

        delta = new_data['total'] - old_data['total']
        sign = f"+{delta}" if delta > 0 else str(delta)
        color = '' if delta == 0 else ('\033[32m' if delta < 0 else '\033[31m')
        reset = '\033[0m' if color else ''
        print(f"  {old_data['total']} → {new_data['total']} ({color}{sign}{reset})")

        diffs = diff_findings(old_data['findings'], new_data['findings'])
        has_diff = False
        for t, d in diffs.items():
            if d['added'] or d['removed']:
                has_diff = True
                old_c, new_c = d['old_count'], d['new_count']
                diff_sign = f"+{new_c - old_c}" if new_c > old_c else str(new_c - old_c)
                print(f"    [{t}] {old_c} → {new_c} ({diff_sign})")
                for item in d['removed']:
                    print(f"      \033[32m- {item}\033[0m")   # 绿色=移除（减少误报）
                for item in d['added']:
                    print(f"      \033[31m+ {item}\033[0m")   # 红色=新增（可能是误报）
        if not has_diff:
            print("    (无变化)")
        print()

        total_added += sum(len(d['added']) for d in diffs.values())
        total_removed += sum(len(d['removed']) for d in diffs.values())

    print("─" * 50)
    print(f"汇总: 新增检测 {total_added} 处  减少检测 {total_removed} 处")
    print("  (绿色=减少的检测项  红色=新增的检测项)")


def cmd_list():
    """列出所有已保存快照"""
    if not SNAPSHOTS_DIR.exists():
        print("尚无快照。运行: python test/diff.py snapshot")
        return

    files = sorted([f for f in SNAPSHOTS_DIR.glob('*.json') if f.name != 'latest.json'], reverse=True)
    if not files:
        print("尚无快照。运行: python test/diff.py snapshot")
        return

    latest_target = None
    latest_link = SNAPSHOTS_DIR / 'latest.json'
    if latest_link.is_symlink():
        latest_target = latest_link.resolve().name

    print(f"已保存 {len(files)} 个快照:\n")
    for f in files:
        data = json.loads(f.read_text(encoding='utf-8'))
        total = sum(d['total'] for d in data['files'].values() if d.get('ok'))
        marker = ' ← latest' if f.name == latest_target else ''
        print(f"  {data['label']:20s}  {data['created_at']}  {total:4d}处  {f.name}{marker}")


def cmd_show(label: Optional[str] = None):
    """显示快照详情"""
    snapshot = load_snapshot(label)
    print(f"快照: {snapshot['label']}  ({snapshot['created_at']})\n")
    for path, data in snapshot['files'].items():
        short = Path(path).name
        if not data['ok']:
            print(f"  {short}: [错误] {data['error']}")
            continue
        print(f"  {short}: {data['total']} 处")
        for etype, items in sorted(data['findings'].items()):
            print(f"    [{etype}] {', '.join(items[:5])}{'...' if len(items) > 5 else ''}")


def main():
    parser = argparse.ArgumentParser(
        description='检测结果快照与差异对比工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test/diff.py snapshot --label 修复house_number前
  # 做代码修改 #
  python test/diff.py compare --against 修复house_number前
  python test/diff.py list
        """
    )
    sub = parser.add_subparsers(dest='cmd')

    p_snap = sub.add_parser('snapshot', help='保存当前检测结果快照')
    p_snap.add_argument('--label', '-l', help='快照标签（默认用日期）')

    p_cmp = sub.add_parser('compare', help='与已保存快照比较')
    p_cmp.add_argument('--against', '-a', help='对比的快照标签（默认 latest）')

    sub.add_parser('list', help='列出所有已保存快照')

    p_show = sub.add_parser('show', help='显示快照详情')
    p_show.add_argument('label', nargs='?', help='快照标签（默认 latest）')

    args = parser.parse_args()

    if args.cmd == 'snapshot':
        cmd_snapshot(args.label)
    elif args.cmd == 'compare':
        cmd_compare(args.against)
    elif args.cmd == 'list':
        cmd_list()
    elif args.cmd == 'show':
        cmd_show(getattr(args, 'label', None))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
