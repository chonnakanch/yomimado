# Private candidate only. This script has no tag, release or approval operation.
param([switch]$Prepare, [switch]$Onnx)
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
    $CommandLog = Join-Path $Build 'build-last-command.log'
    & $Program @Arguments 2>&1 | Tee-Object -FilePath $CommandLog
    if ($LASTEXITCODE -ne 0) {
        if ($env:GITHUB_ACTIONS -eq 'true') {
            # Native stdout bypasses PowerShell transcription on hosted runners.
            # Retain the failing command's actual output, already public in logs.
            $Tail = (Get-Content $CommandLog -Tail 50) -join "`n"
            if ($Tail.Length -gt 12000) { $Tail = $Tail.Substring($Tail.Length - 12000) }
            $Encoded = $Tail.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
            Write-Host "::error title=Windows build command failed::$Encoded"
        }
        throw "$Program exited with $LASTEXITCODE"
    }
}
if (-not $IsWindows -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
    throw 'Build requires native Windows x64 PowerShell 7.'
}
if ((git status --porcelain)) { throw 'Commit changes before building a candidate.' }
$Revision = git rev-parse HEAD
if ($Prepare) {
    New-Item -ItemType Directory -Force $Build | Out-Null
    # Fail on moved daily dictionaries before compiling Python/Rust or freezing.
    Invoke-Checked python @('scripts/windows_release.py', 'download-assets')
    Invoke-Checked python @('scripts/windows_release.py', 'download')
    Invoke-Checked python @('scripts/windows_python.py')
    $RuntimePython = Join-Path $Build 'Python-3.11.17/PCbuild/amd64/python.exe'
    if ($Onnx) {
        # The baseline is export-only. No Torch package enters the frozen runtime.
        Invoke-Checked $RuntimePython @('scripts/prepare_onnx_probe.py', '--runtime', (Join-Path $Build 'venv'), '--baseline', (Join-Path $Build 'onnx-baseline'))
        # Reuse the independently verified focused IPP-free build recipe.
        # Prebuilt Torch remains export-only; no Torch source compilation occurs.
        Invoke-Checked $RuntimePython @('scripts/build-opencv-windows.py', (Join-Path $Service 'build/onnx-prototype/smoke-detector.onnx'))
        Invoke-Checked $Python @('scripts/windows_opencv_runtime.py', 'replace')
        # Small binding only: retain its deliberately resolved offline Cargo graph.
        Invoke-Checked $Python @('scripts/windows_sudachi_runtime.py', 'build')
    } else {
        Invoke-Checked $RuntimePython @('-m', 'venv', (Join-Path $Build 'venv'))
        # Installing local, hash-verified inputs must not consult an index or resolve.
        $Inputs = Get-Content (Join-Path $Service 'windows-inputs.json') -Raw | ConvertFrom-Json
        $Files = @($Inputs.packages | ForEach-Object { Join-Path $Build "inputs/$($_.filename)" })
        Invoke-Checked $Python (@('-m', 'pip', 'install', '--no-index', '--no-deps', '--no-build-isolation') + $Files)
    }
    Invoke-Checked $Python @('-m', 'pip', 'install', '--no-index', '--no-deps', '--no-build-isolation', $Service)
    Invoke-Checked $Python @('-m', 'pip', 'check')
}
if (-not (Test-Path $Python)) { throw 'Prepare the isolated Windows runtime first.' }
$env:PYTHONPATH = $Service
Invoke-Checked $Python @('-m', 'pytest', 'services/ocr/tests')
Invoke-Checked $Python @('-m', 'unittest', 'discover', '-s', 'scripts/tests', '-p', 'test_windows*.py')
Invoke-Checked npm @('ci', '--prefix', 'apps/desktop')
Invoke-Checked npm @('test', '--prefix', 'apps/desktop')
Invoke-Checked cargo @('test', '--locked', '--manifest-path', 'apps/desktop/src-tauri/Cargo.toml')
Invoke-Checked $Python @('scripts/windows_release.py', 'assets')
$Detector = Join-Path $Resources 'assets/comic-text-detector'
$Freeze = @('-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--console', '--name', 'yomimado-ocr', '--distpath', (Join-Path $Build 'dist'), '--workpath', (Join-Path $Build 'pyinstaller'), '--specpath', $Build, '--paths', $Service, '--paths', $Detector, '--hidden-import', 'backports.tarfile', '--collect-all', 'unidic_lite', '--collect-all', 'sudachidict_core')
if ($Onnx) {
    $Baseline = Join-Path $Build 'onnx-baseline/Scripts/python.exe'
    $Assets = Join-Path $Resources 'assets'
    $Graphs = Join-Path $Assets 'onnx'
    Invoke-Checked $Baseline @('scripts/export_onnx_probe.py', '--ocr-model', (Join-Path $Assets 'manga-ocr-base'), '--translation-model', (Join-Path $Assets 'opus-mt-ja-en'), '--output', $Graphs)
    Invoke-Checked $Baseline @('scripts/check_onnx_probe.py', '--ocr-model', (Join-Path $Assets 'manga-ocr-base'), '--translation-model', (Join-Path $Assets 'opus-mt-ja-en'), '--detector-repo', $Detector, '--detector-model', (Join-Path $Service 'build/onnx-prototype/smoke-detector.onnx'), '--exported', $Graphs, '--output', (Join-Path $Build 'onnx-comparison'), '--onnx-python', $Python, '--onnx-pythonpath', $Service)
    # collect-all also copies vendor example ONNX models. Collect Python/native
    # runtime inputs and metadata without those unneeded datasets.
    $Freeze += @('--paths', $PSScriptRoot, '--collect-binaries', 'onnxruntime', '--collect-submodules', 'onnxruntime', '--copy-metadata', 'onnxruntime', '--hidden-import', 'pyclipper', '--hidden-import', 'shapely.geometry')
    foreach ($Name in @('torch', 'torchvision', 'manga_ocr', 'torchsummary', 'onnx', 'ml_dtypes')) { $Freeze += @('--exclude-module', $Name) }
} else {
    Invoke-Checked $Python @('-c', 'import sys; sys.path.insert(0,sys.argv[1]); from inference import TextDetector; import torch; assert torch.version.cuda is None', $Detector)
    $Freeze += @('--hidden-import', 'inference', '--collect-all', 'manga_ocr')
}
foreach ($Name in @('bert','vit','vision_encoder_decoder','marian')) { $Freeze += @('--collect-submodules', "transformers.models.$Name") }
foreach ($Name in @('pytest','tensorflow','wandb','hf_xet','torch.utils.tensorboard')) { $Freeze += @('--exclude-module', $Name) }
$Entry = if ($Onnx) { 'windows_onnx_packaged_main.py' } else { 'windows_packaged_main.py' }
$Freeze += (Join-Path $Service $Entry)
Invoke-Checked $Python $Freeze
$Runtime = Join-Path $Resources 'runtime'
if (Test-Path $Runtime) { Remove-Item $Runtime -Recurse -Force }
Copy-Item (Join-Path $Build 'dist/yomimado-ocr') $Runtime -Recurse
# Remove unused native codec extensions before inventory and exact installed smoke.
Invoke-Checked $Python @('scripts/windows_release.py', 'prune')
Invoke-Checked $Python @('scripts/windows_vc_runtime.py', 'stage')
if (-not $Onnx) { Invoke-Checked $Python @('scripts/create-manga-ocr-warmup.py', (Join-Path $Runtime '_internal/manga_ocr/assets/example.jpg')) }
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
Copy-Item (Join-Path $Root 'docs/windows-native-replacement.md') $Notices
Copy-Item (Join-Path $Root 'docs/windows-numpy-runtime.md') $Notices
Copy-Item (Join-Path $Root 'docs/windows-sudachi-runtime.md') $Notices
Copy-Item (Join-Path $Root 'docs/windows-microsoft-runtime.md') $Notices
if ($Onnx) {
    Copy-Item (Join-Path $Root 'scripts/onnx-probe-inputs.json') $Notices
    Copy-Item (Join-Path $Resources 'assets/onnx/export.json') (Join-Path $Notices 'windows-onnx-export.json')
    Copy-Item (Join-Path $Root 'THIRD_PARTY_LICENSES/windows-onnx-probe') (Join-Path $Notices 'windows-onnx-inputs') -Recurse -Force
    Invoke-Checked $Python @('scripts/windows_opencv_runtime.py', 'retain')
    Invoke-Checked $Python @('scripts/windows_onnx_sources.py')
    Invoke-Checked $Python @('scripts/windows_native_sources.py')
    Invoke-Checked $Python @('scripts/windows_sudachi_runtime.py', 'retain')
}
[IO.File]::WriteAllText((Join-Path $Notices 'project-revision.txt'), "$Revision`n")
@{mode='private-test'; authenticodeSigned=$false; publicDistributionApproved=$false; installedAppVerified=$false} | ConvertTo-Json | Set-Content (Join-Path $Notices 'distribution.json') -Encoding utf8NoBOM
# Retain actual frozen inputs even if later notice/source collection fails.
Invoke-Checked $Python @('scripts/windows_release.py', 'inventory')
$Backend = if ($Onnx) { 'onnx' } else { 'torch' }
Invoke-Checked $Python @('scripts/windows_release.py', 'configuration', '--backend', $Backend)
Invoke-Checked $Python @('scripts/windows_notices.py')
Invoke-Checked $Python @('scripts/windows_release.py', 'seal')
Invoke-Checked $Python @('scripts/windows_release.py', 'verify')
$env:VITE_OCR_URL = 'http://127.0.0.1:8766'
Invoke-Checked npm @('--prefix', 'apps/desktop', 'run', 'tauri', 'build', '--', '--config', 'src-tauri/tauri.windows-release.conf.json', '--target', 'x86_64-pc-windows-msvc', '--bundles', 'nsis', '--ci', '--', '--locked')
Invoke-Checked $Python @('scripts/windows_release.py', 'restore-generated', '--revision', $Revision)
if ((git rev-parse HEAD) -ne $Revision -or (git status --porcelain)) { throw 'Source changed during build.' }
Write-Host 'Built private NSIS candidate. Install, inventory and smoke it before exporting.'
