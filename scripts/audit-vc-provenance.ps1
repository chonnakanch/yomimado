# Read-only provenance inspection. No DLL is executed, installed or changed.
param([string]$Output = 'services/ocr/build/windows-vc-provenance.json')
$ErrorActionPreference = 'Stop'
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ($LASTEXITCODE -or -not $vs) { throw 'Visual Studio installation is unavailable' }
$redist = Join-Path $vs 'VC/Redist/MSVC'
if (-not (Test-Path $redist)) { throw 'Canonical VC redistributable directory is unavailable' }
$files = @(Get-ChildItem "$redist/*/x64/Microsoft.VC*.CRT/*.dll" -File | Sort-Object FullName)
if (-not $files.Count) { throw 'No canonical x64 VC CRT files found' }
$binaries = @(
    foreach ($file in $files) {
        $data = [IO.File]::ReadAllBytes($file.FullName)
        if ($data.Length -lt 64 -or $data[0] -ne 77 -or $data[1] -ne 90) { throw 'Invalid PE header' }
        $offset = [BitConverter]::ToInt32($data, 60)
        if ($offset -lt 0 -or $offset + 6 -gt $data.Length -or [BitConverter]::ToUInt32($data, $offset) -ne 17744) { throw 'Invalid PE signature' }
        $machine = [BitConverter]::ToUInt16($data, $offset + 4)
        if ($machine -ne 34404) { throw 'Canonical CRT input is not AMD64' }
        [ordered]@{
            path = $file.FullName
            name = $file.Name
            sha256 = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
            fileVersion = $file.VersionInfo.FileVersion
            originalFilename = $file.VersionInfo.OriginalFilename
            machine = '0x8664'
        }
    }
)
$reference = Get-Content docs/windows-vc-reference.json -Raw | ConvertFrom-Json
$matches = @(
    foreach ($inputFile in $reference.files) {
        [ordered]@{
            referencePath = $inputFile.path
            referenceSha256 = $inputFile.sha256
            canonicalMatches = @($binaries | Where-Object { $_.sha256 -eq $inputFile.sha256 } | ForEach-Object { $_.path })
        }
    }
)
$result = [ordered]@{
    revision = (git rev-parse HEAD)
    imageOS = $env:ImageOS
    imageVersion = $env:ImageVersion
    visualStudio = $vs
    canonicalRedistRoot = $redist
    canonicalFiles = $binaries
    referenceInventory = $reference.inventory
    referenceMatches = $matches
    sourceCoverageApproved = $false
    publicDistributionApproved = $false
    licensedDistributorConfirmed = $false
}
New-Item (Split-Path $Output -Parent) -ItemType Directory -Force | Out-Null
$result | ConvertTo-Json -Depth 10 | Set-Content $Output -Encoding utf8
'Read-only canonical VC runtime provenance recorded. Redistribution rights and the exact installer gate remain open.' | Add-Content $env:GITHUB_STEP_SUMMARY
$matches | ConvertTo-Json -Depth 5 | Add-Content $env:GITHUB_STEP_SUMMARY
