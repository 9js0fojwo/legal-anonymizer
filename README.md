# 法律文档脱敏工具 · Legal Anonymizer

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()
[![Offline](https://img.shields.io/badge/Network-100%25%20Offline-success.svg)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-orange.svg)]()

> 一款**完全本地运行**、**不联网不上传**的法律文书敏感信息脱敏工具。  
> 律师、法务、合规人员的本地脱敏助手。  
> by **黄灵宝同学**

中文法律文书 100% 本地脱敏 · 支持中英混合涉外文件 · 一键输出 MD/DOCX/PDF 三格式 · 保留原文档字体排版盖章

---

> ⚠️ **使用前请阅读 [DISCLAIMER.md（免责声明）](DISCLAIMER.md)**：本工具是辅助性脱敏工具，**不能替代人工复核**。最终脱敏结果由使用者负责确认。

---

## 📑 目录

- [功能亮点](#-功能亮点)
- [快速开始（普通用户）](#-快速开始普通用户)
- [开发者用法（CLI/API）](#-开发者用法-cliapi)
- [三层检测架构](#-三层检测架构)
- [实测效果](#-实测效果)
- [深入文档](#-深入文档)
- [免责声明](#-免责声明)

---

## ✨ 功能亮点

- 🔒 **100% 本地运行**：所有处理在你电脑上完成，不调用任何外部 API，不上传任何数据
- 🎯 **三层智能检测**：正则规则 + 中文 NER（CLUENER）+ 英文 LLM（OpenAI privacy-filter，可选）
- 📑 **30+ 种敏感信息**：人名（含复姓）、公司、身份证、手机、银行卡、案号、地址、金额、邮箱、API token 等
- 📋 **多格式同时输出**：一次脱敏生成 **MD + DOCX + PDF** 三份文件
- 🎨 **原格式保留**：DOCX→DOCX 完整保留字体/排版；PDF→PDF 原地脱敏保留布局/盖章
- 🔍 **双 OCR 引擎**：默认 RapidOCR（快、轻量），复杂排版可切 PaddleOCR
- 🇨🇳 **中文友好**：复姓识别（欧阳/万俟/诸葛/皇甫/司马/上官）、PDF 排版换行自动合并
- 🌐 **网页 + 命令行**：拖拽上传可视化操作，或 CLI 批处理，皆可

---

## 🚀 快速开始（普通用户）

### 推荐流程：下载 zip → 双击 .command → 浏览器自动打开

1. 在右侧 **[Releases](../../releases)** 页下载最新版 zip
2. 解压到任意位置（如桌面）
3. 双击文件夹中的：
   - **macOS**：`【请双击我！】启动脱敏工具.command`
   - **Windows**：`启动脱敏工具.bat`
4. **首次启动**会自动完成：
   - 安装 Python 依赖（约 800MB，3-5 分钟）
   - 询问"**是否经常处理英文文书**？"（n = 仅中文模式，y = 多装 2.6GB 英文模型）
   - **自动下载中文 NER 模型**（400MB，1-3 分钟，国内走 hf-mirror.com 镜像）
   - 选 y 时再下载英文模型（2.6GB）
5. 浏览器自动打开 `http://127.0.0.1:8080`，开始用
6. **以后再启动会直接跳到第 5 步**（依赖和模型都已缓存）

> 详细图文步骤参见仓库根目录的 `首次使用指南.pdf`

---

## 快速启动（推荐）

### macOS 用户

1. 解压 `legal-anonymizer.zip` 到任意位置
2. 双击文件夹中的 **`【请双击我！】启动脱敏工具.command`**
3. 首次运行会自动安装依赖，之后会自动打开浏览器

> **首次打开遇到安全提示？** 这是 macOS 的正常安全机制，按以下步骤解除：
>
> 1. 弹出「Apple 无法验证……是否包含恶意软件」时，点 **完成**（不要点「移到废纸篓」）
> 2. 打开 **系统设置** → **隐私与安全性**
> 3. 向下滚动到「安全性」区域，找到被阻止的提示
> 4. 点击 **仍要打开** → 输入密码确认
> 5. 再次双击该文件，点弹窗中的 **打开**
> 6. 之后再双击就不会再弹提示了
>
> 详细图文指引请参阅 **`macOS安全设置指引.md`**

### Windows 用户

1. 解压后双击 **`启动脱敏工具.bat`**

---

## 手动安装（如果快速启动不生效）

### 第一步：确认电脑有 Python

**macOS：** 按 `Command + 空格`，搜索 `终端`（或 `Terminal`），打开后输入：

```
python3 --version
```

**Windows：** 按 `Win + R`，输入 `cmd` 回车，然后输入：

```
python --version
```

如果显示 `Python 3.x.x`（比如 `Python 3.11.3`），说明已安装，跳到第二步。

如果提示"未找到命令"或"不是内部命令"，需要先安装 Python：
- 打开 https://www.python.org/downloads/
- 下载最新版本，运行安装程序
- **Windows 用户注意：安装时必须勾选 `Add Python to PATH`（界面最下方的复选框）**
- 安装完成后关闭并重新打开终端，再次输入 `python3 --version`（macOS）或 `python --version`（Windows）确认

### 第二步：解压并进入项目文件夹

将下载的 `legal-anonymizer.zip` 解压到任意位置（比如桌面），然后在终端中进入该文件夹：

**macOS：**
```
cd ~/Desktop/legal-anonymizer
```

**Windows：**
```
cd %USERPROFILE%\Desktop\legal-anonymizer
```

> 提示：也可以在终端中输入 `cd `（注意 cd 后面有一个空格），然后把文件夹从 Finder/资源管理器 拖拽到终端窗口，会自动填入路径，再按回车。

### 第三步：安装依赖（仅首次需要）

**macOS：**
```
pip3 install -r requirements.txt
```

**Windows：**
```
pip install -r requirements.txt
```

如果提示 `pip: command not found`，尝试：
```
python3 -m pip install -r requirements.txt
```
或（Windows）：
```
python -m pip install -r requirements.txt
```

等待安装完成，看到没有红色报错即可。

### 第四步：启动

**macOS：**
```
python3 web_app.py
```

**Windows：**
```
python web_app.py
```

启动后会自动打开浏览器。如果没有自动打开，手动在浏览器地址栏输入终端中显示的地址（通常是 `http://127.0.0.1:8080`）。

看到网页界面即可开始使用。**不要关闭终端窗口**，关闭终端 = 停止服务。

---

## 使用方法

1. 在网页中上传文件（拖拽或点击选择），支持 PDF、DOCX、TXT
2. 点击"开始分析"，工具会自动识别敏感信息
3. 检查识别结果，可以手动添加或取消勾选
4. 点击"执行脱敏"，下载脱敏后的文件

**扫描版 PDF**：工具会自动检测并提示启用 OCR。如需 OCR 支持，额外安装：

macOS：
```
pip3 install pillow pytesseract
brew install tesseract tesseract-lang
```

Windows：
```
pip install pillow pytesseract
```
然后从 https://github.com/UB-Mannheim/tesseract/wiki 下载安装 Tesseract，安装时勾选中文语言包。

---

## 常见问题

### Q: `pip install` 报错 `Permission denied`
A: 在命令前加 `--user`：
```
pip3 install --user -r requirements.txt
```

### Q: 启动后浏览器没有自动打开
A: 手动打开浏览器，输入终端中显示的地址，通常是 `http://127.0.0.1:8080`

### Q: 启动报错 `Address already in use`
A: 端口被占用，程序会自动尝试 8080-8099 端口。如果还是失败，关掉其他占用端口的程序后重试。

### Q: Windows 上 `python` 命令打开了 Microsoft Store
A: 在系统设置中关闭"应用执行别名"中的 Python，或直接使用完整路径运行。

### Q: macOS 提示 `command not found: python3`
A: 需要安装 Python，见第一步。或者尝试安装 Xcode 命令行工具：
```
xcode-select --install
```

### Q: 报错 `ModuleNotFoundError: No module named 'flask'`
A: 依赖没安装成功，重新执行第三步。确保 pip 和 python 是同一个版本：
```
python3 -m pip install -r requirements.txt
```

### Q: DOCX 输出格式和原文不一样
A: 输入 DOCX → 输出 DOCX 时会自动保留原始格式（字体、字号、排版）。如果输入是 PDF，输出的 DOCX 是重新生成的。

---

## 命令行用法（高级）

不需要网页界面也可以直接用命令行：

```bash
# 脱敏 Word 文档
python3 cli.py anonymize input.docx -o output.docx

# 脱敏 PDF
python3 cli.py anonymize input.pdf -o output.pdf

# 扫描版 PDF 启用 OCR
python3 cli.py anonymize scan.pdf -o output.docx --ocr

# 只分析不脱敏
python3 cli.py analyze input.docx

# 查看支持的所有类型
python3 cli.py list-types
```

---

## 可选：启用 LLM 补充检测（三层检测架构）

本工具原生用**正则 + 中文规则**，但复杂中文法律文书里规则层会漏**人名/公司/地址**（特别是没有"原告/被告"关键词的、含复姓的、边界复杂的）。可以叠加两个 LLM 做补充：

| 层 | 模型 | 大小 | 主要补盲 |
|---|---|---|---|
| CN NER | `uer/roberta-base-finetuned-cluener2020-chinese` | ~400 MB | **中文人名（含复姓）、中文公司、中文地址** |
| OpenAI | `openai/privacy-filter`（1.5B MoE） | ~2.6 GB | **英文人名、英文地址、国际电话、API token** |

**两层都按需开启，互不冲突**。中文文书只开 CN NER 够用；中英混合文书两个都开。

### 一次性安装

```bash
pip3 install torch transformers "httpx[socks]"
```

首次运行会把两个模型分别下载到 HuggingFace 缓存目录（`~/.cache/huggingface`），之后离线推理。

### 使用方式

```bash
# 只开中文 NER（推荐，补规则漏掉的中文人名/公司/地址）
python3 cli.py anonymize input.docx -o output.docx --cn-llm

# 只开 OpenAI（文档以英文为主时）
python3 cli.py anonymize input.docx -o output.docx --llm

# 全开（中英混合最强模式）
python3 cli.py anonymize input.docx -o output.docx --cn-llm --llm
```

**Web UI 启用**：环境变量 `LEGAL_ANONYMIZER_CN_LLM=1` 和 `LEGAL_ANONYMIZER_LLM=1`：

```bash
LEGAL_ANONYMIZER_CN_LLM=1 python3 web_app.py
```

### 实测收益

**硬中文样本**（借款合同判决书，规则漏得很严重）：

| 项 | 纯规则 | +CN NER |
|---|---|---|
| 中文人名漏检 | 10+ 处（含 6 种复姓示例：欧阳/万俟/诸葛/皇甫/司马/上官） | ✅ 全部抓到 |
| 复姓识别 | 错切（如"司马XX"被切成"司"+"马XX"） | ✅ 正确合并 |
| 错判纠正 | "某实业"被判人名 | ✅ 纠正为公司 |
| 完整地址 | 只抓"128弄"和"56号楼"碎片 | ✅ 完整地址 |
| "法院调取银行"误报 | 被当作银行名 | ✅ 已修 |

**中英混合样本**（涉外民事起诉状）：

| 项 | 纯规则 | +CN NER +OpenAI |
|---|---|---|
| 英文人名 | 漏 | ✅ John Smith / Jennifer Chen |
| 英文地址 | 漏 | ✅ 2025 Mission Street, San Francisco, CA 94110, USA |
| 英文公司 | 漏（含逗号时） | ✅ Acme Legal Services, Inc. |
| 国际电话 | 漏 | ✅ +1 / +44 |
| API token | 漏 | ✅ sk-proj-... |

### 三层仲裁机制

1. **规则优先**：结构化数据（身份证/银行卡/邮箱等）一律由正则处理
2. **CN NER 可纠错**：
   - 规则把公司判成人名 → CN NER 纠正为公司
   - 规则边界错切（复姓人名只识别后半段）→ CN NER 完整 span 胜出
   - 规则只抓地址碎片 → CN NER 的完整地址胜出
3. **同名全文一致性**：CN NER 对部分语境漏检同名人名时，系统自动扩展到全文所有位置
4. **OpenAI 仅补空位**：只覆盖前两层都没抓到的位置，不与中文冲突
5. **英文段落不跑 CN NER**：CJK 过滤避免把 "company"/"Delaware" 等英文普通词误报

### 限制

- OpenAI 模型英文优先，中文召回低，靠 CN NER 兜底
- CN NER 训练于通用新闻语料，极少数生僻法律术语可能误报（如把"律师"当职位）
- 全开后首次启动需加载两个模型（约 15-20 秒），之后单例复用

---

## 🔒 隐私安全

- 所有处理完全在本地进行，不调用任何外部 API
- 不上传任何数据到云端
- 代码完全开源可审计：`grep -r "requests|urllib|http" *.py` 应返回空结果
- 启用 LLM 后模型一次性下载到本地（`~/.cache/huggingface/`），推理**全程离线**
- 可设置 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=1` 彻底断网

---

## 📚 深入文档

- [`docs/项目报告.md`](docs/项目报告.md) —— 详细技术报告（2 万字，开发历程、架构、实测）
- [`docs/简明版报告.md`](docs/简明版报告.md) —— 公众号友好版（5000 字，给同行/读者）
- [`首次使用指南.pdf`](首次使用指南.pdf) —— 13 章节图文使用手册
- [`DISCLAIMER.md`](DISCLAIMER.md) —— 免责声明（**使用前必读**）

---

## ⚖️ 免责声明

本工具是**辅助性脱敏工具**，**不能替代人工复核**。使用本工具脱敏的法律文书在交付前，**必须由使用者亲自复核确认**。开发者不对任何因使用本工具产生的信息泄露、合规问题或职业责任承担任何责任。

完整免责条款见 [DISCLAIMER.md](DISCLAIMER.md)。

---

## 🤝 贡献

欢迎 issue 和 PR：

- 发现敏感信息漏检 → 提 issue 附带（脱敏过的）样例文本
- 发现误报 → 同上
- 想加新检测类型 → 提 issue 讨论后再 PR
- 文档改进 → 直接 PR

---

## 📜 协议

本项目采用 **Apache License 2.0** —— 见 [LICENSE](LICENSE)。

第三方依赖各自遵循其开源协议（OpenAI Privacy Filter / RapidOCR / PaddleOCR / PyMuPDF 等）。

---

## 💝 致谢

感谢以下开源项目让本工具成为可能：
- [OpenAI Privacy Filter](https://huggingface.co/openai/privacy-filter)
- [CLUENER 2020](https://huggingface.co/uer/roberta-base-finetuned-cluener2020-chinese)
- [RapidOCR](https://github.com/RapidAI/RapidOCR)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

---

*Made with ❤️ by 黄灵宝同学（Rainbow Wong）*
