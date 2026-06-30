# Claude-Gram v2 Launcher for Windows
# Fork: claude-gram @ripcats by tg: @justidev

$ErrorActionPreference = "Stop"

# Проверка Python
try {
    python --version | Out-Null
} catch {
    Write-Host "Python не найден. Устанавливаем через winget..." -ForegroundColor Yellow
    try {
        winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
        Write-Host "Python успешно установлен. Пожалуйста, перезапустите PowerShell и этот скрипт." -ForegroundColor Green
        Exit
    } catch {
        Write-Host "Не удалось установить Python автоматически. Скачайте его с python.org" -ForegroundColor Red
        Exit 1
    }
}

# Запуск основного установщика на Python
$INSTALL_DIR = Get-Location
python "$INSTALL_DIR\install.py"
