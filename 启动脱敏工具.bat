@echo off
chcp 65001 >nul 2>&1
title 法律文档脱敏工具 - by 黄灵宝同学
cd /d "%~dp0"

echo.
echo   ========================================
echo     法律文档脱敏工具 - 正在启动...
echo        by 黄灵宝同学
echo   ========================================
echo.

:: 检测 Python
set PYTHON_CMD=
where python3 >nul 2>&1 && set PYTHON_CMD=python3
if "%PYTHON_CMD%"=="" (
    where python >nul 2>&1 && set PYTHON_CMD=python
)
if "%PYTHON_CMD%"=="" (
    echo   [!] 未找到 Python，请先安装：
    echo.
    echo       从 https://www.python.org 下载安装
    echo       安装时务必勾选 "Add Python to PATH"
    echo.
    echo   安装完成后，重新双击此文件即可。
    echo.
    pause
    exit /b 1
)

:: 验证 Python 版本
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%i
echo   [OK] %PYVER%

:: 检查是否有虚拟环境
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
    echo   [OK] 使用虚拟环境
)

:: 检查并安装依赖
echo   [..] 检查依赖...
%PYTHON_CMD% -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo   [..] 首次运行，正在安装依赖（仅需一次）...
    echo   [..] 这可能需要几分钟，请耐心等待...
    %PYTHON_CMD% -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo   [!] 依赖安装失败，尝试使用 --user 模式...
        %PYTHON_CMD% -m pip install --user -q -r requirements.txt
    )
    echo   [OK] 依赖安装完成
) else (
    echo   [OK] 依赖已就绪
)

:: 创建必要目录
if not exist inbox mkdir inbox
if not exist output mkdir output
if not exist uploads mkdir uploads

:: 设置 HuggingFace 国内镜像
if "%HF_ENDPOINT%"=="" set HF_ENDPOINT=https://hf-mirror.com

:: 首次启动询问：是否处理英文文书
if not exist .user_config (
    echo.
    echo   ========================================
    echo     首次启动配置（仅一次）
    echo   ========================================
    echo.
    echo   工具默认能识别中文敏感信息。
    echo   是否同时启用英文识别？（需下载 2.6 GB 英文模型）
    echo.
    set /p ENABLE_EN="  您是否经常处理英文/涉外法律文书？(y/n，默认 n)："
    if /i "%ENABLE_EN%"=="y" (
        echo ENABLE_OPENAI=1>.user_config
        echo   [OK] 已启用英文模型
    ) else (
        echo ENABLE_OPENAI=0>.user_config
        echo   [OK] 仅中文模式
    )
    echo.
)

:: 读取配置
for /f "tokens=2 delims==" %%i in (.user_config) do set ENABLE_OPENAI=%%i
if "%ENABLE_OPENAI%"=="" set ENABLE_OPENAI=0

:: 预下载 AI 模型（首次）
if not exist .models_downloaded (
    echo.
    echo   ========================================
    echo     下载 AI 模型（首次仅一次）
    echo   ========================================
    echo.
    echo   正在下载中文 NER 模型（约 400 MB）...
    echo   这是核心检测能力，请耐心等待 1-3 分钟...
    echo.
    %PYTHON_CMD% -c "import os; os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com'); from transformers import AutoTokenizer, AutoModelForTokenClassification; AutoTokenizer.from_pretrained('uer/roberta-base-finetuned-cluener2020-chinese'); AutoModelForTokenClassification.from_pretrained('uer/roberta-base-finetuned-cluener2020-chinese'); print('  [OK] 中文 NER 模型下载完成')"

    if "%ENABLE_OPENAI%"=="1" (
        echo.
        echo   正在下载英文模型（约 2.6 GB，请耐心等待 5-15 分钟）...
        %PYTHON_CMD% -c "import os; os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com'); from transformers import AutoTokenizer, AutoModelForTokenClassification; AutoTokenizer.from_pretrained('openai/privacy-filter'); AutoModelForTokenClassification.from_pretrained('openai/privacy-filter'); print('  [OK] 英文模型下载完成')"
    )
    echo.>.models_downloaded
    echo   [OK] 所有模型已就绪
    echo.
)

:: 启动服务（web_app.py 会自动打开浏览器）
echo.
echo   [..] 启动服务...
echo.
echo   ========================================
echo     浏览器将自动打开，请在网页中操作
echo.
echo     关闭此窗口即可停止服务
echo   ========================================
echo.

%PYTHON_CMD% web_app.py

echo.
echo   服务已停止。
pause
