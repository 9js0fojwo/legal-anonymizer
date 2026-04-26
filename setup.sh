#!/bin/bash
# ============================================================
# 法律文件脱敏工具 - 全自动环境安装
# 用法: bash setup.sh  （或由启动器自动调用，无需手动运行）
# ============================================================
# 安装策略（自动选择）:
#   1. 如果已有 .venv → 跳过，直接结束
#   2. 如果系统有 Python 3.9+ → 用系统 Python 创建 venv
#   3. 如果有 uv → 用 uv 下载 Python 并创建 venv
#   4. 如果有 Homebrew → brew install python@3.11
#   5. 自动安装 uv（无需管理员权限），再用 uv 下载 Python
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
LOG="$SCRIPT_DIR/.setup.log"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $*${NC}"; }
info() { echo -e "${YELLOW}  … $*${NC}"; }
err()  { echo -e "${RED}  ✗ $*${NC}"; }

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   法律文件脱敏工具 - 环境自动安装    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 0. 如果已安装，跳过 ──────────────────────────────────────
if [ -f "$VENV_DIR/bin/python" ]; then
    # 验证关键依赖还在
    if "$VENV_DIR/bin/python" -c "import flask, fitz, docx" 2>/dev/null; then
        ok "环境已就绪，跳过安装"
        echo ""
        exit 0
    fi
    info "环境不完整，重新安装依赖..."
    SKIP_VENV_CREATE=1
fi

# ── 1. 查找可用 Python ────────────────────────────────────────
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" &>/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done

# ── 2. 没有 Python → 自动获取 ───────────────────────────────
if [ -z "$PYTHON" ]; then
    # 尝试 uv（无需管理员权限，自带 Python 下载能力）
    UV_BIN=""
    if command -v uv &>/dev/null; then
        UV_BIN="uv"
    elif [ -f "$HOME/.local/bin/uv" ]; then
        UV_BIN="$HOME/.local/bin/uv"
    fi

    if [ -z "$UV_BIN" ]; then
        info "未找到 Python，正在安装 uv 工具（约 10MB，无需管理员权限）..."
        curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --no-modify-path >> "$LOG" 2>&1
        UV_BIN="$HOME/.local/bin/uv"
        if [ ! -f "$UV_BIN" ]; then
            # macOS ARM path
            UV_BIN="$HOME/.cargo/bin/uv"
        fi
    fi

    if [ -f "$UV_BIN" ]; then
        ok "uv 已就绪"
        info "正在下载 Python 3.11（首次约需 1-2 分钟）..."
        "$UV_BIN" python install 3.11 >> "$LOG" 2>&1
        PYTHON=$("$UV_BIN" python find 3.11 2>/dev/null)
        if [ -z "$PYTHON" ]; then
            # uv managed python 路径
            PYTHON=$(ls "$HOME/.local/share/uv/python/"python3.11*/bin/python3 2>/dev/null | head -1)
        fi
    fi

    # uv 失败 → 尝试 Homebrew
    if [ -z "$PYTHON" ]; then
        if command -v brew &>/dev/null; then
            info "通过 Homebrew 安装 Python 3.11..."
            brew install python@3.11 >> "$LOG" 2>&1
            PYTHON="python3.11"
        fi
    fi

    if [ -z "$PYTHON" ]; then
        err "无法自动安装 Python。请前往 https://www.python.org 下载安装后重试。"
        echo ""
        read -p "  按回车键退出..." 2>/dev/null || true
        exit 1
    fi
fi

ok "Python: $($PYTHON --version 2>&1)"

# ── 3. 创建虚拟环境 ───────────────────────────────────────────
if [ -z "$SKIP_VENV_CREATE" ]; then
    info "创建独立运行环境..."
    "$PYTHON" -m venv "$VENV_DIR" >> "$LOG" 2>&1
fi
PIP="$VENV_DIR/bin/pip"
ok "运行环境就绪"

# ── 4. 安装依赖 ───────────────────────────────────────────────
echo ""
info "安装依赖包（首次约需 3-5 分钟，请耐心等待）..."
"$PIP" install --upgrade pip -q >> "$LOG" 2>&1

REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
if [ -f "$REQUIREMENTS" ]; then
    "$PIP" install -r "$REQUIREMENTS" -q >> "$LOG" 2>&1
else
    "$PIP" install flask pymupdf python-docx pillow reportlab chardet paddleocr -q >> "$LOG" 2>&1
fi
ok "依赖安装完成"

# ── 5. 验证安装 ───────────────────────────────────────────────
echo ""
if "$VENV_DIR/bin/python" -c "import flask, fitz, docx" 2>/dev/null; then
    ok "核心组件验证通过"
else
    err "部分依赖未成功安装，详情见 .setup.log"
fi

# ── 6. 确保目录结构 ───────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/inbox" "$SCRIPT_DIR/output" "$SCRIPT_DIR/uploads"

# ── 完成 ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  ════════════════════════════════════════"
echo -e "    安装完成！正在启动..."
echo -e "  ════════════════════════════════════════${NC}"
echo ""
