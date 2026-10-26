[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

foreach ($outputPath in @(
    (Join-Path $projectRoot "build"),
    (Join-Path $projectRoot "dist\\TicketPilot")
)) {
    if (Test-Path -LiteralPath $outputPath) {
        Remove-Item -LiteralPath $outputPath -Recurse -Force
    }
}

Write-Host "Building TicketPilot Windows onedir distribution..."
python -m PyInstaller --noconfirm --clean TicketPilot.spec

Write-Host "Build complete: $projectRoot\dist\TicketPilot\TicketPilot.exe"
