"""
Chinese NER Detector (CLUENER)
基于 uer/roberta-base-finetuned-cluener2020-chinese 的中文命名实体识别检测器

CLUENER2020 标签体系（10 类）及本项目的处理策略：
  name         → person       人名
  company      → company      公司名
  address      → full_address 地址
  government   → government   政府机关
  organization → institution  机构
  position     → (默认丢弃)    职位；但"上官/司马/欧阳"等复姓模式会被合并到相邻 name
  book         → (丢弃)        书名（《民法典》这类非 PII）
  movie / game / scene → (丢弃) 非 PII 类别

设计要点：
  1. 懒加载 + 进程级单例（复用 llm_detector 的模式）
  2. 复姓粘合：CLUENER 有时会把复姓人名（如"司马XX"）切成 position="司马" + name="XX"，
     本检测器在后处理里识别复姓并合并成完整人名
  3. 误报过滤：书名、景点、电影等标签直接丢弃
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "uer/roberta-base-finetuned-cluener2020-chinese"

# CLUENER → 项目类型
LABEL_MAP = {
    "name": "person",
    "company": "company",
    "address": "full_address",
    "government": "government",
    "organization": "institution",
    # 以下默认丢弃（在 KEEP_POSITIONS 里单独处理 position）
    "position": None,
    "book": None,
    "movie": None,
    "game": None,
    "scene": None,
}

# CLUENER 常把复姓切成 position="上官"+name="文渊"，这里收录常见复姓做粘合
COMPOUND_SURNAMES = {
    "欧阳", "太史", "端木", "上官", "司马", "东方", "独孤", "南宫",
    "万俟", "闻人", "夏侯", "诸葛", "尉迟", "公羊", "赫连", "澹台",
    "皇甫", "宗政", "濮阳", "公冶", "太叔", "申屠", "公孙", "慕容",
    "仲孙", "钟离", "长孙", "宇文", "司徒", "鲜于", "司空", "令狐",
}


class CNNERDetector:
    """中文 NER 检测器（CLUENER），懒加载单例共享"""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        device: Optional[str] = None,
        min_score: float = 0.7,
        max_chars: int = 400,
        keep_position: bool = False,
    ):
        """
        Args:
            min_score: CLUENER 上阈值稍高（0.7）以压低误报
            keep_position: 是否保留 position 类型（默认丢弃；法律文书里"律师/法官"不算 PII）
            max_chars: 分段长度。模型 max_position_embeddings=512，中文近 1 字 1 token，
                       默认 400 留安全余量（含 [CLS]/[SEP]/OOV 等额外 token）
        """
        self.model_id = model_id
        self.device = device
        self.min_score = min_score
        self.max_chars = max_chars
        self.keep_position = keep_position

        self._pipeline = None
        self._load_error: Optional[str] = None

    # ---------------- 懒加载 ----------------

    def _ensure_loaded(self) -> bool:
        if self._pipeline is not None:
            return True
        if self._load_error is not None:
            return False
        try:
            import torch  # noqa: F401
            from transformers import (
                AutoModelForTokenClassification,
                AutoTokenizer,
                pipeline,
            )
        except ImportError as e:
            self._load_error = f"缺少依赖：{e.name}。请先安装：pip install torch transformers"
            logger.warning(self._load_error)
            return False

        try:
            import torch

            device = self.device
            if device is None:
                if torch.cuda.is_available():
                    device = "cuda"
                elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"

            logger.info(f"[cn_ner] loading {self.model_id} on {device} ...")
            tok = AutoTokenizer.from_pretrained(self.model_id)
            mdl = AutoModelForTokenClassification.from_pretrained(self.model_id)
            self._pipeline = pipeline(
                task="token-classification",
                model=mdl,
                tokenizer=tok,
                aggregation_strategy="simple",
                device=device,
            )
            return True
        except Exception as e:
            self._load_error = f"模型加载失败: {e}"
            logger.exception(self._load_error)
            return False

    @property
    def available(self) -> bool:
        return self._ensure_loaded()

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    # ---------------- 检测 ----------------

    def detect(
        self,
        text: str,
        only_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
    ) -> List[Tuple[str, str, int]]:
        if not text or not self._ensure_loaded():
            return []

        raw_spans: List[Tuple[str, str, int]] = []  # (text, raw_label, start)
        offset = 0
        for chunk in self._split_chunks(text, self.max_chars):
            try:
                spans = self._pipeline(chunk)
            except Exception as e:
                logger.warning(f"[cn_ner] inference failed: {e}")
                offset += len(chunk)
                continue

            for span in spans:
                label = span.get("entity_group") or span.get("entity") or ""
                for prefix in ("B-", "I-", "E-", "S-"):
                    if label.startswith(prefix):
                        label = label[len(prefix):]
                        break
                score = float(span.get("score", 1.0))
                if score < self.min_score:
                    continue
                start = int(span.get("start", 0)) + offset
                end = int(span.get("end", 0)) + offset
                if end <= start:
                    continue
                entity_text = text[start:end].strip()
                if len(entity_text) < 2:
                    continue
                raw_spans.append((entity_text, label, start))
            offset += len(chunk)

        # 1. 复姓粘合：position=<复姓> + 紧邻 name → 合并成 person
        merged = self._merge_compound_surname(raw_spans, text)

        # 2. 标签映射 + 类型过滤
        results: List[Tuple[str, str, int]] = []
        for t, raw_label, p in merged:
            if raw_label == "position" and not self.keep_position:
                continue
            mapped = LABEL_MAP.get(raw_label)
            if mapped is None:
                if raw_label == "position" and self.keep_position:
                    mapped = "position"
                else:
                    continue

            if only_types and mapped not in only_types:
                continue
            if exclude_types and mapped in exclude_types:
                continue

            # name/person 做一次基本过滤：去掉以停用词结尾的碎片
            if mapped == "person" and t[-1] in "的了过是为与和或及在":
                continue

            # 丢弃纯英文/拉丁命中 —— CLUENER 是中文模型，对英文会乱报
            # （实际测试：把 "company"/"Delaware" 这类普通词当成公司）
            has_cjk = any("一" <= c <= "鿿" for c in t)
            if not has_cjk:
                continue

            # government/court 过滤：泛指名（第二审人民法院/原审人民法院等）不是具体机构
            if mapped in ("government", "court", "institution"):
                generic_gov_court = {
                    "人民法院", "第一审人民法院", "第二审人民法院", "第三审人民法院",
                    "原审人民法院", "再审人民法院", "审判人民法院",
                    "人民检察院", "本院", "法院", "检察院", "原审", "一审", "二审", "再审",
                }
                if t in generic_gov_court:
                    continue
                # "第X条/款/项/审XX" 开头的法规引用
                import re as _re
                if _re.match(r'第[一二三四五六七八九十百千\d]+[条款项审]', t):
                    continue

            results.append((t, mapped, p))

        return self._dedupe(results)

    @staticmethod
    def _merge_compound_surname(
        spans: List[Tuple[str, str, int]], text: str
    ) -> List[Tuple[str, str, int]]:
        """合并 position=<复姓> + 紧邻 name 为 name"""
        if not spans:
            return spans
        spans = sorted(spans, key=lambda x: x[2])
        out: List[Tuple[str, str, int]] = []
        i = 0
        while i < len(spans):
            t, lbl, p = spans[i]
            if (
                lbl == "position"
                and t in COMPOUND_SURNAMES
                and i + 1 < len(spans)
            ):
                nt, nlbl, np_ = spans[i + 1]
                # 严格相邻：position 的末尾 == name 的开头
                if nlbl == "name" and (p + len(t)) == np_:
                    merged_text = text[p : np_ + len(nt)]
                    out.append((merged_text, "name", p))
                    i += 2
                    continue
            out.append((t, lbl, p))
            i += 1
        return out

    @staticmethod
    def _split_chunks(text: str, max_chars: int) -> List[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        i = 0
        while i < len(text):
            end = min(i + max_chars, len(text))
            if end < len(text):
                for sep in ("\n\n", "\n", "。", "；"):
                    cut = text.rfind(sep, i, end)
                    if cut > i + max_chars // 2:
                        end = cut + len(sep)
                        break
            chunks.append(text[i:end])
            i = end
        return chunks

    @staticmethod
    def _dedupe(items: List[Tuple[str, str, int]]) -> List[Tuple[str, str, int]]:
        seen = set()
        out = []
        for t, ty, p in items:
            key = (t, ty, p)
            if key in seen:
                continue
            seen.add(key)
            out.append((t, ty, p))
        out.sort(key=lambda x: x[2])
        return out


_SHARED: Optional["CNNERDetector"] = None


def get_shared_cn_detector(**kwargs) -> "CNNERDetector":
    global _SHARED
    if _SHARED is None:
        _SHARED = CNNERDetector(**kwargs)
    return _SHARED


def is_cn_llm_enabled_via_env() -> bool:
    return os.environ.get("LEGAL_ANONYMIZER_CN_LLM", "").lower() in ("1", "true", "yes", "on")
