#!/usr/bin/env python3
"""遍历 sweep_results 重新做漏检审计（如 sweep_runner 中途崩溃只剩文件，可单独跑这个）"""
import json
import os
import sys
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test" / "sweep_results"

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
sys.path.insert(0, str(ROOT))

from anonymizer import LegalAnonymizer

a = LegalAnonymizer()
audits = []
for txt_path in sorted(OUT.glob("*.txt")):
    if txt_path.name.startswith('_'):
        continue
    name = txt_path.stem
    text = txt_path.read_text(encoding='utf-8', errors='ignore')
    findings = a.analyze_text(text).get('findings', {})
    leaks = []
    for ty, items in findings.items():
        for item in items:
            if item.startswith('[') and item.endswith(']'):
                continue
            leaks.append({'type': ty, 'text': item})
    audits.append({'name': name, 'leaks': leaks[:50]})

# write
out_md = OUT / '_audit_check.md'
lines = [f'# 漏检审计 (复跑) {time.strftime("%Y-%m-%d %H:%M")}\n']
for a_ in audits:
    lines.append(f"## {a_['name']}")
    if not a_['leaks']:
        lines.append('✅ 无漏检\n')
    else:
        lines.append(f"⚠️ {len(a_['leaks'])} 条漏检：")
        for l in a_['leaks'][:20]:
            lines.append(f"- `{l['type']}`: `{l['text']}`")
        lines.append('')
out_md.write_text('\n'.join(lines), encoding='utf-8')
(OUT / '_audit_check.json').write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Audit check written: {out_md}")
