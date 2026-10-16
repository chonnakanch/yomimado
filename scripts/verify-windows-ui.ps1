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
. (Join-Path $PSScriptRoot 'windows-ui-driver.ps1')
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
$ToolbarWindow = [IntPtr]::Zero
$ModelCreated = $false
$Record = @{
    windows11HardwareVerified=$false; cases=@();
    desktopSha256=(Get-FileHash (Join-Path $Installed 'yomimado.exe') -Algorithm SHA256).Hash.ToLower()
}

function Wait-Check {
    param([scriptblock]$Check, [string]$Failure, [int]$Seconds=40)
    Wait-YomiMadoUi $Process $Check $Failure $Seconds
}
function Get-Button {
    param([string]$Name, [IntPtr]$Window=$script:MainWindow)
    return Get-YomiMadoAction $Window $Name
}
function Start-TestApp {
    $script:Process = Start-Process (Join-Path $Installed 'yomimado.exe') -PassThru
    $script:ToolbarWindow = Wait-YomiMadoWindow $Process 'YomiMado toolbar'
    $script:MainWindow = $ToolbarWindow
    Wait-Check { $null -ne (Get-Button 'Selected Area') -and $null -ne (Get-Button 'Whole Screen') } 'Installed toolbar did not load.'
}
function Open-TestSettings {
    Invoke-YomiMadoMenuAction $Process 'Settings'
    $script:MainWindow = Wait-YomiMadoWindow $Process 'YomiMado*Settings'
}
function Stop-TestApp {
    Stop-YomiMadoViaMenu $Process
}
function Invoke-Button {
    param([string]$Name)
    Invoke-YomiMadoAction $MainWindow $Name
}

try {
    $Record.phase = 'missing model and startup conflict'
    Start-TestApp
    Open-TestSettings
    Wait-Check { $null -ne (Get-Button 'Select detector model file') } 'Windows release hides detector import.'
    foreach ($Name in @('Selected Area', 'Whole Screen')) {
        if ((Get-Button $Name $ToolbarWindow).Current.IsEnabled) { throw "Scan is enabled without a detector: $Name" }
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
    if ((Get-Button 'Whole Screen' $ToolbarWindow).Current.IsEnabled) { throw 'Cancelled import incorrectly enables scanning.' }
    $Record.modelDialogCancellation = $true
    Write-Host 'Model import dialog cancellation passed.'
    Stop-TestApp
    # This is a smoke-only user-data fixture, never an installer/resource input.
    New-Item -ItemType Directory -Force (Split-Path -Parent $ModelPath) | Out-Null
    Copy-Item $DetectorModel $ModelPath
    $ModelCreated = $true
    Start-TestApp
    Open-TestSettings
    Wait-Check { $null -ne (Get-Button 'Replace detector model') } 'Staged user model was not recognized.'
    $SettingsWindow = $MainWindow
    if (-not [YomiMadoUiNative]::CloseWindow($SettingsWindow)) { throw 'Cannot close Settings.' }
    Wait-Check { -not [YomiMadoUiNative]::IsWindowVisible($SettingsWindow) -and [YomiMadoUiNative]::IsWindowVisible($ToolbarWindow) } 'Closing Settings did not leave the toolbar running.'
    $Record.settingsCloseKeepsToolbar = $true
    $script:MainWindow = $ToolbarWindow
    Wait-Check {
        (Get-Button 'Selected Area').Current.IsEnabled -and (Get-Button 'Whole Screen').Current.IsEnabled
    } 'Installed detector did not enable the scan controls.'
    foreach ($Case in @(
        @{name='manual selection button'; button='Selected Area'},
        @{name='manual shortcut'; keys='^+o'},
        @{name='page-scan button'; button='Whole Screen'},
        @{name='page-scan shortcut'; keys='^+s'}
    )) {
        $Record.phase = $Case.name
        if (-not [YomiMadoUiNative]::SetForegroundWindow($MainWindow)) { throw 'Cannot focus installed app.' }
        if ($Case.ContainsKey('button')) { Invoke-Button $Case.button }
        else { [System.Windows.Forms.SendKeys]::SendWait($Case.keys) }
        Wait-Check {
            @([YomiMadoUiNative]::Windows($Process.Id) | Where-Object { $_ -ne $MainWindow }).Count -gt 0 -and
            -not [YomiMadoUiNative]::IsWindowVisible($MainWindow)
        } "No selector appeared for $($Case.name); possible WebView2 deadlock."
        if (-not [YomiMadoUiNative]::Responding($MainWindow)) { throw "UI froze for $($Case.name)." }
        $script:Selector = [IntPtr]::Zero
        Wait-Check {
            foreach ($Handle in [YomiMadoUiNative]::Windows($Process.Id)) {
                if ($Handle -eq $MainWindow) { continue }
                $Element = [System.Windows.Automation.AutomationElement]::FromHandle($Handle)
                $Names = ($Element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition) | ForEach-Object { $_.Current.Name }) -join ' '
                # The disposable runner has no manga reader. Whole Screen
                # should reach its draw-area fallback. Target the new edge
                # hint, not the removed instruction card or a loading webview.
                if ($Names -match 'Esc cancel' -and $Names -match 'Drag (to capture|around pages)') {
                    $script:Selector = $Handle
                    return $true
                }
            }
            return $false
        } "Selector UI did not load for $($Case.name)."
        if (-not [YomiMadoUiNative]::SetForegroundWindow($Selector)) { throw 'Cannot focus capture selector.' }
        Wait-Check { [YomiMadoUiNative]::GetForegroundWindow() -eq $Selector } 'Capture selector did not receive foreground focus.'
        [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
        Wait-Check {
            [YomiMadoUiNative]::IsWindowVisible($MainWindow) -and
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
