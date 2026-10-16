# Exercise the real Win32/UI Automation driver against a synthetic desktop app.
# No installer, OCR service, model, screenshot or release credential is used.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'This UI driver test runs only on the disposable Windows x64 runner.'
}
. (Join-Path (Split-Path -Parent $PSScriptRoot) 'windows-ui-driver.ps1')
$Work = Join-Path $env:RUNNER_TEMP ('yomimado-ui-driver-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $Work | Out-Null
$Executable = Join-Path $Work 'synthetic-reader.exe'
# WPF provides standard Button/MenuItem automation peers. The runner's legacy
# WinForms provider reports dynamically compiled controls as generic panes.
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Xaml
$References = @(
    [System.Windows.Application].Assembly.Location,
    [System.Windows.Media.Visual].Assembly.Location,
    [System.Windows.DependencyObject].Assembly.Location,
    [System.Xaml.XamlReader].Assembly.Location
)
Add-Type -ReferencedAssemblies $References -OutputAssembly $Executable -OutputType WindowsApplication -TypeDefinition @'
using System;
using System.Windows;
using System.Windows.Controls;
public static class SyntheticYomiMado {
    private static bool quitting;
    [STAThread]
    public static void Main() {
        var app = new Application { ShutdownMode=ShutdownMode.OnExplicitShutdown };
        var toolbar = new Window { Title="YomiMado toolbar", ShowInTaskbar=false, Width=600, Height=110, Left=80, Top=80 };
        toolbar.Closing += delegate(object sender, System.ComponentModel.CancelEventArgs e) { if (!quitting) e.Cancel=true; };
        var settings = new Window { Title="YomiMado - Settings", Width=600, Height=300 };
        settings.Content = new Button { Content="Select detector model file", Width=250, Height=30 };
        settings.Closing += delegate(object sender, System.ComponentModel.CancelEventArgs e) {
            if (!quitting) { e.Cancel=true; settings.Hide(); }
        };
        var menu = new Window { Title="YomiMado More actions", Width=320, Height=120, ShowInTaskbar=false };
        var choices = new Menu { VerticalAlignment=VerticalAlignment.Top };
        var open = new MenuItem { Header="Settings" };
        open.Click += delegate { menu.Hide(); settings.Show(); };
        var quit = new MenuItem { Header="Quit YomiMado" };
        quit.Click += delegate { quitting=true; app.Shutdown(); };
        choices.Items.Add(open);
        choices.Items.Add(quit);
        menu.Content = choices;
        var more = new Button { Content="More actions", Width=150, Height=30 };
        more.Click += delegate { menu.Show(); };
        toolbar.Content = more;
        app.Run(toolbar);
    }
}
'@
$First = $null
$Other = $null
try {
    $First = Start-Process $Executable -PassThru
    $Other = Start-Process $Executable -PassThru
    $Toolbar = Wait-YomiMadoWindow $First 'YomiMado toolbar'
    $OtherToolbar = Wait-YomiMadoWindow $Other 'YomiMado toolbar'
    if ($Toolbar -eq $OtherToolbar) { throw 'Window discovery escaped its process.' }
    Invoke-YomiMadoMenuAction $First 'Settings'
    $Settings = Wait-YomiMadoWindow $First 'YomiMado*Settings'
    Wait-YomiMadoUi $First { $null -ne (Get-YomiMadoAction $Settings 'Select detector model file') } 'Settings action was not found in its own window.'
    if (-not [YomiMadoUiNative]::CloseWindow($Settings)) { throw 'Cannot send native Settings close.' }
    Wait-YomiMadoUi $First { -not [YomiMadoUiNative]::IsWindowVisible($Settings) } 'Native close did not hide Settings.'
    if (-not [YomiMadoUiNative]::IsWindowVisible($Toolbar)) { throw 'Settings close hid the toolbar.' }
    Invoke-YomiMadoMenuAction $First 'Settings'
    $Reopened = Wait-YomiMadoWindow $First 'YomiMado*Settings'
    if ($Reopened -ne $Settings) { throw 'Secondary window was not reused.' }
    Stop-YomiMadoViaMenu $First
    $Other.Refresh()
    if ($Other.HasExited) { throw 'Quit affected a different process.' }
    Stop-YomiMadoViaMenu $Other
    Write-Host 'Windows UI driver: PID-scoped toolbar/menu discovery, Settings close/reopen and explicit Quit passed.'
} catch {
    # Synthetic labels only: retain UIA/native diagnostics if the runner's
    # accessibility provider differs from the installed WebView2 provider.
    foreach ($Owned in @($First, $Other)) {
        if ($null -eq $Owned) { continue }
        foreach ($Handle in [YomiMadoUiNative]::Windows($Owned.Id)) {
            Write-Host "Synthetic window $($Owned.Id): $([YomiMadoUiNative]::Text($Handle))"
            Write-Host ([YomiMadoUiNative]::Controls($Handle) -join ' | ')
            $Element = [System.Windows.Automation.AutomationElement]::FromHandle($Handle)
            foreach ($Node in $Element.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) {
                Write-Host "$($Node.Current.ControlType.ProgrammaticName): $($Node.Current.Name)"
            }
        }
    }
    throw
} finally {
    foreach ($Owned in @($First, $Other)) {
        if ($null -ne $Owned) {
            $Owned.Refresh()
            if (-not $Owned.HasExited) { Stop-Process -Id $Owned.Id -ErrorAction SilentlyContinue }
        }
    }
    Remove-Item $Work -Recurse -Force -ErrorAction SilentlyContinue
}
