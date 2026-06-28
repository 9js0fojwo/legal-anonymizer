# Legal Anonymizer · 法律文档脱敏工具

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()
[![Offline](https://img.shields.io/badge/Network-100%25%20Offline-success.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-orange.svg)]()

**[English](#english) · [中文](#中文)**

---

<a id="english"></a>

## English

A **100% local, offline** legal document anonymization tool. Double-click to start. No uploads. No cloud. Your files never leave your computer.

---

### 3 Steps

**1. Download → 2. Unzip → 3. Double-click `启动脱敏工具.bat`** (Windows) or `.command` (macOS)

Browser opens at `http://127.0.0.1:8080`. Drag a file in. Done.

> First run auto-installs dependencies (3-5 min). Subsequent launches are instant.

---

### Killer Features

#### 🔧 You Make the Rules

Not a one-size-fits-all blacklist. **You decide.**

- **Force-mask** specific words (client names, project codes) → add to custom dictionary
- **Never-mask** specific words (your firm's name, public info) → add to exclusion list
- The tool follows *your* judgment, not the other way around.

#### 🔄 Redact → Edit → Restore (game changer)

Redact a contract → send to client → client edits → get it back → **restore all redacted content with one click.**

```
Original → Redacted → Client edits → Upload redacted file + mapping →
  → One-click restore → Complete contract. Every name back in place.
```

No manual cross-referencing. No hand-restoration. No mistakes. **No other anonymization tool does this.**

#### ✍️ Manual Review Mode

Machine detection is the first pass. You are the final pass.

- Select text → right-click → redact. Like a highlighter, but for privacy.
- Machine missed something? Mark it manually.
- Machine flagged wrong? One-click undo.
- Sleep better knowing you checked every line yourself.

---

### Free vs Pro

| | Free 🆓 | Pro 💎 |
|------|----------|---------|
| Basic redaction (30+ types) | ✅ | ✅ |
| Manual line-through redaction | ✅ | ✅ |
| **Custom dictionary** (force-mask words) | ❌ | ✅ |
| **Exclusion list** (never-mask words) | ❌ | ✅ |
| **Redact → Edit → Restore** (upload mapping to restore) | ❌ | ✅ |
| **Chinese NER** (compound surnames, companies, addresses) | ❌ | ✅ |
| **OCR** (scanned PDFs) | ❌ | ✅ |
| Triple output (MD+DOCX+PDF) | ❌ | ✅ |
| CLI batch processing | ❌ | ✅ |

> 💡 **Pro — ¥199 one-time, permanent** → WeChat: **law18520071304**. Files stay local. Fully offline even after activation.

---

### More

- Manual install: `pip install -r requirements.txt && python web_app.py`
- CLI: `python cli.py anonymize input.docx -o output.docx`
- [Full docs](docs/项目报告.md) · [User guide PDF](首次使用指南.pdf) · [Disclaimer](DISCLAIMER.md)

### Contributing

- Found a missed detection? Open an issue with a (redacted) sample text
- Found a false positive? Same
- Want a new detection type? Open an issue to discuss before PR
- Documentation improvements? PR directly

### License

Apache License 2.0 — see [LICENSE](LICENSE).

---

*Made with ❤️ by 树肥同学*

---

<a id="中文"></a>

## 中文

> ⚠️ 使用前请阅读 [免责声明](DISCLAIMER.md)：本工具为辅助性工具，**不能替代人工复核**。

一款**100% 本地运行、不联网不上传**的法律文书脱敏工具。双击启动，浏览器操作，文件不出电脑。

---

### 三步搞定

**1. 下载 → 2. 解压 → 3. 双击 `启动脱敏工具.bat`**

浏览器自动打开 `http://127.0.0.1:8080`，拖文件进去，开始脱敏。

> 首次启动自动安装依赖（3-5 分钟），之后秒开。macOS 双击 `.command` 文件。

---

### 三大杀招

#### 🔧 完全按你的规矩来

不是死板的"全部脱敏"——**你说了算**。

- 指定哪些词**必须脱敏**（比如你的客户名字、特定项目代号）→ 加入自定义词典
- 指定哪些词**绝对不脱**（比如律所名称、公开信息）→ 加入排除列表
- 你设定规则，工具执行。不是反过来。

#### 🔄 脱敏→修改→还原（律师才知道这有多值钱）

你把合同脱敏发给客户 → 客户修改 → 你拿到改好的合同 → **把脱敏内容一键还原回去**。

```
原文 → 脱敏 → 发给客户修改 → 客户改好传回 →
  → 上传脱敏文件 + 映射表 → 一键还原 → 完整合同，一个字不差
```

**不用手动对照、不用人工复原、不会漏掉任何一个名字。** 这是市面上所有脱敏工具都没有的功能。

#### ✍️ 手动划线复查

机器跑完，你再过一遍——选中文字、划线标红、一键脱敏。

- 自动检测漏掉的？手动补上
- 机器误判的？一键撤销
- 走完一遍，心里有底

---

### 免费版 vs 专业版

| | 免费版 🆓 | 专业版 💎 |
|------|----------|---------|
| 基础脱敏（30+ 类型） | ✅ | ✅ |
| 手动划线脱敏 | ✅ | ✅ |
| **自定义词典**（指定脱敏词） | ❌ | ✅ |
| **排除列表**（指定不脱敏词） | ❌ | ✅ |
| **脱敏→修改→还原**（上传映射表还原） | ❌ | ✅ |
| **中文 NER 智能检测**（复姓/公司/地址） | ❌ | ✅ |
| **OCR 扫描件识别** | ❌ | ✅ |
| 三格式输出（MD+DOCX+PDF） | ❌ | ✅ |
| 批处理 | ❌ | ✅ |

> 💡 **¥199 永久激活** → 加微信 **law18520071304**。文件不出电脑，激活后完全离线使用。

---

### 更多

- [详细文档](docs/项目报告.md) · [简明版介绍](docs/简明版报告.md) · [使用手册 PDF](首次使用指南.pdf)
- 手动安装：`pip install -r requirements.txt && python web_app.py`
- CLI 批处理：`python cli.py anonymize input.docx -o output.docx`

### 协议

Apache License 2.0 —— 见 [LICENSE](LICENSE)

### 致谢

- [OpenAI Privacy Filter](https://huggingface.co/openai/privacy-filter)
- [CLUENER 2020](https://huggingface.co/uer/roberta-base-finetuned-cluener2020-chinese)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

---

*Made with ❤️ by 树肥同学*
