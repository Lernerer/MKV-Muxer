<#
.SYNOPSIS
    Полная сборка MKV Muxer: portable EXE, onedir, установщик, ZIP и SHA256SUMS.

.DESCRIPTION
    Скрипт выполняет всё, что нужно для выпуска новой версии:
      1) PyInstaller onefile  -> dist\MKV_Muxer.exe
      2) PyInstaller onedir   -> dist\MKV_Muxer\
      3) Inno Setup           -> release\MKV_Muxer_<версия>_setup.exe
      4) portable ZIP         -> release\MKV_Muxer_<версия>_portable.zip
      5) SHA256SUMS.txt       -> release\SHA256SUMS.txt

    Версия берётся из installer\MKV_Muxer.iss (MyAppVersion).
    Пути к Python, mkvmerge и ISCC определяются автоматически;
    при необходимости их можно передать параметрами.

.PARAMETER Python
    Путь к python.exe. По умолчанию ищется Python 3.10-3.16 в профиле пользователя,
    затем python.exe из PATH.

.PARAMETER Mkvmerge
    Путь к mkvmerge.exe. По умолчанию: переменная среды MKVMERGE,
    затем C:\Program Files\MKVToolNix\mkvmerge.exe.

.PARAMETER Iscc
    Путь к ISCC.exe (Inno Setup). По умолчанию ищется в LOCALAPPDATA и Program Files.

.PARAMETER SkipInstaller
    Не собирать установщик (нужен только portable EXE и ZIP).

.PARAMETER KeepBuild
    Не удалять промежуточные папки build\onefile и build\onedir.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\build_release.ps1

.EXAMPLE
    .\build_release.ps1 -Mkvmerge "D:\MKVToolNix\mkvmerge.exe" -KeepBuild
#>
[CmdletBinding()]
param(
    [string]$Python,
    [string]$Mkvmerge,
    [string]$Iscc,
    [switch]$SkipInstaller,
    [switch]$KeepBuild
)

$ErrorActionPreference = 'Stop'

function Write-Step {
    param([string]$Text)
    Write-Host ''
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$What
    )
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$What завершилось с кодом $LASTEXITCODE"
    }
}

function Get-Sha256 {
    param([string]$Path)
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$specOnefile = Join-Path $root 'MKV_Muxer.spec'
$specOnedir = Join-Path $root 'MKV_Muxer_onedir.spec'
$issPath = Join-Path $root 'installer\MKV_Muxer.iss'
$dist = Join-Path $root 'dist'
$release = Join-Path $root 'release'
$build = Join-Path $root 'build'

foreach ($required in @($specOnefile, $specOnedir, (Join-Path $root 'mkv_muxer.py'),
                       (Join-Path $root 'app.ico'), (Join-Path $root 'LICENSES'),
                       (Join-Path $root 'README.txt'))) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Не найден обязательный файл или папка: $required"
    }
}

# --- версия из сценария Inno Setup ---
$version = '2.0'
if (Test-Path -LiteralPath $issPath) {
    $match = Select-String -LiteralPath $issPath -Pattern '#define\s+MyAppVersion\s+"([^"]+)"' |
        Select-Object -First 1
    if ($match) {
        $version = $match.Matches[0].Groups[1].Value
    }
}

Write-Host "MKV Muxer $version - полная сборка" -ForegroundColor White

# --- Python ---
if (-not $Python) {
    $candidates = @()
    foreach ($v in 316..310) {
        $candidates += Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"
    }
    $inPath = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($inPath) {
        $candidates += $inPath.Source
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            $Python = $candidate
            break
        }
    }
}

if (-not $Python -or -not (Test-Path -LiteralPath $Python)) {
    throw 'Python не найден. Укажите путь: -Python "C:\...\python.exe"'
}

& $Python -c "import PyInstaller, customtkinter" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Для $Python не установлены PyInstaller и/или customtkinter. Выполните: & '$Python' -m pip install pyinstaller customtkinter pillow"
}

# --- mkvmerge ---
if (-not $Mkvmerge) {
    $Mkvmerge = $env:MKVMERGE
}
if (-not $Mkvmerge) {
    $Mkvmerge = 'C:\Program Files\MKVToolNix\mkvmerge.exe'
}
if (-not (Test-Path -LiteralPath $Mkvmerge)) {
    throw "mkvmerge.exe не найден: $Mkvmerge. Укажите путь: -Mkvmerge ""C:\...\mkvmerge.exe"""
}
# spec-файлы читают этот путь
$env:MKVMERGE = $Mkvmerge

# --- Inno Setup ---
if (-not $SkipInstaller -and -not $Iscc) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\InnoSetup7\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\InnoSetup6\ISCC.exe'),
        'C:\Program Files\Inno Setup 7\ISCC.exe',
        'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        'C:\Program Files\Inno Setup 6\ISCC.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $Iscc = $candidate
            break
        }
    }
}
if (-not $SkipInstaller -and (-not $Iscc -or -not (Test-Path -LiteralPath $Iscc))) {
    throw 'ISCC.exe (Inno Setup) не найден. Укажите путь: -Iscc "C:\...\ISCC.exe" или используйте -SkipInstaller'
}

New-Item -ItemType Directory -Path $dist -Force | Out-Null
New-Item -ItemType Directory -Path $release -Force | Out-Null

Write-Step 'portable EXE (onefile)'
Invoke-Checked $Python @(
    '-m', 'PyInstaller', '--noconfirm',
    '--distpath', $dist,
    '--workpath', (Join-Path $build 'onefile'),
    $specOnefile
) 'PyInstaller (onefile)'

if (-not $SkipInstaller) {
    Write-Step 'onedir для установщика'
    Invoke-Checked $Python @(
        '-m', 'PyInstaller', '--noconfirm',
        '--distpath', $dist,
        '--workpath', (Join-Path $build 'onedir'),
        $specOnedir
    ) 'PyInstaller (onedir)'

    Write-Step 'установщик (Inno Setup)'
    Invoke-Checked $Iscc @($issPath) 'Inno Setup'
}

$exeOnefile = Join-Path $dist 'MKV_Muxer.exe'
if (-not (Test-Path -LiteralPath $exeOnefile)) {
    throw "Сборка не создала файл: $exeOnefile"
}
if (-not $SkipInstaller) {
    $exeOnedir = Join-Path $dist 'MKV_Muxer\MKV_Muxer.exe'
    if (-not (Test-Path -LiteralPath $exeOnedir)) {
        throw "Сборка не создала файл: $exeOnedir"
    }
}

# --- portable ZIP ---
Write-Step 'portable ZIP'
$stageRoot = Join-Path $release '_stage'
$appDir = Join-Path $stageRoot 'MKV_Muxer'
if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $appDir -Force | Out-Null

Copy-Item -LiteralPath $exeOnefile -Destination $appDir
Copy-Item -LiteralPath (Join-Path $root 'mkv_muxer.py') -Destination $appDir
Copy-Item -LiteralPath (Join-Path $root 'README.txt') -Destination $appDir
Copy-Item -LiteralPath (Join-Path $root 'LICENSES') -Destination $appDir -Recurse

$exeHash = Get-Sha256 (Join-Path $appDir 'MKV_Muxer.exe')
$pyHash = Get-Sha256 (Join-Path $appDir 'mkv_muxer.py')
Set-Content -LiteralPath (Join-Path $appDir 'SHA256SUMS.txt') -Encoding Ascii -Value @(
    "$exeHash  MKV_Muxer.exe",
    "$pyHash  mkv_muxer.py"
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$zipPath = Join-Path $release "MKV_Muxer_${version}_portable.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$archive = [System.IO.Compression.ZipFile]::Open(
    $zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in (Get-ChildItem -LiteralPath $stageRoot -Recurse -File)) {
        $entryName = $file.FullName.Substring($stageRoot.Length + 1).Replace('\', '/')
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive, $file.FullName, $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal)
    }
}
finally {
    $archive.Dispose()
}

$check = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $entryCount = $check.Entries.Count
}
finally {
    $check.Dispose()
}
if ($entryCount -lt 10) {
    throw "ZIP содержит слишком мало файлов ($entryCount), упаковка не удалась"
}
Remove-Item -LiteralPath $stageRoot -Recurse -Force

# --- итоговые контрольные суммы ---
$artifactNames = @()
$setupName = "MKV_Muxer_${version}_setup.exe"
if (Test-Path -LiteralPath (Join-Path $release $setupName)) {
    $artifactNames += $setupName
}
$artifactNames += "MKV_Muxer_${version}_portable.zip"

$sumLines = @()
foreach ($name in $artifactNames) {
    $path = Join-Path $release $name
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Не найден готовый файл: $path"
    }
    $sumLines += "$(Get-Sha256 $path)  $name"
}
Set-Content -LiteralPath (Join-Path $release 'SHA256SUMS.txt') -Encoding Ascii -Value $sumLines

# --- уборка ---
if (-not $KeepBuild) {
    foreach ($dir in @((Join-Path $build 'onefile'), (Join-Path $build 'onedir'))) {
        if (Test-Path -LiteralPath $dir) {
            Remove-Item -LiteralPath $dir -Recurse -Force
        }
    }
    if ((Test-Path -LiteralPath $build) -and
        -not (Get-ChildItem -LiteralPath $build -Force | Select-Object -First 1)) {
        Remove-Item -LiteralPath $build -Force
    }
    $pycache = Join-Path $root '__pycache__'
    if (Test-Path -LiteralPath $pycache) {
        Remove-Item -LiteralPath $pycache -Recurse -Force
    }
}

Write-Host ''
Write-Host 'Готово.' -ForegroundColor Green
foreach ($name in $artifactNames) {
    $path = Join-Path $release $name
    $size = [math]::Round((Get-Item -LiteralPath $path).Length / 1MB, 1)
    Write-Host ("  {0}  ({1} МБ)" -f $path, $size)
}
Write-Host ("  {0}" -f (Join-Path $release 'SHA256SUMS.txt'))
Write-Host ''
Write-Host "Python:     $Python"
Write-Host "mkvmerge:   $Mkvmerge"
if (-not $SkipInstaller) {
    Write-Host "Inno Setup: $Iscc"
}

exit 0
