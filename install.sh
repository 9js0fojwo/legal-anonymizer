#!/bin/bash
# 法律文档脱敏工具 - 安装脚本

set -e

echo "========================================"
echo "法律文档脱敏工具 - 安装"
echo "========================================"

# 检测Python版本
echo ""
echo "检查Python版本..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "错误: 未找到Python，请先安装Python 3.7+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2)
echo "  Python版本: $PYTHON_VERSION"

# 创建虚拟环境（可选）
echo ""
read -p "是否创建虚拟环境? (y/n, 默认n): " CREATE_VENV
CREATE_VENV=${CREATE_VENV:-n}

if [ "$CREATE_VENV" = "y" ] || [ "$CREATE_VENV" = "Y" ]; then
    echo "创建虚拟环境..."
    $PYTHON_CMD -m venv .venv
    echo "激活虚拟环境..."
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        source .venv/bin/activate
        PYTHON_CMD=.venv/bin/python
        PIP_CMD=.venv/bin/pip
    else
        echo "Windows请手动激活虚拟环境: .venv\Scripts\activate"
    fi
    echo "虚拟环境已创建"
else
    PIP_CMD=pip
fi

# 升级pip
echo ""
echo "升级pip..."
$PYTHON_CMD -m pip install --upgrade pip

# 安装基础依赖
echo ""
echo "安装基础依赖..."
$PIP_CMD install -r requirements.txt

# 询问是否安装OCR依赖
echo ""
read -p "是否安装OCR支持（用于处理扫描版PDF）? (y/n, 默认n): " INSTALL_OCR
INSTALL_OCR=${INSTALL_OCR:-n}

if [ "$INSTALL_OCR" = "y" ] || [ "$INSTALL_OCR" = "Y" ]; then
    echo "安装OCR依赖..."
    $PIP_CMD install pillow pytesseract

    echo ""
    echo "提示: 您还需要安装Tesseract OCR引擎:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS: brew install tesseract"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "  Ubuntu/Debian: sudo apt install tesseract-ocr"
    else
        echo "  Windows: 下载安装 https://github.com/UB-Mannheim/tesseract/wiki"
    fi
fi

# 运行测试
echo ""
read -p "是否运行测试? (y/n, 默认y): " RUN_TEST
RUN_TEST=${RUN_TEST:-y}

if [ "$RUN_TEST" = "y" ] || [ "$RUN_TEST" = "Y" ]; then
    echo ""
    echo "运行测试..."
    $PYTHON_CMD test.py
fi

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
echo ""
echo "快速开始:"
echo "  查看帮助: $PYTHON_CMD cli.py --help"
echo "  脱敏文件: $PYTHON_CMD cli.py anonymize input.pdf -o output.pdf"
echo "  分析文件: $PYTHON_CMD cli.py analyze input.pdf"
echo "  列出类型: $PYTHON_CMD cli.py list-types"
echo ""
echo "更多示例请查看 examples/ 目录"
echo ""
