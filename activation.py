#!/usr/bin/env python3
"""
激活码验证模块
用户侧：验证激活码是否有效，管理激活状态
"""

import os
import json
import hashlib
import hmac
from pathlib import Path
from datetime import datetime

# ⚠️ 不要改这个密钥。改了之后所有已发出的激活码全部失效。
SECRET_KEY = b"legal-anonymizer-2026-rainbow-secret-key-v1"

# 激活状态文件
ACTIVATION_FILE = Path(__file__).parent / ".activation.json"

# 高级功能列表
PREMIUM_FEATURES = [
    "cn_ner",      # 中文 NER 检测（复姓、公司名等）
    "openai_llm",  # OpenAI 隐私过滤器（英文检测）
    "ocr",         # OCR 扫描件处理
    "ollama",      # 本地 Ollama 大模型
    "batch",       # 批量处理（CLI）
    "custom_dict", # 自定义词典
]


def generate_code(prefix: str) -> str:
    """
    生成激活码（仅供卖家使用）
    格式: LEGAL-XXXX-XXXX-XXXX
    """
    # 用 HMAC-SHA256 签名前缀
    signature = hmac.new(SECRET_KEY, prefix.encode(), hashlib.sha256).hexdigest()[:12]
    # 格式化为 4-4-4
    code_body = f"{signature[:4]}-{signature[4:8]}-{signature[8:12]}"
    # 前缀 + 签名
    return f"{prefix}-{code_body}".upper()


def validate_code(code: str) -> bool:
    """
    验证激活码
    返回 True 表示有效
    """
    if not code:
        return False

    code = code.strip().upper()
    parts = code.split("-")

    # 格式: LEGAL-XXXX-XXXX-XXXX（共 4 段）
    if len(parts) != 4:
        return False

    prefix = parts[0]
    # 前缀必须以 LEGAL 或 LAWMASK 开头
    if not (prefix.startswith("LEGAL") or prefix.startswith("LAWMASK")):
        return False

    # 后三段是签名
    signature_body = f"{parts[1]}-{parts[2]}-{parts[3]}"
    expected_body = hmac.new(SECRET_KEY, prefix.encode(), hashlib.sha256).hexdigest()[:12]
    expected_formatted = f"{expected_body[:4]}-{expected_body[4:8]}-{expected_body[8:12]}"

    return signature_body.upper() == expected_formatted.upper()


def get_activation_status() -> dict:
    """获取当前激活状态"""
    if ACTIVATION_FILE.exists():
        try:
            with open(ACTIVATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 验证存储的激活码仍然有效
            if validate_code(data.get("code", "")):
                return {
                    "activated": True,
                    "code": data["code"][:8] + "****",
                    "activated_at": data.get("activated_at", ""),
                    "features": PREMIUM_FEATURES,
                }
        except Exception:
            pass

    return {
        "activated": False,
        "code": None,
        "activated_at": None,
        "features": [],
    }


def activate(code: str) -> bool:
    """
    激活软件
    返回 True 表示激活成功
    """
    if not validate_code(code):
        return False

    data = {
        "code": code,
        "activated_at": datetime.now().isoformat(),
        "version": "2.0",
    }

    with open(ACTIVATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return True


def is_premium_feature_available(feature: str) -> bool:
    """检查某个高级功能是否可用"""
    status = get_activation_status()
    if not status["activated"]:
        return False
    return feature in PREMIUM_FEATURES


def is_activated() -> bool:
    """简化的激活检查"""
    return get_activation_status()["activated"]
