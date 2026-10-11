param([Parameter(Mandatory=$true)][string]$Installed)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $PSScriptRoot
$Data = Join-Path $env:APPDATA 'com.yomimado.desktop'
$AppExe = Join-Path $Installed 'yomimado.exe'
if (-not (Test-Path $AppExe)) { throw 'Installed desktop executable is missing.' }
$OriginalPath = $env:PATH
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
$Process = Start-Process $AppExe -PassThru
$Child = $null
try {
    $Deadline = (Get-Date).AddSeconds(75)
    while ((Get-Date) -lt $Deadline) {
        $Process.Refresh()
        if ($Process.HasExited) { throw "Installed desktop exited: $($Process.ExitCode)" }
        $Children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Process.Id)" | Where-Object { $_.Name -eq 'yomimado-ocr.exe' })
        if ($Children.Count -eq 1) {
            $Child = $Children[0]
            $Ready = @(Get-ChildItem $Data -Filter "service-ready-$($Process.Id)-*.json" -ErrorAction SilentlyContinue)
            if ($Ready.Count -eq 1) {
                $Proof = Get-Content $Ready[0].FullName -Raw | ConvertFrom-Json
                if ($Proof.pid -eq $Child.ProcessId -and $Proof.port -eq 8766) { break }
            }
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $Child -or (Get-Date) -ge $Deadline) { throw 'Installed bundled startup did not complete.' }
    if ($Child.ExecutablePath -ne (Join-Path $Installed 'ocr/runtime/yomimado-ocr.exe')) { throw 'Desktop launched a different runtime.' }
    $Health = Invoke-RestMethod 'http://127.0.0.1:8766/health'
    if ($Health.status -ne 'ok' -or $Health.ocr -ne 'manga') { throw 'Installed service health failed.' }
    # Close the actual desktop normally; then verify the service died as well.
    if (-not $Process.CloseMainWindow()) { throw 'Desktop main window could not be closed.' }
    if (-not $Process.WaitForExit(15000)) { throw 'Desktop did not exit after window close.' }
    $Deadline = (Get-Date).AddSeconds(10)
    while ((Get-Process -Id $Child.ProcessId -ErrorAction SilentlyContinue) -and (Get-Date) -lt $Deadline) { Start-Sleep -Milliseconds 100 }
    if (Get-Process -Id $Child.ProcessId -ErrorAction SilentlyContinue) { throw 'Bundled service survived desktop exit.' }
    if (Test-NetConnection 127.0.0.1 -Port 8766 -InformationLevel Quiet -WarningAction SilentlyContinue) { throw 'OCR port remained occupied after quit.' }
    $Record = @{
        installedPath=$Installed; dataPath=$Data; pythonOrCudaOnPath=$false;
        desktopSha256=(Get-FileHash $AppExe -Algorithm SHA256).Hash.ToLower();
        desktopSignature=(Get-AuthenticodeSignature $AppExe).Status.ToString();
        bundledStartup=$true; quitCleanup=$true; windows11HardwareVerified=$false
    }
    $Record | ConvertTo-Json | Set-Content (Join-Path $Root 'services/ocr/build/windows/installed-verification.json') -Encoding utf8NoBOM
} finally {
    # Cleanup is limited to the child we started. Never kill by executable name.
    $Process.Refresh()
    if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -ErrorAction SilentlyContinue }
    $env:PATH = $OriginalPath
}
