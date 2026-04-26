"""
LLM-based PII Detector (OpenAI privacy-filter)
基于 OpenAI privacy-filter（1.5B MoE, 50M active）的 PII 检测器

该模型主要面向英文/拉丁文字，官方说明："Performance may drop on non-English text,
non-Latin scripts." 因此本检测器在本项目中的定位是**补充层**：
  - 覆盖中文规则盲区：英文人名、英文地址、英文机构名、API key / secret、英文 URL
  - 对英文邮箱/电话/日期做交叉验证
  - 中文人名/公司名仍以 EntityDetector 的规则为准

设计要点：
  1. 懒加载：首次调用 detect() 时才加载模型，避免启动变慢
  2. 依赖缺失时优雅降级：transformers/torch 没装就返回空列表并打印提示
  3. 类型映射：把 privacy-filter 的 8 类 PII 映射到项目现有类型体系
  4. 位置对齐：transformers pipeline 返回的 offset 对齐原文字符索引
  5. 过滤短片段：< 2 字符的命中通常是误报
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# OpenAI privacy-filter 的 8 类 → 本项目类型
# 注意：privacy-filter 的 private_person 在中文文本上召回很低，所以我们保留但不
# 依赖它；中文人名主要靠规则层 EntityDetector 兜底。
LABEL_MAP = {
    "account_number": "bank_account",
    "private_address": "full_address",
    "private_email": "email",
    "private_person": "person",
    "private_phone": "phone",
    "private_url": "website",
    "private_date": "date",
    "secret": "secret",  # API key / token，项目里作为新类型
}

DEFAULT_MODEL_ID = "openai/privacy-filter"


class LLMDetector:
    """基于 token-classification LLM 的 PII 检测器（懒加载）"""

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        device: Optional[str] = None,
        min_score: float = 0.5,
        max_chars: int = 8000,
        only_latin_spans: bool = True,
    ):
        """
        Args:
            model_id: HuggingFace 模型 ID
            device: "cpu" | "mps" | "cuda" | None（自动选择）
            min_score: 最低置信度阈值
            max_chars: 单次推理最大字符数；超出会自动分段
            only_latin_spans: True 时丢弃命中中完全不含拉丁字母/数字的片段
                              —— 因为模型对中文召回不稳，容易产出误报。
                              关掉后可观察模型对中文的表现。
        """
        self.model_id = model_id
        self.device = device
        self.min_score = min_score
        self.max_chars = max_chars
        self.only_latin_spans = only_latin_spans

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
            self._load_error = (
                f"缺少依赖：{e.name}。请先安装：\n"
                f"  pip install torch transformers"
            )
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

            logger.info(f"[llm_detector] loading {self.model_id} on {device} ...")
            tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            model = AutoModelForTokenClassification.from_pretrained(self.model_id)
            # HF pipeline 自己处理 BIOES 聚合（aggregation_strategy="simple"）
            self._pipeline = pipeline(
                task="token-classification",
                model=model,
                tokenizer=tokenizer,
                aggregation_strategy="simple",
                device=device,
            )
            logger.info(f"[llm_detector] model loaded on {device}")
            return True
        except Exception as e:
            self._load_error = f"模型加载失败: {e}"
            logger.exception(self._load_error)
            return False

    @property
    def available(self) -> bool:
        """尝试加载并返回是否可用（不抛异常）"""
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
        """
        检测 PII，返回 [(entity_text, mapped_type, start_pos), ...]
        与 PatternDetector.detect() 签名对齐。
        """
        if not text or not self._ensure_loaded():
            return []

        # 分段推理，避免超长文本 OOM
        results: List[Tuple[str, str, int]] = []
        offset = 0
        for chunk in self._split_chunks(text, self.max_chars):
            try:
                spans = self._pipeline(chunk)
            except Exception as e:
                logger.warning(f"[llm_detector] inference failed on chunk: {e}")
                offset += len(chunk)
                continue

            for span in spans:
                label = span.get("entity_group") or span.get("entity") or ""
                # privacy-filter 模型 label 可能带 B-/I-/E-/S- 前缀
                for prefix in ("B-", "I-", "E-", "S-"):
                    if label.startswith(prefix):
                        label = label[len(prefix):]
                        break
                mapped = LABEL_MAP.get(label)
                if mapped is None:
                    continue

                score = float(span.get("score", 1.0))
                if score < self.min_score:
                    continue

                # pipeline 返回的 start/end 是 chunk 内的偏移
                start = int(span.get("start", 0)) + offset
                end = int(span.get("end", 0)) + offset
                if end <= start:
                    continue

                # 用原文索引取实际片段（比模型重建的字符串更可靠）
                entity_text = text[start:end]
                # 去掉前后的空白和常见标点（不影响中间内容）
                l_strip = len(entity_text) - len(entity_text.lstrip(" \t\n,，。；;"))
                r_strip = len(entity_text) - len(entity_text.rstrip(" \t\n,，。；;"))
                if l_strip:
                    start += l_strip
                end -= r_strip
                entity_text = text[start:end]
                if len(entity_text) < 2:
                    continue

                # 过滤全中文片段（模型中文召回不稳，容易错切）
                if self.only_latin_spans and mapped == "person":
                    if not any(c.isascii() and c.isalnum() for c in entity_text):
                        continue

                # 类型过滤
                if only_types and mapped not in only_types:
                    continue
                if exclude_types and mapped in exclude_types:
                    continue

                # 修正 start 到 entity_text 在原文中实际出现的位置
                real_start = text.find(entity_text, start)
                if real_start == -1:
                    real_start = start
                results.append((entity_text, mapped, real_start))

            offset += len(chunk)

        merged = self._merge_adjacent(results, text)
        merged = self._fix_url_tail(merged, text)
        merged = self._extend_boundaries(merged, text)
        return self._dedupe(merged)

    @staticmethod
    def _extend_boundaries(
        items: List[Tuple[str, str, int]], text: str
    ) -> List[Tuple[str, str, int]]:
        """
        修补模型边界丢字符的问题：
          - phone: 尾部向后扩展到非 [数字/空格/-] 字符
          - secret: 尾部向后扩展到非 [A-Za-z0-9_\\-] 字符
          - account_number / bank_account: 同 secret
          - website: 尾部扩展到空白/中文/右括号前
        前向扩展不做（容易吞进前置关键词）。
        """
        import string

        CHARSETS = {
            "phone": set(string.digits + " -"),
            "secret": set(string.ascii_letters + string.digits + "_-."),
            "bank_account": set(string.digits + " -"),
            "website": set(string.ascii_letters + string.digits + ":/.-?=&%#_~+@"),
        }
        out = []
        for t, ty, p in items:
            cs = CHARSETS.get(ty)
            if cs is None:
                out.append((t, ty, p))
                continue
            end = p + len(t)
            new_end = end
            while new_end < len(text) and text[new_end] in cs:
                new_end += 1
            if new_end > end:
                out.append((text[p:new_end].rstrip(" -"), ty, p))
            else:
                out.append((t, ty, p))
        return out

    @staticmethod
    def _fix_url_tail(
        items: List[Tuple[str, str, int]], text: str
    ) -> List[Tuple[str, str, int]]:
        """
        修复：website 后紧跟 secret 且 secret 以 :// 或 / 开头时，合并为 website。
        模型经常把 'https' 标为 website，把后半段 '://host/path' 标为 secret。
        """
        if not items:
            return items
        items = sorted(items, key=lambda x: x[2])
        out: List[Tuple[str, str, int]] = []
        i = 0
        while i < len(items):
            t, ty, p = items[i]
            if ty == "website" and i + 1 < len(items):
                nt, nty, np_ = items[i + 1]
                end = p + len(t)
                gap = text[end:np_]
                if (
                    nty == "secret"
                    and 0 <= (np_ - end) <= 1
                    and (nt.startswith("://") or nt.startswith("/"))
                    and len(gap) == 0
                ):
                    new_text = text[p : np_ + len(nt)]
                    out.append((new_text, "website", p))
                    i += 2
                    continue
            out.append((t, ty, p))
            i += 1
        return out

    @staticmethod
    def _merge_adjacent(
        items: List[Tuple[str, str, int]], text: str, max_gap: int = 3
    ) -> List[Tuple[str, str, int]]:
        """
        合并相邻的同类型片段（subword 碎片化的修补）。
        e.g. ('zhangsan@example', email, 100) + ('.com', email, 116) -> 'zhangsan@example.com'
        只合并间隔 <= max_gap 且中间仅含标点/空格的片段。
        """
        if not items:
            return items
        items = sorted(items, key=lambda x: (x[2], -len(x[0])))
        merged: List[Tuple[str, str, int]] = []
        for t, ty, p in items:
            end = p + len(t)
            if merged:
                lt, lty, lp = merged[-1]
                lend = lp + len(lt)
                gap_text = text[lend:p]
                if ty == lty and 0 <= (p - lend) <= max_gap and (
                    gap_text == ""
                    or all(c in " \t.,-:/@· " for c in gap_text)
                ):
                    new_text = text[lp:end]
                    merged[-1] = (new_text, lty, lp)
                    continue
            merged.append((t, ty, p))
        return merged

    @staticmethod
    def _split_chunks(text: str, max_chars: int) -> List[str]:
        if len(text) <= max_chars:
            return [text]
        chunks = []
        i = 0
        while i < len(text):
            end = min(i + max_chars, len(text))
            # 尽量在换行/句号处切
            if end < len(text):
                for sep in ("\n\n", "\n", "。", ". "):
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


def is_llm_enabled_via_env() -> bool:
    """读取 LEGAL_ANONYMIZER_LLM 环境变量，便于脚本/启动器统一开关"""
    return os.environ.get("LEGAL_ANONYMIZER_LLM", "").lower() in ("1", "true", "yes", "on")


_SHARED: Optional["LLMDetector"] = None


def get_shared_detector(**kwargs) -> "LLMDetector":
    """
    进程级共享 LLMDetector 单例。
    Web UI 等场景每次请求都会新建 LegalAnonymizer，用这个函数避免重复加载 1.5GB 模型。
    """
    global _SHARED
    if _SHARED is None:
        _SHARED = LLMDetector(**kwargs)
    return _SHARED
