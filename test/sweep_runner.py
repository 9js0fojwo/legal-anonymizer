#!/usr/bin/env python3
"""
10份 PDF 全测试扫描

读取 /tmp/pdf_sweep.txt（kind|name|path），对每份跑脱敏，
保存输出到 test/sweep_results/，并对每份做漏脱敏审计。
"""

from __future__ import annotations
import json
import os
import re
import sys
import time
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "test" / "sweep_results"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY = OUT_DIR / "_summary.md"
DETECT_LOG = OUT_DIR / "_audit.json"

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
sys.path.insert(0, str(ROOT))


def is_scanned_pdf(path: str) -> bool:
    """判断是文字层 PDF 还是图片型/扫描型 PDF（看前 3 页文字层占比）"""
    try:
        import fitz
        doc = fitz.open(path)
        n_check = min(3, len(doc))
        total_text = 0
        for i in range(n_check):
            total_text += len(doc[i].get_text("text").strip())
        doc.close()
        return total_text < 40 * n_check  # 平均每页 <40 字符 ≈ 扫描版
    except Exception:
        return False


def run_one(idx: int, kind: str, name: str, src: str) -> dict:
    safe_name = re.sub(r'[^\w一-龥]+', '_', name).strip('_')
    out_pdf = OUT_DIR / f"{idx:02d}_{safe_name}.pdf"
    out_txt = out_pdf.with_suffix('.txt')
    out_map = OUT_DIR / f"{idx:02d}_{safe_name}_mapping.json"

    actually_scan = is_scanned_pdf(src)
    cmd = [
        sys.executable, str(ROOT / "cli.py"), "anonymize", src,
        "-o", str(out_pdf),
        "--mask-strategy", "placeholder",
    ]
    if actually_scan:
        cmd += ["--ocr"]

    print(f"\n[{idx:02d}/{10}] {kind} | {name}")
    print(f"     src     : {src}")
    print(f"     scanned : {actually_scan}")
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    dt = time.time() - t0
    print(f"     elapsed : {dt:.1f}s exit={res.returncode}")

    audit = {
        'idx': idx, 'kind': kind, 'name': name, 'src': src,
        'is_scanned': actually_scan,
        'elapsed_s': round(dt, 1),
        'exit_code': res.returncode,
        'error': None,
        'leaks': [],
        'totals': {},
        'output_pdf': str(out_pdf) if out_pdf.exists() else None,
        'output_txt': str(out_txt) if out_txt.exists() else None,
        'output_mapping': str(out_map) if out_map.exists() else None,
    }
    if res.returncode != 0:
        audit['error'] = res.stderr[-1500:]
        print(f"     [FAIL] {audit['error'][:200]}")
        return audit

    # 漏检审计：对脱敏后的 .txt 跑 LegalAnonymizer.analyze_text
    if out_txt.exists():
        anonymized = out_txt.read_text(encoding='utf-8', errors='ignore')
        from anonymizer import LegalAnonymizer
        a = LegalAnonymizer()
        analysis = a.analyze_text(anonymized)
        leaks = []
        for ty, items in analysis.get('findings', {}).items():
            for item in items:
                if item.startswith('[') and item.endswith(']'):
                    continue  # placeholder 不算泄漏
                leaks.append({'type': ty, 'text': item})
        audit['leaks'] = leaks[:50]
        print(f"     leaks   : {len(leaks)} (top 5: {[l['text'] for l in leaks[:5]]})")

    if out_map.exists():
        try:
            data = json.loads(out_map.read_text(encoding='utf-8'))
            meta = data.get('metadata', {})
            audit['totals'] = {
                'entities': meta.get('entity_count'),
                'replacements': meta.get('replacements_made'),
            }
        except Exception:
            pass

    return audit


def main():
    sweep_file = Path("/tmp/pdf_sweep.txt")
    audits = []
    with sweep_file.open() as f:
        rows = [l.strip().split('|', 2) for l in f if l.strip() and not l.startswith('#')]
    for i, (kind, name, src) in enumerate(rows, 1):
        try:
            audits.append(run_one(i, kind, name, src))
        except subprocess.TimeoutExpired:
            audits.append({'idx': i, 'kind': kind, 'name': name, 'src': src,
                           'error': 'TIMEOUT', 'leaks': [], 'totals': {}})
            print('     [TIMEOUT 15min]')
        except Exception as e:
            audits.append({'idx': i, 'kind': kind, 'name': name, 'src': src,
                           'error': str(e), 'leaks': [], 'totals': {}})
            print(f'     [EXCEPTION] {e}')

    DETECT_LOG.write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = ['# 10 份 PDF 脱敏全扫描结果\n', f'生成时间：{time.strftime("%Y-%m-%d %H:%M")}\n']
    lines.append('| # | 类别 | 名称 | 实体数 | 漏脱 | 用时 | 状态 |')
    lines.append('|---|------|------|--------|------|------|------|')
    for a in audits:
        ent = a['totals'].get('entities', '-')
        leaks = len(a['leaks'])
        elapsed = a.get('elapsed_s', '-')
        status = '✅' if (a.get('error') is None and leaks == 0) else (
            '🟡 漏脱敏' if a.get('error') is None else '❌ 错误')
        lines.append(f"| {a['idx']:02d} | {a['kind']} | {a['name']} | {ent} | {leaks} | {elapsed}s | {status} |")
    lines.append('\n## 各文档漏脱敏明细\n')
    for a in audits:
        lines.append(f"### {a['idx']:02d}. {a['name']}")
        if a.get('error'):
            lines.append(f"❌ 错误：`{(a['error'] or '')[:200]}`\n")
            continue
        if not a['leaks']:
            lines.append("✅ 全部脱敏，无漏检。\n")
            continue
        lines.append('漏脱敏实体（脱敏后文本中仍可识别为敏感信息）：\n')
        lines.append('| 类型 | 文本 |')
        lines.append('|------|------|')
        for l in a['leaks']:
            txt = l['text'].replace('|', '\\|')
            lines.append(f"| {l['type']} | `{txt}` |")
        lines.append('')
    SUMMARY.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n=== Summary written: {SUMMARY}")


if __name__ == "__main__":
    main()
