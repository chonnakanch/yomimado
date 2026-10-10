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
using System.Text;
public static class YomiMadoUiNative {
    private delegate bool EnumCallback(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumCallback callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, EnumCallback callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint process);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern int GetDlgCtrlID(IntPtr window);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr window);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", SetLastError=true)] private static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
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
    public static string Text(IntPtr window) {
        var text = new StringBuilder(512);
        GetWindowText(window, text, text.Capacity);
        return text.ToString();
    }
    public static IntPtr CancelButton(IntPtr dialog) {
        IntPtr cancel = IntPtr.Zero;
        EnumChildWindows(dialog, (window, parameter) => {
            // IDCANCEL is the native common-dialog control ID. The runner is
            // English; require its label and state before sending a click.
            if (GetDlgCtrlID(window) == 2 && Text(window).Replace("&", "") == "Cancel"
                && IsWindowVisible(window) && IsWindowEnabled(window)) cancel = window;
            return true;
        }, IntPtr.Zero);
        return cancel;
    }
    public static string[] Controls(IntPtr dialog) {
        var controls = new List<string>();
        EnumChildWindows(dialog, (window, parameter) => {
            controls.Add(GetDlgCtrlID(window) + ":" + Text(window));
            return controls.Count < 100;
        }, IntPtr.Zero);
        return controls.ToArray();
    }
    public static bool ClickButton(IntPtr button) {
        return PostMessage(button, 0x00F5, IntPtr.Zero, IntPtr.Zero); // BM_CLICK
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
$SecondProcess = $null
$MainWindow = [IntPtr]::Zero
$ModelCreated = $false
$Record = @{
    windows11HardwareVerified=$false; cases=@();
    desktopSha256=(Get-FileHash (Join-Path $Installed 'yomimado.exe') -Algorithm SHA256).Hash.ToLower()
}

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
    $Record.phase = 'missing model and startup conflict'
    Start-TestApp
    Wait-Check { $null -ne (Get-Button 'Select detector model file') } 'Windows release hides detector import.'
    foreach ($Name in @('Select screen region', 'Scan manga page', 'Set/adjust scan area')) {
        if ((Get-Button $Name).Current.IsEnabled) { throw "Scan is enabled without a detector: $Name" }
    }
    $Record.missingModelPanel = $true
    Write-Host 'Missing-model panel and disabled scan buttons passed.'
    # A second instance must explain the occupied service port, then exit
    # normally after acknowledgement without blocking the first app.
    $SecondProcess = Start-Process (Join-Path $Installed 'yomimado.exe') -PassThru
    Wait-Check {
        $SecondProcess.Refresh()
        if ($SecondProcess.HasExited) { throw 'Second instance exited without its startup error dialog.' }
        @([YomiMadoUiNative]::Windows($SecondProcess.Id) | Where-Object {
            [System.Windows.Automation.AutomationElement]::FromHandle($_).Current.Name -eq 'YomiMado startup failed'
        }).Count -eq 1
    } 'Occupied-port startup error dialog did not appear.'
    $ErrorWindow = @([YomiMadoUiNative]::Windows($SecondProcess.Id) | Where-Object {
        [System.Windows.Automation.AutomationElement]::FromHandle($_).Current.Name -eq 'YomiMado startup failed'
    })[0]
    $ErrorElement = [System.Windows.Automation.AutomationElement]::FromHandle($ErrorWindow)
    $ErrorText = ($ErrorElement.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | ForEach-Object { $_.Current.Name }) -join ' '
    if ($ErrorText -notmatch 'Port 8766 is occupied') { throw 'Second instance did not explain the occupied port.' }
    if (-not [YomiMadoUiNative]::SetForegroundWindow($ErrorWindow)) { throw 'Cannot focus startup error dialog.' }
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    if (-not $SecondProcess.WaitForExit(15000)) { throw 'Startup error acknowledgement did not exit.' }
    $SecondProcess.Refresh()
    $Record.occupiedPortExitCode = $SecondProcess.ExitCode
    # Pinned tauri-runtime-wry 2.11.4 maps RequestExit to ControlFlow::Exit,
    # which uses zero even when AppHandle::exit requested one. Require normal
    # termination and retain the actual result; do not mistake it for a hang.
    if ($SecondProcess.ExitCode -notin @(0, 1)) { throw "Unexpected startup-error exit code: $($SecondProcess.ExitCode)" }
    if (-not [YomiMadoUiNative]::Responding($MainWindow)) { throw 'Second instance blocked the original app.' }
    $Record.occupiedPortDialog = $true
    Write-Host "Occupied-port dialog, acknowledgement and original app responsiveness passed; exit code $($SecondProcess.ExitCode)."
    # Exercise native dialog cancellation before staging the hash-checked fixture.
    $Record.phase = 'model dialog cancellation'
    Invoke-Button 'Select detector model file'
    $script:CancelButton = [IntPtr]::Zero
    $script:ModelDialogHandle = [IntPtr]::Zero
    Wait-Check {
        foreach ($Handle in [YomiMadoUiNative]::Windows($Process.Id)) {
            if ($Handle -eq $MainWindow) { continue }
            if ([YomiMadoUiNative]::Text($Handle) -ne 'Open') { continue }
            $Button = [YomiMadoUiNative]::CancelButton($Handle)
            if ($Button -ne [IntPtr]::Zero) {
                $script:CancelButton = $Button
                $script:ModelDialogHandle = $Handle
                return $true
            }
        }
        return $false
    } 'Model file dialog never exposed an enabled Cancel button.'
    # The common dialog's UIA provider did not expose Cancel on this runner.
    # Activate the actual Open dialog and click its native IDCANCEL control;
    # never send Escape to an arbitrary auxiliary/IME window.
    if (-not [YomiMadoUiNative]::SetForegroundWindow($ModelDialogHandle)) { throw 'Cannot focus model file dialog.' }
    Wait-Check { [YomiMadoUiNative]::GetForegroundWindow() -eq $ModelDialogHandle } 'Model file dialog did not receive focus.'
    if (-not [YomiMadoUiNative]::ClickButton($CancelButton)) { throw 'Cannot click the native model dialog Cancel control.' }
    Wait-Check { -not [YomiMadoUiNative]::IsWindowVisible($ModelDialogHandle) } 'Model dialog cancellation hung.'
    Wait-Check {
        $Button = Get-Button 'Select detector model file'
        $null -ne $Button -and $Button.Current.IsEnabled
    } 'Cancelled model import did not finish in the frontend.'
    if ((Get-Button 'Scan manga page').Current.IsEnabled) { throw 'Cancelled import incorrectly enables scanning.' }
    $Record.modelDialogCancellation = $true
    Write-Host 'Model import dialog cancellation passed.'
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
        $Record.phase = $Case.name
        if (-not [YomiMadoUiNative]::SetForegroundWindow($MainWindow)) { throw 'Cannot focus installed app.' }
        if ($Case.ContainsKey('button')) { Invoke-Button $Case.button }
        else { [System.Windows.Forms.SendKeys]::SendWait($Case.keys) }
        Wait-Check {
            @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow }).Count -gt 0 -and
            [YomiMadoUiNative]::IsIconic($MainWindow)
        } "No selector appeared for $($Case.name); possible WebView2 deadlock."
        if (-not [YomiMadoUiNative]::Responding($MainWindow)) { throw "UI froze for $($Case.name)." }
        $script:Selector = [IntPtr]::Zero
        Wait-Check {
            foreach ($Handle in [YomiMadoUiNative]::Windows($Process.Id)) {
                if ($Handle -eq $MainWindow) { continue }
                $Element = [System.Windows.Automation.AutomationElement]::FromHandle($Handle)
                $Names = ($Element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | ForEach-Object { $_.Current.Name }) -join ' '
                if ($Names -match 'Press Escape to (cancel|close)') {
                    $script:Selector = $Handle
                    return $true
                }
            }
            return $false
        } "Selector UI did not load for $($Case.name)."
        if (-not [YomiMadoUiNative]::SetForegroundWindow($Selector)) { throw 'Cannot focus capture selector.' }
        # Wait for rendered content rather than guessing WebView2 startup time.
        Start-Sleep -Milliseconds 200
        [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
        Wait-Check {
            -not [YomiMadoUiNative]::IsIconic($MainWindow) -and
            -not [YomiMadoUiNative]::IsWindowVisible($Selector)
        } "Selector did not cancel for $($Case.name)."
        if (-not [YomiMadoUiNative]::Responding($MainWindow)) { throw 'Main window is unresponsive after cancellation.' }
        $Record.cases += @{name=$Case.name; selectorOpened=$true; cancellation=$true; responsive=$true}
        Write-Host "Installed UI passed: $($Case.name)."
    }
    Stop-TestApp
    $Record.detectorSha256 = $ExpectedModelHash
    $Record.passed = $true
    $Record.phase = 'complete'
    Write-Host 'Installed Windows model setup, buttons, shortcuts and UI cancellation passed.'
} catch {
    # This driver has no release credentials and runs only on the disposable
    # runner. Retain its actual failure without screenshots or model bytes.
    $Record.passed = $false
    $Record.failure = @{
        message=$_.Exception.Message;
        exceptionType=$_.Exception.GetType().FullName;
        lineNumber=$_.InvocationInfo.ScriptLineNumber
    }
    $EncodedFailure = $_.Exception.Message.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    Write-Host "::error title=Installed Windows UI failed::$EncodedFailure"
    throw
} finally {
    # Preserve completed cases if a later case fails. No screenshot or model bytes.
    if ($null -ne $Process -and -not $Process.HasExited) {
        try {
            $Record.visibleWindows = @([YomiMadoUiNative]::Windows($Process.Id) | ForEach-Object {
                @{
                    handle=$_.ToInt64(); title=[YomiMadoUiNative]::Text($_);
                    controls=[YomiMadoUiNative]::Controls($_);
                    responding=[YomiMadoUiNative]::Responding($_);
                    minimized=[YomiMadoUiNative]::IsIconic($_);
                    foreground=($_ -eq [YomiMadoUiNative]::GetForegroundWindow())
                }
            })
        } catch { $Record.windowSnapshotError = $_.Exception.Message }
    }
    [IO.File]::WriteAllText((Join-Path $Root 'services/ocr/build/windows/installed-ui.json'), ($Record | ConvertTo-Json -Depth 8))
    if ($null -ne $Process) {
        $Process.Refresh()
        if (-not $Process.HasExited) { Stop-Process -Id $Process.Id -ErrorAction SilentlyContinue }
    }
    if ($null -ne $SecondProcess) {
        $SecondProcess.Refresh()
        if (-not $SecondProcess.HasExited) { Stop-Process -Id $SecondProcess.Id -ErrorAction SilentlyContinue }
    }
    if ($ModelCreated) { Remove-Item $ModelPath -ErrorAction SilentlyContinue }
}
