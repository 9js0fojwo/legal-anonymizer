@echo off
chcp 65001 >nul 2>&1
title 法律文档脱敏工具 - 环境安装
cd /d "%~dp0"

echo.
echo   ========================================
echo     法律文档脱敏工具 - 环境自动安装
echo        by 黄灵宝同学
echo   ========================================
echo.

:: 检测虚拟环境是否已存在
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import flask, fitz, docx" >nul 2>&1
    if not errorlevel 1 (
        echo   [OK] 环境已就绪，跳过安装
        echo.
        goto :end
    )
    echo   [..] 环境不完整，重新安装依赖...
    goto :install_deps
)

:: 检测 Python
set PYTHON_CMD=
where python3 >nul 2>&1 && set PYTHON_CMD=python3
if "%PYTHON_CMD%"=="" (
    where python >nul 2>&1 && set PYTHON_CMD=python
)
if "%PYTHON_CMD%"=="" (
    echo   [!] 未找到 Python，请先安装:
    echo.
    echo       1. 访问 https://www.python.org/downloads/
    echo       2. 下载最新版本
    echo       3. 安装时务必勾选 "Add Python to PATH"
    echo       4. 安装完成后重新运行此脚本
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%i
echo   [OK] %PYVER%

:: 创建虚拟环境
echo   [..] 创建独立运行环境...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo   [!] 虚拟环境创建失败，将使用全局 Python
    goto :install_global
)
echo   [OK] 运行环境就绪

:install_deps
echo.
echo   [..] 安装依赖包（首次约需 3-5 分钟）...
.venv\Scripts\pip.exe install --upgrade pip -q >nul 2>&1
.venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 (
    echo   [!] 部分依赖安装失败，请查看错误信息
) else (
    echo   [OK] 依赖安装完成
)

:: 验证
echo.
.venv\Scripts\python.exe -c "import flask, fitz, docx" >nul 2>&1
if not errorlevel 1 (
    echo   [OK] 核心组件验证通过
) else (
    echo   [!] 部分核心依赖未成功安装
)
goto :end

:install_global
echo.
echo   [..] 安装依赖包到全局 Python...
%PYTHON_CMD% -m pip install -r requirements.txt -q
echo   [OK] 安装完成

:end
:: 创建目录
if not exist inbox mkdir inbox
if not exist output mkdir output
if not exist uploads mkdir uploads

echo.
echo   ========================================
echo     安装完成！
echo   ========================================
echo.
pause
