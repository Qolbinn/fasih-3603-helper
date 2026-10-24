# ==============================================================================
# FASIH 3603 HELPER - BROWSER EXTENSION PACKAGER SCRIPT
# ==============================================================================
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
$outputZip = Join-Path $rootDir "Fasih_3603_Helper_Extension.zip"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Mengemas Ekstensi Browser FASIH 3603 Helper (Manifest V3)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (Test-Path $outputZip) {
    Remove-Item -Force $outputZip
    Write-Host "Menghapus paket zip lama..." -ForegroundColor Yellow
}

# Berkas dan folder yang disertakan dalam ekstensi
$itemsToInclude = @(
    "manifest.json",
    "background",
    "content",
    "sidepanel",
    "libs",
    "icons"
)

# Buat folder sementara untuk packaging bersih
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("fasih_ext_pack_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null

try {
    foreach ($item in $itemsToInclude) {
        $sourcePath = Join-Path $scriptDir $item
        if (Test-Path $sourcePath) {
            Copy-Item -Path $sourcePath -Destination $tempDir -Recurse -Force
        } else {
            Write-Warning "Item '$item' tidak ditemukan di folder ekstensi!"
        }
    }

    Write-Host "Mengompresi ke $outputZip..." -ForegroundColor Green
    Compress-Archive -Path "$tempDir\*" -DestinationPath $outputZip -CompressionLevel Optimal

    $zipSize = [Math]::Round(((Get-Item $outputZip).Length / 1KB), 1)
    Write-Host "Berhasil dikemas: $outputZip ($zipSize KB)" -ForegroundColor Green
    Write-Host "Ekstensi siap didistribusikan ke staf/petugas untuk di-load di Chrome / Edge!" -ForegroundColor Cyan
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
