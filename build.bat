@echo off
chcp 65001 >nul
echo ========================================
echo   Git 版本化富文本笔记工具 - 打包构建
echo ========================================
echo.

python -m pip install pyinstaller -q
if errorlevel 1 (
    echo [错误] pip install 失败，请检查 Python 环境
    pause
    exit /b 1
)

echo [信息] 正在打包为单文件 EXE ...
pyinstaller --onefile --windowed --noupx ^
    --name "GitNoteEditor" ^
    --hidden-import PyQt5 ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    --clean ^
    main.py

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
pause
