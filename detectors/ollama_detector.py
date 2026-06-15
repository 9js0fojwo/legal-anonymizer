"""
OllamaDetector — 本地大模型 PII 检测层

通过 Ollama 的 OpenAI 兼容接口（/v1/chat/completions）调用本地部署的大模型，
让模型以 JSON 格式返回文中出现的敏感实体，再将实体文本映射回原文位置。

定位：第 5 层补充检测，只覆盖前四层（正则 + 规则 + CN NER + OpenAI privacy-filter）
未覆盖的位置。适合处理：
  - 上下文高度依赖的人名识别（如"甲方的法定代表人"后紧跟名字）
  - 规则难以枚举的特殊机构名、地名缩写
  - 中英混合复杂语境下的综合推理

配置方式：
  环境变量：
    LEGAL_ANONYMIZER_OLLAMA=1            启用本层（默认关闭）
    LEGAL_ANONYMIZER_OLLAMA_URL=http://host:11434   Ollama 服务地址（默认 localhost:11434）
    LEGAL_ANONYMIZER_OLLAMA_MODEL=qwen2.5:7b        模型名（默认 qwen2.5:7b）

  CLI 参数（见 cli.py）：
    --ollama                启用
    --ollama-url URL        服务地址
    --ollama-model MODEL    模型名

注意：
  - Gemma 系列经由 /v1 接口默认会启动思考（reasoning），导致正文为空。
    本模块对 gemma 模型自动添加 extra_body={"reasoning_effort": "none"} 绕过此问题。
  - 本层使用生成式 LLM（不是 token classifier），通过实体文本字符串反查位置，
    不会因"输出位置"错误而影响脱敏正确性（最差结果是不命中，而非误报位置）。
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
import urllib.error
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# 本层识别的类型 → 项目内部类型
OLLAMA_TYPE_MAP = {
    "person":       "person",
    "company":      "company",
    "law_firm":     "law_firm",
    "institution":  "institution",
    "government":   "government",
    "court":        "court",
    "full_address": "full_address",
    "bank_account": "bank_account",
    "case_number":  "case_number",
    "phone":        "phone",
    "email":        "email",
    "id_card":      "id_card",
    "secret":       "secret",
    "website":      "website",
}

_SYSTEM_PROMPT = """\
You are a PII extractor for Chinese legal documents. Your task is to find \
personal and sensitive information in the given text.

Return ONLY a valid JSON object with this exact structure:
{"entities": [{"text": "...", "type": "..."}]}

Valid types:
  person        — personal names (人名)
  company       — company / enterprise names (公司名)
  law_firm      — law firm names (律师事务所)
  institution   — non-profit organizations, schools, hospitals (机构)
  government    — government agencies (政府部门)
  court         — court names (法院)
  full_address  — complete street / location addresses (地址)
  bank_account  — bank account numbers (银行账号)
  case_number   — legal case numbers (案号)
  phone         — phone or fax numbers (电话/传真)
  email         — email addresses (邮箱)
  id_card       — national ID / passport numbers (身份证/护照)
  secret        — API keys, tokens, passwords (密钥/密码)
  website       — URLs and domain names (网址)

Rules:
1. "text" must be an EXACT substring copied verbatim from the document.
2. Skip entities that are clearly already in structured formats captured \
by regex (e.g., pure 18-digit numbers, phone patterns). Focus on \
context-dependent names, addresses, and compound identifiers.
3. Do not invent, paraphrase, or expand entities.
4. If nothing is found, return {"entities": []}.
5. Output only the JSON object — no markdown fences, no explanation.
"""


class OllamaDetector:
    """本地 Ollama 大模型 PII 检测器（第 5 补充层）"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        timeout: int = 60,
        max_chars: int = 3000,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_chars = max_chars
        self._available: Optional[bool] = None

    # ───────────────── 可用性探测 ─────────────────

    def _probe(self) -> bool:
        """向 Ollama 发一次 /api/tags 请求确认服务可达"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
            return True
        except Exception as e:
            logger.warning(f"[ollama] 无法连接 {self.base_url}: {e}")
            return False

    @property
    def available(self) -> bool:
        if self._available is None:
            self._available = self._probe()
        return self._available

    # ───────────────── 检测主入口 ─────────────────

    def detect(
        self,
        text: str,
        only_types: Optional[List[str]] = None,
        exclude_types: Optional[List[str]] = None,
    ) -> List[Tuple[str, str, int]]:
        """
        检测 PII，返回 [(entity_text, mapped_type, start_pos), ...]
        与其他 Detector.detect() 签名对齐。
        """
        if not text or not self.available:
            return []

        results: List[Tuple[str, str, int]] = []
        for chunk_text, chunk_offset in self._split_chunks(text, self.max_chars):
            raw = self._call_model(chunk_text)
            if not raw:
                continue
            for entity_text, mapped_type in self._parse_response(raw):
                if only_types and mapped_type not in only_types:
                    continue
                if exclude_types and mapped_type in exclude_types:
                    continue
                # 在原文中查找该实体的所有出现位置
                idx = 0
                while True:
                    pos = text.find(entity_text, idx)
                    if pos == -1:
                        break
                    results.append((entity_text, mapped_type, pos))
                    idx = pos + 1

        return self._dedupe(results)

    # ───────────────── 模型调用 ─────────────────

    def _call_model(self, text_chunk: str) -> Optional[str]:
        """调用 Ollama /v1/chat/completions，返回模型输出文本"""
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Document:\n{text_chunk}"},
            ],
            "temperature": 0,
            "stream": False,
        }

        # Gemma 系列通过 /v1 默认会开启思考（reasoning），导致 content 为空
        # 通过 extra_body 传入 reasoning_effort=none 关闭
        if "gemma" in self.model.lower():
            payload["extra_body"] = {"reasoning_effort": "none"}

        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            return content or None
        except urllib.error.URLError as e:
            logger.warning(f"[ollama] 请求失败: {e}")
            self._available = False  # 标记不可用，后续跳过
            return None
        except Exception as e:
            logger.warning(f"[ollama] 意外错误: {e}")
            return None

    # ───────────────── 结果解析 ─────────────────

    def _parse_response(self, content: str) -> List[Tuple[str, str]]:
        """
        解析模型返回的 JSON，返回 [(entity_text, mapped_type), ...]。
        容错：处理 markdown 代码块、不完整 JSON、额外说明文字等。
        """
        # 去掉 markdown 代码块包裹
        content = re.sub(r"```(?:json)?\s*", "", content).strip()
        # 尝试提取第一个 {...} 块
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return []
        try:
            obj = json.loads(match.group())
        except json.JSONDecodeError:
            logger.debug(f"[ollama] JSON 解析失败，原始输出: {content[:200]}")
            return []

        entities = obj.get("entities", [])
        if not isinstance(entities, list):
            return []

        results = []
        for item in entities:
            if not isinstance(item, dict):
                continue
            raw_text = item.get("text", "").strip()
            raw_type = item.get("type", "").strip().lower()
            if not raw_text or not raw_type:
                continue
            mapped = OLLAMA_TYPE_MAP.get(raw_type)
            if mapped is None:
                continue
            if len(raw_text) < 2:
                continue
            results.append((raw_text, mapped))
        return results

    # ───────────────── 工具方法 ─────────────────

    @staticmethod
    def _split_chunks(text: str, max_chars: int) -> List[Tuple[str, int]]:
        """按 max_chars 切块，尽量在段落/句号处断开，返回 [(chunk_text, offset)]"""
        if len(text) <= max_chars:
            return [(text, 0)]
        chunks = []
        i = 0
        while i < len(text):
            end = min(i + max_chars, len(text))
            if end < len(text):
                for sep in ("\n\n", "\n", "。", ". "):
                    cut = text.rfind(sep, i, end)
                    if cut > i + max_chars // 2:
                        end = cut + len(sep)
                        break
            chunks.append((text[i:end], i))
            i = end
        return chunks

    @staticmethod
    def _dedupe(items: List[Tuple[str, str, int]]) -> List[Tuple[str, str, int]]:
        seen = set()
        out = []
        for t, ty, p in items:
            key = (t, ty, p)
            if key not in seen:
                seen.add(key)
                out.append((t, ty, p))
        out.sort(key=lambda x: x[2])
        return out


# ───────────────── 进程级单例 ─────────────────

_SHARED: Optional[OllamaDetector] = None


def get_shared_ollama_detector(**kwargs) -> OllamaDetector:
    global _SHARED
    if _SHARED is None:
        _SHARED = OllamaDetector(**kwargs)
    return _SHARED


def is_ollama_enabled_via_env() -> bool:
    return os.environ.get("LEGAL_ANONYMIZER_OLLAMA", "").lower() in ("1", "true", "yes", "on")


def ollama_url_from_env() -> str:
    return os.environ.get("LEGAL_ANONYMIZER_OLLAMA_URL", "http://localhost:11434")


def ollama_model_from_env() -> str:
    return os.environ.get("LEGAL_ANONYMIZER_OLLAMA_MODEL", "qwen2.5:7b")
