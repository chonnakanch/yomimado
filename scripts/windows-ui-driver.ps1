# Shared Windows PowerShell 5.1 UI driver for source/release smoke checks.
# Resolve visible windows by owned PID/title, including the taskbar-skipping toolbar.
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
    public static bool CloseWindow(IntPtr window) {
        return PostMessage(window, 0x0010, IntPtr.Zero, IntPtr.Zero); // WM_CLOSE
    }
    public static bool Responding(IntPtr window) {
        IntPtr result;
        return SendMessageTimeout(window, 0, IntPtr.Zero, IntPtr.Zero, 2, 1000, out result) != IntPtr.Zero;
    }
}
'@


function Wait-YomiMadoUi {
    param([Diagnostics.Process]$Process, [scriptblock]$Check, [string]$Failure, [int]$Seconds=40)
    $Deadline = (Get-Date).AddSeconds($Seconds)
    do {
        $Process.Refresh()
        if ($Process.HasExited) { throw "Desktop exited during UI check: $($Process.ExitCode)" }
        if (& $Check) { return }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $Deadline)
    throw $Failure
}

function Get-YomiMadoWindow {
    param([Diagnostics.Process]$Process, [string]$Title)
    foreach ($Handle in [YomiMadoUiNative]::Windows($Process.Id)) {
        if ([YomiMadoUiNative]::Text($Handle) -like $Title) { return $Handle }
    }
    return [IntPtr]::Zero
}

function Wait-YomiMadoWindow {
    param([Diagnostics.Process]$Process, [string]$Title)
    Wait-YomiMadoUi $Process {
        $Handle = Get-YomiMadoWindow $Process $Title
        $Handle -ne [IntPtr]::Zero -and [YomiMadoUiNative]::Responding($Handle)
    } "Window did not become responsive: $Title"
    return Get-YomiMadoWindow $Process $Title
}

function Get-YomiMadoAction {
    param([IntPtr]$Window, [string]$Name)
    if ($Window -eq [IntPtr]::Zero) { return $null }
    $Element = [System.Windows.Automation.AutomationElement]::FromHandle($Window)
    $Types = New-Object System.Windows.Automation.OrCondition -ArgumentList @(
        (New-Object System.Windows.Automation.PropertyCondition -ArgumentList @([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)),
        (New-Object System.Windows.Automation.PropertyCondition -ArgumentList @([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::MenuItem))
    )
    $Condition = New-Object System.Windows.Automation.AndCondition -ArgumentList @(
        $Types,
        (New-Object System.Windows.Automation.PropertyCondition -ArgumentList @([System.Windows.Automation.AutomationElement]::NameProperty, $Name))
    )
    return $Element.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $Condition)
}

function Invoke-YomiMadoAction {
    param([IntPtr]$Window, [string]$Name)
    $Action = Get-YomiMadoAction $Window $Name
    if ($null -eq $Action -or -not $Action.Current.IsEnabled) { throw "Action is unavailable: $Name" }
    $Invoke = $null
    if (-not $Action.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$Invoke)) {
        throw "Action does not expose Invoke: $Name"
    }
    $Invoke.Invoke()
}

function Open-YomiMadoMenu {
    param([Diagnostics.Process]$Process)
    $Menu = Get-YomiMadoWindow $Process 'YomiMado More actions'
    if ($Menu -ne [IntPtr]::Zero) { return $Menu }
    $Toolbar = Wait-YomiMadoWindow $Process 'YomiMado toolbar'
    if (-not [YomiMadoUiNative]::SetForegroundWindow($Toolbar)) { throw 'Cannot focus toolbar.' }
    Wait-YomiMadoUi $Process {
        $Action = Get-YomiMadoAction $Toolbar 'More actions'
        $null -ne $Action -and $Action.Current.IsEnabled
    } 'Toolbar actions did not load.'
    $Action = Get-YomiMadoAction $Toolbar 'More actions'
    $Expand = $null
    # WebView2 exposes aria-expanded menu buttons through ExpandCollapse.
    # Ordinary buttons (including the WPF fixture) can expose Invoke instead.
    if ($Action.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern, [ref]$Expand)) {
        $Expand.Expand()
    } else {
        Invoke-YomiMadoAction $Toolbar 'More actions'
    }
    return Wait-YomiMadoWindow $Process 'YomiMado More actions'
}

function Invoke-YomiMadoMenuAction {
    param([Diagnostics.Process]$Process, [string]$Name)
    $Menu = Open-YomiMadoMenu $Process
    Wait-YomiMadoUi $Process {
        $Action = Get-YomiMadoAction $Menu $Name
        $null -ne $Action -and $Action.Current.IsEnabled
    } "Menu action did not become available: $Name"
    Invoke-YomiMadoAction $Menu $Name
}

function Stop-YomiMadoViaMenu {
    param([Diagnostics.Process]$Process)
    Invoke-YomiMadoMenuAction $Process 'Quit YomiMado'
    if (-not $Process.WaitForExit(15000)) { throw 'Desktop did not exit after explicit Quit.' }
}
