@echo off
chcp 65001 >nul
echo ========================================
echo   版本化富文本笔记工具 - 打包构建
echo ========================================
echo.

echo [信息] 安装依赖...
python -m pip install pyinstaller PyQt5 Pillow requests beautifulsoup4 pynput lxml -q
if errorlevel 1 (
    echo [错误] pip install 失败，请检查 Python 环境
    pause
    exit /b 1
)

echo [信息] 生成图标...
python make_icon.py
if errorlevel 1 (
    echo [警告] 图标生成失败，将使用默认图标
)

echo [信息] 正在打包为单文件 EXE...
pyinstaller GitNoteEditor.spec --clean --noconfirm
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo   EXE 位置: dist\GitNoteEditor.exe
echo ========================================
echo.
echo   提示：config.json 等用户数据文件会自动保存到
echo   %%APPDATA%%\GitNoteEditor\ 目录下。
echo ========================================
pause
