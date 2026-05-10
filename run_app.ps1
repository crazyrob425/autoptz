#!/usr/bin/env powershell
Write-Host "[PS] Starting AI-Stalker app..." -ForegroundColor Green
Set-Location "D:\aistalker"
$outputFile = "D:\aistalker\app_debug.log"
python startup.py 2>&1 | Tee-Object -FilePath $outputFile
Write-Host "[PS] App exited" -ForegroundColor Yellow
Write-Host "[PS] Debug output written to: $outputFile" -ForegroundColor Green
