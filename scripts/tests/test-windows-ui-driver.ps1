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
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -OutputAssembly $Executable -OutputType WindowsApplication -TypeDefinition @'
using System;
using System.Drawing;
using System.Windows.Forms;
public static class SyntheticYomiMado {
    private static bool quitting;
    private static Form toolbar;
    private static Form menu;
    private static Form settings;
    [STAThread]
    public static void Main() {
        Application.EnableVisualStyles();
        toolbar = new Form { Text="YomiMado toolbar", ShowInTaskbar=false, Width=600, Height=110 };
        toolbar.StartPosition = FormStartPosition.Manual;
        toolbar.Location = new Point(80, 80);
        toolbar.FormClosing += delegate(object sender, FormClosingEventArgs e) { if (!quitting) e.Cancel=true; };
        settings = new Form { Text="YomiMado - Settings", Width=600, Height=300 };
        settings.Controls.Add(new Button { Text="Select detector model file", Width=250 });
        settings.FormClosing += delegate(object sender, FormClosingEventArgs e) {
            if (!quitting) { e.Cancel=true; settings.Hide(); }
        };
        menu = new Form { Text="YomiMado More actions", Width=320, Height=120, ShowInTaskbar=false };
        var choices = new MenuStrip();
        var open = new ToolStripMenuItem("Settings");
        open.Click += delegate { menu.Hide(); settings.Show(); };
        var quit = new ToolStripMenuItem("Quit YomiMado");
        quit.Click += delegate { quitting=true; Application.Exit(); };
        choices.Items.Add(open);
        choices.Items.Add(quit);
        menu.Controls.Add(choices);
        var more = new Button { Text="More actions", Width=150 };
        more.Click += delegate { menu.Show(); };
        toolbar.Controls.Add(more);
        Application.Run(toolbar);
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
} finally {
    foreach ($Owned in @($First, $Other)) {
        if ($null -ne $Owned) {
            $Owned.Refresh()
            if (-not $Owned.HasExited) { Stop-Process -Id $Owned.Id -ErrorAction SilentlyContinue }
        }
    }
    Remove-Item $Work -Recurse -Force -ErrorAction SilentlyContinue
}
