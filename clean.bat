@echo off
echo 执行项目清理？（按任意键执行，Ctrl+C取消）
pause > nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
if exist "New-Code\config.json" del /q "New-Code\config.json"
if exist "New-Code\logs" rd /s /q "New-Code\logs"
echo 清理完成！