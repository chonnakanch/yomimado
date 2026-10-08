# Installed UI regression checks on the disposable Windows Actions runner only.
# Windows PowerShell 5.1 supplies the .NET Framework UI Automation assemblies.
param(
    [Parameter(Mandatory=$true)][string]$Installed,
    [Parameter(Mandatory=$true)][string]$DetectorModel
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'UI automation is restricted to the disposable Windows x64 Actions runner.'
}
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class YomiMadoUiNative {
    private delegate bool EnumCallback(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumCallback callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint process);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll", SetLastError=true)] private static extern IntPtr SendMessageTimeout(IntPtr window, uint message, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
    public static IntPtr[] Windows(uint process) {
        var windows = new List<IntPtr>();
        EnumWindows((window, parameter) => {
            uint owner; GetWindowThreadProcessId(window, out owner);
            if (owner == process && IsWindowVisible(window)) windows.Add(window);
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }
    public static bool Responding(IntPtr window) {
        IntPtr result;
        return SendMessageTimeout(window, 0, IntPtr.Zero, IntPtr.Zero, 2, 1000, out result) != IntPtr.Zero;
    }
}
'@
$Root = Split-Path -Parent $PSScriptRoot
$Data = Join-Path $env:APPDATA 'com.yomimado.desktop'
$ModelPath = Join-Path $Data 'models/comictextdetector.pt.onnx'
$ExpectedModelHash = '1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f'
if ((Get-FileHash $DetectorModel -Algorithm SHA256).Hash.ToLower() -ne $ExpectedModelHash) {
    throw 'UI smoke detector hash differs.'
}
if (Test-Path $ModelPath) { throw 'Expected a fresh Actions profile without a detector.' }
$Process = $null
$MainWindow = [IntPtr]::Zero
$ModelCreated = $false
$Record = @{ windows11HardwareVerified=$false; cases=@() }

function Wait-Check {
    param([scriptblock]$Check, [string]$Failure, [int]$Seconds=40)
    $Deadline = (Get-Date).AddSeconds($Seconds)
    do {
        $Process.Refresh()
        if ($Process.HasExited) { throw "Installed desktop exited during UI check: $($Process.ExitCode)" }
        if (& $Check) { return }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $Deadline)
    throw $Failure
}
function Get-Button {
    param([string]$Name)
    $Window = [System.Windows.Automation.AutomationElement]::FromHandle($MainWindow)
    $Condition = New-Object System.Windows.Automation.AndCondition -ArgumentList @(
        (New-Object System.Windows.Automation.PropertyCondition -ArgumentList @([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)),
        (New-Object System.Windows.Automation.PropertyCondition -ArgumentList @([System.Windows.Automation.AutomationElement]::NameProperty, $Name))
    )
    return $Window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $Condition)
}
function Start-TestApp {
    $script:Process = Start-Process (Join-Path $Installed 'yomimado.exe') -PassThru
    Wait-Check { $Process.MainWindowHandle -ne [IntPtr]::Zero -and [YomiMadoUiNative]::Responding($Process.MainWindowHandle) } 'Main window never became responsive.' 75
    $script:MainWindow = $Process.MainWindowHandle
    Wait-Check { $null -ne (Get-Button 'Scan manga page') } 'Installed main UI did not load.'
}
function Stop-TestApp {
    if (-not $Process.CloseMainWindow()) { throw 'Main window did not accept normal close.' }
    if (-not $Process.WaitForExit(15000)) { throw 'Main window froze during normal quit.' }
}
function Invoke-Button {
    param([string]$Name)
    $Button = Get-Button $Name
    if ($null -eq $Button -or -not $Button.Current.IsEnabled) { throw "Button is unavailable: $Name" }
    $Button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
}

try {
    Start-TestApp
    Wait-Check { $null -ne (Get-Button 'Select detector model file') } 'Windows release hides detector import.'
    foreach ($Name in @('Select screen region', 'Scan manga page', 'Set/adjust scan area')) {
        if ((Get-Button $Name).Current.IsEnabled) { throw "Scan is enabled without a detector: $Name" }
    }
    $Record.missingModelPanel = $true
    # Exercise native dialog cancellation before staging the hash-checked fixture.
    Invoke-Button 'Select detector model file'
    Wait-Check { @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow }).Count -gt 0 } 'Model file dialog did not open.'
    $Dialog = @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow })[0]
    if (-not [YomiMadoUiNative]::SetForegroundWindow($Dialog)) { throw 'Cannot focus model file dialog.' }
    [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
    Wait-Check { @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow }).Count -eq 0 } 'Model dialog cancellation hung.'
    if ((Get-Button 'Scan manga page').Current.IsEnabled) { throw 'Cancelled import incorrectly enables scanning.' }
    $Record.modelDialogCancellation = $true
    Stop-TestApp
    # This is a smoke-only user-data fixture, never an installer/resource input.
    New-Item -ItemType Directory -Force (Split-Path -Parent $ModelPath) | Out-Null
    Copy-Item $DetectorModel $ModelPath
    $ModelCreated = $true
    Start-TestApp
    Wait-Check { $null -ne (Get-Button 'Replace detector model') } 'Staged user model was not recognized.'
    foreach ($Case in @(
        @{name='manual selection button'; button='Select screen region'},
        @{name='scan-area button'; button='Set/adjust scan area'},
        @{name='manual shortcut'; keys='^+o'},
        @{name='page-scan button'; button='Scan manga page'},
        @{name='page-scan shortcut'; keys='^+s'}
    )) {
        if (-not [YomiMadoUiNative]::SetForegroundWindow($MainWindow)) { throw 'Cannot focus installed app.' }
        if ($Case.ContainsKey('button')) { Invoke-Button $Case.button }
        else { [System.Windows.Forms.SendKeys]::SendWait($Case.keys) }
        Wait-Check {
            @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow }).Count -gt 0 -and
            [YomiMadoUiNative]::IsIconic($MainWindow)
        } "No selector appeared for $($Case.name); possible WebView2 deadlock."
        if (-not [YomiMadoUiNative]::Responding($MainWindow)) { throw "UI froze for $($Case.name)." }
        $Selector = @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow })[0]
        if (-not [YomiMadoUiNative]::SetForegroundWindow($Selector)) { throw 'Cannot focus capture selector.' }
        # Allow the selector's DOM key handler to attach before Escape.
        Start-Sleep -Milliseconds 500
        [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
        Wait-Check {
            -not [YomiMadoUiNative]::IsIconic($MainWindow) -and
            @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow }).Count -eq 0
        } "Selector did not cancel for $($Case.name)."
        if (-not [YomiMadoUiNative]::Responding($MainWindow)) { throw 'Main window is unresponsive after cancellation.' }
        $Record.cases += @{name=$Case.name; selectorOpened=$true; cancellation=$true; responsive=$true}
    }
    Stop-TestApp
    $Record.desktopSha256 = (Get-FileHash (Join-Path $Installed 'yomimado.exe') -Algorithm SHA256).Hash.ToLower()
    $Record.detectorSha256 = $ExpectedModelHash
    $Record.passed = $true
    Write-Host 'Installed Windows model setup, buttons, shortcuts and UI cancellation passed.'
} finally {
    # Preserve completed cases if a later case fails. No screenshot or model bytes.
    [IO.File]::WriteAllText((Join-Path $Root 'services/ocr/build/windows/installed-ui.json'), ($Record | ConvertTo-Json -Depth 8))
    if ($null -ne $Process) {
        $Process.Refresh()
        if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -ErrorAction SilentlyContinue }
    }
    if ($ModelCreated) { Remove-Item $ModelPath -ErrorAction SilentlyContinue }
}
