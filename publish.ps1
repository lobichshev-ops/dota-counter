<#
  Публикация сайта контрпиков на GitHub Pages.

  ВАЖНО, что сделать до запуска:
    1. Создать на github.com ПУСТОЙ репозиторий (без README и .gitignore).
    2. Запустить этот скрипт в обычном PowerShell, не через агента:
       откроется браузер для входа в GitHub.

  Пример:
       cd "C:\Users\aloof\OneDrive\Documents\deepseek-harness\default-workspace\dota-counter"
       .\publish.ps1 -User твой_логин

  Если PowerShell ругается на запрет выполнения скриптов:
       powershell -ExecutionPolicy Bypass -File .\publish.ps1 -User твой_логин
#>
param(
    [Parameter(Mandatory = $true)][string]$User,
    [string]$Repo = "dota-counter"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/4] git init" -ForegroundColor Cyan
if (-not (Test-Path ".git")) { git init -b main } else { Write-Host "      репозиторий уже есть" }

# личность задаём только для этого репозитория, глобальный конфиг не трогаем
git config user.name  $User
git config user.email "$User@users.noreply.github.com"

Write-Host "[2/4] коммит" -ForegroundColor Cyan
git add -A
$head = git rev-parse --verify HEAD 2>$null
if ($LASTEXITCODE -eq 0) {
    git commit -m "Обновление сайта контрпиков" --allow-empty
} else {
    git commit -m "Сайт контрпиков Dota 2"
}

Write-Host "[3/4] remote" -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin "https://github.com/$User/$Repo.git"

Write-Host "[4/4] push (сейчас откроется браузер для входа)" -ForegroundColor Cyan
# schannel в этой системе не работает — идём через openssl
git -c http.sslBackend=openssl push -u origin main

Write-Host ""
Write-Host "Запушено. Осталось включить Pages:" -ForegroundColor Green
Write-Host "  Settings -> Pages -> Source: Deploy from a branch -> main / (root) -> Save"
Write-Host "Через минуту сайт будет здесь:" -ForegroundColor Green
Write-Host "  https://$User.github.io/$Repo/" -ForegroundColor Green
