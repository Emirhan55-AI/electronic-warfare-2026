# BÂZ için EXE paketine veya kaynak uygulamasına bağlı masaüstü kısayolu kurar.
[CmdletBinding()]
param(
    [string]$PythonExecutable = "",
    [string]$ExecutablePath = "",
    [string]$DesktopDirectory = [Environment]::GetFolderPath('Desktop')
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$shortcutPath = Join-Path $DesktopDirectory 'BÂZ.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$installedParent = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs/BAZ'))
$previousInstalledShortcut = $shortcut.Arguments -eq '' -and
    $shortcut.Description -eq 'BÂZ — Elektronik Harp Operatör Uygulaması' -and
    $shortcut.TargetPath.StartsWith($installedParent + '\', [StringComparison]::OrdinalIgnoreCase) -and
    ((Split-Path -Leaf $shortcut.TargetPath) -eq 'BAZ.exe')
if (-not $ExecutablePath -and -not $PythonExecutable -and $previousInstalledShortcut -and
    (Test-Path -LiteralPath $shortcut.TargetPath)) {
    $ExecutablePath = $shortcut.TargetPath
}
$iconPath = Join-Path $projectDirectory 'app/operator_console/assets/baz-logo.ico'
$defaultExecutablePath = Join-Path $projectDirectory 'dist/operator-console-20260918/BAZ/BAZ.exe'
if (-not $ExecutablePath -and -not $PythonExecutable -and (Test-Path -LiteralPath $defaultExecutablePath)) {
    $ExecutablePath = $defaultExecutablePath
}
if ($ExecutablePath) {
    $targetPath = (Resolve-Path -LiteralPath $ExecutablePath).Path
    $workingDirectory = Split-Path -Parent $targetPath
    $arguments = ''
    $iconPath = $targetPath
} else {
    if (-not $PythonExecutable) {
        $PythonExecutable = (Get-Command python.exe -ErrorAction Stop).Source
    }
    $PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path
    $pythonwPath = Join-Path (Split-Path -Parent $PythonExecutable) 'pythonw.exe'
    foreach ($requiredPath in @($pythonwPath, $iconPath, $DesktopDirectory)) {
        if (-not (Test-Path -LiteralPath $requiredPath)) {
            throw "Gerekli dosya veya dizin bulunamadı: $requiredPath"
        }
    }
    Push-Location -LiteralPath $projectDirectory
    try {
        & $PythonExecutable -c 'from app.operator_console.quick_application import main'
        if ($LASTEXITCODE -ne 0) {
            throw 'Uygulama bağımlılıkları yüklenemedi. requirements/product.txt kurulumunu denetleyin.'
        }
    } finally {
        Pop-Location
    }
    $targetPath = $pythonwPath
    $workingDirectory = $projectDirectory
    $arguments = '-m app.operator_console'
}

$previousSourceShortcut = ($shortcut.Arguments -eq '-m app.operator_console') -and
    ($shortcut.WorkingDirectory -eq $projectDirectory) -and
    ((Split-Path -Leaf $shortcut.TargetPath) -eq 'pythonw.exe')
$currentShortcut = ($shortcut.TargetPath -eq $targetPath) -and
    ($shortcut.Arguments -eq $arguments) -and
    ($shortcut.WorkingDirectory -eq $workingDirectory)
if ((Test-Path -LiteralPath $shortcutPath) -and -not ($previousSourceShortcut -or $previousInstalledShortcut -or $currentShortcut)) {
    throw "Aynı adlı farklı bir kısayol korunuyor: $shortcutPath"
}
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $workingDirectory
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = 'BÂZ — Elektronik Harp Operatör Uygulaması'
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Output "Masaüstü kısayolu hazır: $shortcutPath"
