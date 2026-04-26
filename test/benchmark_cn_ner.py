"""
中文 NER 模型对照实验

对比在同一份中英混合法律文书上：
  1. 纯规则（现有 PatternDetector + EntityDetector）
  2. 规则 + ckiplab/bert-tiny-chinese-ner  (~50MB, 繁体训练)
  3. 规则 + uer/roberta-base-finetuned-cluener2020-chinese  (~400MB, 简体 CLUENER)

输出指标：
  - 每个模型独立抓到的实体（text, type）
  - 与规则层重叠 vs 独有的分布
  - 明显误报（单字/标点/常见词被识别为人名）
"""

from __future__ import annotations

import os
import sys
import time
from typing import List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonymizer import LegalAnonymizer

SAMPLE_PATH = os.environ.get(
    "BENCHMARK_SAMPLE",
    os.path.join(os.path.dirname(__file__), "sample_mixed.txt"),
)


CANDIDATES = [
    ("tiny_繁体", "ckiplab/bert-tiny-chinese-ner"),
    ("base_简体CLUENER", "uer/roberta-base-finetuned-cluener2020-chinese"),
]


def load_pipeline(model_id: str):
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch

    device = "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else "cpu"
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForTokenClassification.from_pretrained(model_id)
    return pipeline(
        "token-classification",
        model=model,
        tokenizer=tok,
        aggregation_strategy="simple",
        device=device,
    )


def run_model(model_id: str, text: str) -> List[Tuple[str, str, int]]:
    t0 = time.time()
    pipe = load_pipeline(model_id)
    load_t = time.time() - t0

    t0 = time.time()
    spans = pipe(text)
    infer_t = time.time() - t0

    results = []
    for span in spans:
        label = span.get("entity_group") or span.get("entity") or ""
        # 清理 B-/I-/E-/S- 前缀
        for prefix in ("B-", "I-", "E-", "S-"):
            if label.startswith(prefix):
                label = label[len(prefix):]
                break
        start = int(span.get("start", 0))
        end = int(span.get("end", 0))
        score = float(span.get("score", 1.0))
        if end <= start or score < 0.5:
            continue
        txt = text[start:end].strip()
        if len(txt) < 2:
            continue
        results.append((txt, label, start))

    return results, load_t, infer_t


def rule_entities(text: str) -> List[Tuple[str, str, int]]:
    a = LegalAnonymizer(use_llm=False)
    return a._detect_all(text)


def overlap(a_start: int, a_len: int, b_start: int, b_len: int) -> bool:
    return a_start < b_start + b_len and b_start < a_start + a_len


def categorize(
    model_hits: List[Tuple[str, str, int]],
    rule_hits: List[Tuple[str, str, int]],
) -> Tuple[List, List]:
    """分类模型命中：与规则重叠的 vs 规则没抓到的（可能是补盲 or 误报）"""
    rule_spans = [(p, p + len(t)) for t, _, p in rule_hits]
    covered, novel = [], []
    for t, ty, p in model_hits:
        end = p + len(t)
        if any(overlap(p, len(t), rs, re_ - rs) for rs, re_ in rule_spans):
            covered.append((t, ty, p))
        else:
            novel.append((t, ty, p))
    return covered, novel


def main():
    text = open(SAMPLE_PATH).read()

    print("=" * 70)
    print("中文 NER 对照实验")
    print("=" * 70)

    rule_hits = rule_entities(text)
    rule_cn = [(t, ty, p) for t, ty, p in rule_hits if any("一" <= c <= "鿿" for c in t)]
    print(f"\n[规则层] 总命中 {len(rule_hits)}, 中文实体 {len(rule_cn)}")
    for t, ty, p in rule_cn:
        print(f"  [{ty:14s}] {t}")

    for label, model_id in CANDIDATES:
        print("\n" + "-" * 70)
        print(f"[模型] {label}  ({model_id})")
        print("-" * 70)
        try:
            hits, load_t, infer_t = run_model(model_id, text)
        except Exception as e:
            print(f"  加载/推理失败: {e}")
            continue

        print(f"  加载 {load_t:.1f}s | 推理 {infer_t:.2f}s | 总命中 {len(hits)}")

        covered, novel = categorize(hits, rule_hits)
        cn_novel = [(t, ty, p) for t, ty, p in novel if any("一" <= c <= "鿿" for c in t)]

        print(f"\n  ▸ 与规则重叠（交叉验证）: {len(covered)}")
        for t, ty, p in covered[:8]:
            print(f"      [{ty:10s}] {t}")
        if len(covered) > 8:
            print(f"      ... 还有 {len(covered) - 8}")

        print(f"\n  ▸ 规则没抓到、模型新发现的中文实体: {len(cn_novel)}  ← 核心价值")
        for t, ty, p in cn_novel:
            marker = ""
            # 简单误报检测：单字+常见虚词，或者明显是角色词
            if t in {"公司", "原告", "被告", "甲方", "乙方", "本案", "法院"} or len(t) < 2:
                marker = " [疑似误报]"
            print(f"      [{ty:10s}] {t}{marker}")

        eng_novel = [
            (t, ty, p) for t, ty, p in novel
            if not any("一" <= c <= "鿿" for c in t)
        ]
        if eng_novel:
            print(f"\n  ▸ 规则没抓到、模型发现的英文实体: {len(eng_novel)}")
            for t, ty, p in eng_novel[:8]:
                print(f"      [{ty:10s}] {t}")


if __name__ == "__main__":
    main()
