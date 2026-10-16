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
Add-Type -AssemblyName UIAutomationProvider
$References = @(
    [System.Windows.Application].Assembly.Location,
    [System.Windows.Media.Visual].Assembly.Location,
    [System.Windows.DependencyObject].Assembly.Location,
    [System.Xaml.XamlReader].Assembly.Location,
    [System.Windows.Automation.Provider.IExpandCollapseProvider].Assembly.Location,
    [System.Windows.Automation.ExpandCollapseState].Assembly.Location
)
Add-Type -ReferencedAssemblies $References -OutputAssembly $Executable -OutputType WindowsApplication -TypeDefinition @'
using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Automation;
using System.Windows.Automation.Peers;
using System.Windows.Automation.Provider;
// Match WebView2's aria-expanded menu button: ExpandCollapse, without Invoke.
public sealed class ExpandMenuButton : Button {
    public Action OpenMenu;
    public Action CloseMenu;
    public Func<bool> IsMenuOpen;
    protected override AutomationPeer OnCreateAutomationPeer() { return new ExpandMenuPeer(this); }
}
public sealed class ExpandMenuPeer : ButtonAutomationPeer, IExpandCollapseProvider {
    public ExpandMenuPeer(ExpandMenuButton owner) : base(owner) { }
    public override object GetPattern(PatternInterface pattern) {
        if (pattern == PatternInterface.Invoke) return null;
        if (pattern == PatternInterface.ExpandCollapse) return this;
        return base.GetPattern(pattern);
    }
    public ExpandCollapseState ExpandCollapseState {
        get {
            var button = (ExpandMenuButton)Owner;
            return (ExpandCollapseState)button.Dispatcher.Invoke(new Func<ExpandCollapseState>(() =>
                button.IsMenuOpen() ? ExpandCollapseState.Expanded : ExpandCollapseState.Collapsed));
        }
    }
    public void Expand() {
        var button = (ExpandMenuButton)Owner;
        button.Dispatcher.BeginInvoke(button.OpenMenu);
    }
    public void Collapse() {
        var button = (ExpandMenuButton)Owner;
        button.Dispatcher.BeginInvoke(button.CloseMenu);
    }
}
public static class SyntheticYomiMado {
    private static bool quitting;
    [STAThread]
    public static void Main(string[] args) {
        var app = new Application { ShutdownMode=ShutdownMode.OnExplicitShutdown };
        var toolbar = new Window { Title="YomiMado toolbar", ShowInTaskbar=false, Width=600, Height=110, Left=80, Top=80 };
        toolbar.Closing += delegate(object sender, System.ComponentModel.CancelEventArgs e) { if (!quitting) e.Cancel=true; };
        var settings = new Window { Title="YomiMado - Settings", Width=600, Height=300 };
        var settingsContent = new StackPanel();
        settingsContent.Children.Add(new Button { Content="Select detector model file", Width=250, Height=30 });
        settingsContent.Children.Add(new System.Windows.Controls.Primitives.ToggleButton {
            Content="Selected Area", IsChecked=true, Width=150, Height=30
        });
        settings.Content = settingsContent;
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
        Button more = args.Length > 0 ? new ExpandMenuButton {
            OpenMenu=() => menu.Show(), CloseMenu=() => menu.Hide(), IsMenuOpen=() => menu.IsVisible
        } : new Button();
        more.Content="More actions"; more.Width=150; more.Height=30;
        more.Click += delegate { menu.Show(); };
        toolbar.Content = more;
        app.Run(toolbar);
    }
}
'@
$First = $null
$Other = $null
try {
    $First = Start-Process $Executable -ArgumentList 'expand-only' -PassThru
    $Other = Start-Process $Executable -PassThru
    $Toolbar = Wait-YomiMadoWindow $First 'YomiMado toolbar'
    $OtherToolbar = Wait-YomiMadoWindow $Other 'YomiMado toolbar'
    if ($Toolbar -eq $OtherToolbar) { throw 'Window discovery escaped its process.' }
    Wait-YomiMadoUi $First { $null -ne (Get-YomiMadoAction $Toolbar 'More actions') } 'Expand-only menu button did not load.'
    $ExpandOnly = Get-YomiMadoAction $Toolbar 'More actions'
    $Pattern = $null
    if ($ExpandOnly.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$Pattern)) {
        throw 'Expand-only fixture unexpectedly exposes Invoke.'
    }
    if (-not $ExpandOnly.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern, [ref]$Pattern)) {
        throw 'Expand-only fixture does not expose ExpandCollapse.'
    }
    Invoke-YomiMadoMenuAction $First 'Settings'
    $Settings = Wait-YomiMadoWindow $First 'YomiMado*Settings'
    Wait-YomiMadoUi $First { $null -ne (Get-YomiMadoAction $Settings 'Select detector model file') } 'Settings action was not found in its own window.'
    $Scan = Get-YomiMadoAction $Settings 'Selected Area'
    $Pattern = $null
    if ($Scan.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$Pattern)) {
        throw 'Toggle-only fixture unexpectedly exposes Invoke.'
    }
    if (-not $Scan.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern, [ref]$Pattern)) {
        throw 'Toggle-only fixture does not expose Toggle.'
    }
    Invoke-YomiMadoAction $Settings 'Selected Area'
    Wait-YomiMadoUi $First { $Pattern.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::Off } 'Pressed scan action did not toggle.'
    Invoke-YomiMadoAction $Settings 'Selected Area'
    Wait-YomiMadoUi $First { $Pattern.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::On } 'Unpressed scan action did not toggle.'
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
    Write-Host 'Windows UI driver: ExpandCollapse/Invoke menus, Toggle scan actions, PID-scoped discovery, Settings close/reopen and explicit Quit passed.'
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
