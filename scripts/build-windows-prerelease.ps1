# Private candidate only. This script has no tag, release or approval operation.
param([switch]$Prepare)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Service = Join-Path $Root 'services/ocr'
$Build = Join-Path $Service 'build/windows'
$Resources = Join-Path $Root 'apps/desktop/src-tauri/resources/ocr'
$Python = Join-Path $Build 'venv/Scripts/python.exe'
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program exited with $LASTEXITCODE" }
}
if (-not $IsWindows -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Build requires native Windows x64 PowerShell 7.'
}
if ((git status --porcelain)) { throw 'Commit changes before building a candidate.' }
$Revision = git rev-parse HEAD
if ($Prepare) {
    New-Item -ItemType Directory -Force $Build | Out-Null
    Invoke-Checked python @('scripts/windows_release.py', 'download')
    Invoke-Checked python @('scripts/windows_python.py')
    $RuntimePython = Join-Path $Build 'Python-3.11.17/PCbuild/amd64/python.exe'
    Invoke-Checked $RuntimePython @('-m', 'venv', (Join-Path $Build 'venv'))
    # Installing local, hash-verified inputs must not consult an index or resolve.
    $Inputs = Get-Content (Join-Path $Service 'windows-inputs.json') -Raw | ConvertFrom-Json
    $Files = @($Inputs.packages | ForEach-Object { Join-Path $Build "inputs/$($_.filename)" })
    Invoke-Checked $Python (@('-m', 'pip', 'install', '--no-index', '--no-deps', '--no-build-isolation') + $Files)
    Invoke-Checked $Python @('-m', 'pip', 'install', '--no-index', '--no-deps', '--no-build-isolation', $Service)
    Invoke-Checked $Python @('-m', 'pip', 'check')
}
if (-not (Test-Path $Python)) { throw 'Prepare the isolated Windows runtime first.' }
Invoke-Checked $Python @('-m', 'pytest', 'services/ocr/tests')
Invoke-Checked $Python @('-m', 'unittest', 'discover', '-s', 'scripts/tests', '-p', 'test_windows*.py')
Invoke-Checked npm @('ci', '--prefix', 'apps/desktop')
Invoke-Checked npm @('test', '--prefix', 'apps/desktop')
Invoke-Checked cargo @('test', '--locked', '--manifest-path', 'apps/desktop/src-tauri/Cargo.toml')
Invoke-Checked $Python @('scripts/windows_release.py', 'assets')
$Detector = Join-Path $Resources 'assets/comic-text-detector'
Invoke-Checked $Python @('-c', 'import sys; sys.path.insert(0,sys.argv[1]); from inference import TextDetector; import torch; assert torch.version.cuda is None', $Detector)
$Freeze = @('-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--console', '--name', 'yomimado-ocr', '--distpath', (Join-Path $Build 'dist'), '--workpath', (Join-Path $Build 'pyinstaller'), '--specpath', $Build, '--paths', $Service, '--paths', $Detector, '--hidden-import', 'inference', '--hidden-import', 'backports.tarfile', '--collect-all', 'manga_ocr', '--collect-all', 'unidic_lite', '--collect-all', 'sudachidict_core')
foreach ($Name in @('bert','vit','vision_encoder_decoder','marian')) { $Freeze += @('--collect-submodules', "transformers.models.$Name") }
foreach ($Name in @('pytest','tensorflow','wandb','hf_xet','torch.testing','torch.utils.tensorboard')) { $Freeze += @('--exclude-module', $Name) }
$Freeze += (Join-Path $Service 'windows_packaged_main.py')
Invoke-Checked $Python $Freeze
$Runtime = Join-Path $Resources 'runtime'
if (Test-Path $Runtime) { Remove-Item $Runtime -Recurse -Force }
Copy-Item (Join-Path $Build 'dist/yomimado-ocr') $Runtime -Recurse
# The optional FFmpeg plugin is unnecessary for still-image DNN inference.
# Remove it from the frozen input, not from the original wheel/source evidence.
Get-ChildItem $Runtime -Recurse -File -Filter 'opencv_videoio_ffmpeg*.dll' | Remove-Item
Invoke-Checked $Python @('scripts/create-manga-ocr-warmup.py', (Join-Path $Runtime '_internal/manga_ocr/assets/example.jpg'))
$Notices = Join-Path $Resources 'notices'
New-Item -ItemType Directory -Force $Notices | Out-Null
foreach ($Name in @('LICENSE', 'README.md', 'MODEL_CREDITS.md', 'ASSET_NOTICES.md', 'detector-inference.patch')) {
    $Path = if ($Name -eq 'LICENSE') { Join-Path $Root $Name } else { Join-Path $Root "THIRD_PARTY_LICENSES/$Name" }
    Copy-Item $Path $Notices
}
Copy-Item (Join-Path $Root 'THIRD_PARTY_LICENSES/upstream/assets') $Notices -Recurse -Force
Copy-Item (Join-Path $Service 'windows-inputs.json') $Notices
Copy-Item (Join-Path $Service 'windows-assets.json') $Notices
Copy-Item (Join-Path $Build 'python-build.json') $Notices
Copy-Item (Join-Path $Root 'docs/windows-source-review.md') $Notices
[IO.File]::WriteAllText((Join-Path $Notices 'project-revision.txt'), "$Revision`n")
@{mode='private-test'; authenticodeSigned=$false; publicDistributionApproved=$false; installedAppVerified=$false} | ConvertTo-Json | Set-Content (Join-Path $Notices 'distribution.json') -Encoding utf8NoBOM
Invoke-Checked $Python @('scripts/windows_notices.py')
Invoke-Checked $Python @('scripts/windows_release.py', 'configuration')
Invoke-Checked $Python @('scripts/windows_release.py', 'inventory')
Invoke-Checked $Python @('scripts/windows_release.py', 'seal')
Invoke-Checked $Python @('scripts/windows_release.py', 'verify')
$env:VITE_OCR_URL = 'http://127.0.0.1:8766'
Invoke-Checked npm @('--prefix', 'apps/desktop', 'run', 'tauri', 'build', '--', '--config', 'src-tauri/tauri.windows-release.conf.json', '--target', 'x86_64-pc-windows-msvc', '--bundles', 'nsis', '--ci', '--', '--locked')
if ((git rev-parse HEAD) -ne $Revision -or (git status --porcelain)) { throw 'Source changed during build.' }
Write-Host 'Built private NSIS candidate. Install, inventory and smoke it before exporting.'
