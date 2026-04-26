@echo off
REM 法律文档脱敏工具 - Windows安装脚本

echo ========================================
echo 法律文档脱敏工具 - 安装
echo ========================================

REM 检查Python
echo.
echo 检查Python版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

python --version

REM 升级pip
echo.
echo 升级pip...
python -m pip install --upgrade pip

REM 安装基础依赖
echo.
echo 安装基础依赖...
pip install -r requirements.txt

REM 询问是否安装OCR依赖
echo.
set /p INSTALL_OCR="是否安装OCR支持（用于处理扫描版PDF）? (y/n, 默认n): "
if "%INSTALL_OCR%"=="" set INSTALL_OCR=n

if /i "%INSTALL_OCR%"=="y" (
    echo 安装OCR依赖...
    pip install pillow pytesseract
    echo.
    echo 提示: 您还需要安装Tesseract OCR引擎
    echo 下载地址: https://github.com/UB-Mannheim/tesseract/wiki
)

REM 询问是否运行测试
echo.
set /p RUN_TEST="是否运行测试? (y/n, 默认y): "
if "%RUN_TEST%"=="" set RUN_TEST=y

if /i "%RUN_TEST%"=="y" (
    echo.
    echo 运行测试...
    python test.py
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 快速开始:
echo   查看帮助: python cli.py --help
echo   脱敏文件: python cli.py anonymize input.pdf -o output.pdf
echo   分析文件: python cli.py analyze input.pdf
echo   列出类型: python cli.py list-types
echo.
echo 更多示例请查看 examples\ 目录
echo.
pause
