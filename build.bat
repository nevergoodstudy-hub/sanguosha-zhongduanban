@echo off
chcp 65001 >nul
echo ========================================
echo    三国杀 - 打包脚本
echo ========================================
echo.

echo [1/4] 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo     正在安装 PyInstaller...
    pip install pyinstaller -q
)
echo     PyInstaller 已就绪

echo.
echo [2/4] 清理旧的构建文件...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
echo     清理完成

echo.
echo [3/4] 开始打包...
pyinstaller sanguosha.spec --noconfirm

echo.
echo [4/4] 打包完成！
echo.
echo ========================================
if exist "dist\三国杀.exe" (
    echo    成功！可执行文件位于:
    echo    dist\三国杀.exe
    echo.
    echo    文件大小:
    for %%A in ("dist\三国杀.exe") do echo    %%~zA bytes
) else (
    echo    打包失败，请检查错误信息
)
echo ========================================
echo.
pause
