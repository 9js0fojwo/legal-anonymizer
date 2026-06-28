#!/usr/bin/env python3
"""
版本更新检查模块
启动时检查 GitHub Releases 是否有新版本
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

# 当前版本（每次发新版改这个数字）
CURRENT_VERSION = "1.0.0"

# GitHub 仓库
GITHUB_REPO = "9js0fojwo/legal-anonymizer"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# 缓存更新检查结果，避免每次启动都请求
CACHE_DIR = Path.home() / ".legal-anonymizer"
CACHE_FILE = CACHE_DIR / "update_check.json"
CACHE_HOURS = 24  # 每 24 小时检查一次


def _parse_version(tag: str) -> tuple:
    """解析 v1.2.3 → (1, 2, 3)"""
    tag = tag.lstrip("v")
    try:
        return tuple(int(x) for x in tag.split(".")[:3])
    except Exception:
        return (0, 0, 0)


def check_update(force: bool = False) -> dict:
    """
    检查是否有新版本

    返回:
        {
            "has_update": True/False,
            "current": "1.0.0",
            "latest": "1.2.0",
            "download_url": "https://...",
            "release_notes": "...",
            "error": None
        }
    """

    result = {
        "has_update": False,
        "current": CURRENT_VERSION,
        "latest": None,
        "download_url": None,
        "release_notes": None,
        "error": None,
    }

    # 检查缓存（非强制模式）
    if not force and CACHE_FILE.exists():
        try:
            cache_age = CACHE_FILE.stat().st_mtime
            import time
            if time.time() - cache_age < CACHE_HOURS * 3600:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("current") == CURRENT_VERSION:
                    return cached
        except Exception:
            pass

    try:
        req = urllib.request.Request(RELEASES_API)
        req.add_header("Accept", "application/vnd.github.v3+json")
        req.add_header("User-Agent", "Legal-Anonymizer-Update-Check")
        # 超时 10 秒
        resp = urllib.request.urlopen(req, timeout=10)
        release = json.loads(resp.read().decode())

        latest_tag = release.get("tag_name", "")
        latest_version = _parse_version(latest_tag)
        current_version = _parse_version(CURRENT_VERSION)

        if latest_version > current_version:
            result["has_update"] = True
            result["latest"] = latest_tag
            result["download_url"] = release.get("html_url", "")
            result["release_notes"] = release.get("body", "")[:500]

    except urllib.error.URLError as e:
        result["error"] = f"网络不可用（离线模式）"
    except Exception as e:
        result["error"] = str(e)

    # 写入缓存
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return result


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    info = check_update(force=force)
    if info["has_update"]:
        print(f"\n🆕 发现新版本: {info['latest']}（当前 {info['current']}）")
        print(f"   下载: {info['download_url']}")
        print(f"   更新内容:\n{info['release_notes']}")
    elif info["error"]:
        print(f"检查更新: {info['error']}")
    else:
        print(f"✅ 已是最新版本 {info['current']}")
