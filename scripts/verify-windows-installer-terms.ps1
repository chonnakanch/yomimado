# Exercise our installer mechanics on the disposable Actions runner only.
# This is not a maintainer licence grant or protected publication approval.
param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Installer terms tests require the disposable Windows x64 Actions runner.'
}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$Root = Split-Path -Parent $PSScriptRoot
$Manifest = Get-Content (Join-Path $Root 'docs/windows-microsoft-terms.json') -Raw | ConvertFrom-Json
$Terms = Join-Path $Root $Manifest.termsFile
$Hash = (Get-FileHash $Terms -Algorithm SHA256).Hash.ToLower()
if ($Hash -ne $Manifest.termsSha256) { throw 'Installer component terms hash differs.' }
$Suite = Join-Path $env:RUNNER_TEMP ('yomimado-installer-terms-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $Suite | Out-Null
$Output = Join-Path $Root 'services/ocr/build/windows/installer-terms-verification.json'
$Record = @{
    passed=$false; termsSha256=$Hash;
    installerSha256=(Get-FileHash $Installer -Algorithm SHA256).Hash.ToLower();
    cases=@(); humanApproval=$false
}
$Process = $null

function Rejected-Install {
    param([string]$Name, [string[]]$Flags)
    $Destination = Join-Path $Suite $Name
    $p = Start-Process $Installer -ArgumentList ($Flags + "/D=$Destination") -PassThru
    try {
        if (-not $p.WaitForExit(30000)) { throw "Installer did not reject $Name promptly." }
        if ($p.ExitCode -ne 2 -or (Test-Path $Destination)) {
            throw "Installer terms rejection failed: $Name, exit $($p.ExitCode)."
        }
        $script:Record.cases += @{name=$Name; exitCode=$p.ExitCode; filesWritten=$false}
    } finally {
        if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    }
}

function Installer-Window {
    # NSIS may extract into a child process; only inspect this launch's family.
    $Owners = @($script:Process.Id)
    $Children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($script:Process.Id)")
    $Owners += @($Children | ForEach-Object { [int]$_.ProcessId })
    foreach ($Owner in $Owners) {
        $Condition = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$Owner)
        $Windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
            [System.Windows.Automation.TreeScope]::Children, $Condition)
        foreach ($Window in $Windows) {
            if ($Window.Current.Name -like 'YomiMado*') { return $Window }
        }
    }
    return $null
}

function Button {
    param($Window, [string]$Name)
    $Condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button)
    foreach ($Control in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $Condition)) {
        if ($Control.Current.Name.Replace('&', '') -eq $Name) { return $Control }
    }
    return $null
}

try {
    Rejected-Install 'silent-missing' @('/S')
    Rejected-Install 'passive-missing' @('/P')
    Rejected-Install 'silent-wrong-hash' @('/S', ('/ACCEPTMSRUNTIME=' + ('0' * 64)))
    Rejected-Install 'passive-wrong-hash' @('/P', ('/ACCEPTMSRUNTIME=' + ('0' * 64)))
    $Destination = Join-Path $Suite 'interactive-cancel'
    $Process = Start-Process $Installer -ArgumentList "/D=$Destination" -PassThru
    $Deadline = (Get-Date).AddSeconds(40)
    $Window = $null
    do {
        $Window = Installer-Window
        if ($null -ne $Window -and $null -ne (Button $Window 'Next >')) { break }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $Deadline)
    if ($null -eq $Window) { throw 'Installer welcome window is missing.' }
    $Next = Button $Window 'Next >'
    if ($null -eq $Next -or -not $Next.Current.IsEnabled) { throw 'Welcome Next button is unavailable.' }
    ([System.Windows.Automation.InvokePattern]$Next.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern)).Invoke()
    $Deadline = (Get-Date).AddSeconds(15)
    $Checkbox = $null
    do {
        $Window = Installer-Window
        if ($null -ne $Window) {
            $Condition = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                [System.Windows.Automation.ControlType]::CheckBox)
            $Checkbox = $Window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $Condition)
            if ($null -ne $Checkbox) { break }
        }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $Deadline)
    if ($null -eq $Checkbox) { throw 'Terms page acceptance checkbox is missing.' }
    $Toggle = [System.Windows.Automation.TogglePattern]$Checkbox.GetCurrentPattern(
        [System.Windows.Automation.TogglePattern]::Pattern)
    $Next = Button $Window 'Next >'
    if ($Toggle.Current.ToggleState -ne [System.Windows.Automation.ToggleState]::Off -or
        $null -eq $Next -or $Next.Current.IsEnabled) {
        throw 'Interactive setup can continue without affirmative acceptance.'
    }
    $Texts = @()
    foreach ($Control in $Window.FindAll([System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition)) {
        $Texts += $Control.Current.Name
        $Pattern = $null
        if ($Control.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$Pattern)) {
            $Texts += ([System.Windows.Automation.TextPattern]$Pattern).DocumentRange.GetText(-1)
        } elseif ($Control.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$Pattern)) {
            $Texts += ([System.Windows.Automation.ValuePattern]$Pattern).Current.Value
        }
    }
    if (($Texts -join ' ') -notlike '*YomiMado - Microsoft runtime component terms*') {
        throw 'Interactive terms text is missing or wrong.'
    }
    $Cancel = Button $Window 'Cancel'
    if ($null -eq $Cancel) { throw 'Terms Cancel button is missing.' }
    ([System.Windows.Automation.InvokePattern]$Cancel.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern)).Invoke()
    if (-not $Process.WaitForExit(15000) -or (Test-Path $Destination)) {
        throw 'Declining installer terms did not exit without writing files.'
    }
    $Record.cases += @{
        name='interactive-cancel'; checkboxInitiallyUnchecked=$true;
        nextInitiallyDisabled=$true; termsTextPresent=$true; filesWritten=$false
    }
    $Record.passed = $true
    Write-Host 'Component terms reject silent/passive missing or wrong assent; interactive decline writes no files.'
} catch {
    $Record.error = $_.Exception.Message
    throw
} finally {
    if ($null -ne $Process -and -not $Process.HasExited) { Stop-Process -Id $Process.Id -Force }
    $Record | ConvertTo-Json -Depth 6 | Set-Content $Output -Encoding UTF8
    Remove-Item $Suite -Recurse -Force
}
