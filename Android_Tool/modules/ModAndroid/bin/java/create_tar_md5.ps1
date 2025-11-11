# ============================================================================
# Script tạo file AP.tar.md5 chuẩn cho Odin
# Sử dụng: .\create_tar_md5.ps1 [input_file] [output_name]
# Default: input=system.img.lz4, output=AP
# ============================================================================

param(
    [string]$InputFile = "system.img.lz4",
    [string]$OutputName = "AP"
)

$OutputTar = "$OutputName.tar"
$OutputTarMd5 = "$OutputName.tar.md5"

# ============================================================================
# Kiểm tra file input
# ============================================================================
Write-Host "[*] Checking input file: $InputFile" -ForegroundColor Cyan
if (-not (Test-Path $InputFile)) {
    Write-Host "[!] ERROR: File $InputFile not found!" -ForegroundColor Red
    exit 1
}
Write-Host "[+] Input file found: $InputFile" -ForegroundColor Green

# ============================================================================
# Tạo file tar với format ustar
# ============================================================================
Write-Host "[*] Creating tar file: $OutputTar" -ForegroundColor Cyan
tar -H ustar -c -f $OutputTar $InputFile

if (-not (Test-Path $OutputTar)) {
    Write-Host "[!] ERROR: Failed to create $OutputTar!" -ForegroundColor Red
    exit 1
}
Write-Host "[+] Tar file created: $OutputTar" -ForegroundColor Green

# ============================================================================
# Tính MD5 hash
# ============================================================================
Write-Host "[*] Calculating MD5 hash..." -ForegroundColor Cyan
$md5Hash = (Get-FileHash $OutputTar -Algorithm MD5).Hash.ToLower()
Write-Host "[+] MD5: $md5Hash" -ForegroundColor Green

# ============================================================================
# Tạo file AP.tar.md5
# ============================================================================
Write-Host "[*] Creating $OutputTarMd5..." -ForegroundColor Cyan
"$md5Hash  $OutputTar" | Out-File -Encoding ASCII -FilePath $OutputTarMd5

if (-not (Test-Path $OutputTarMd5)) {
    Write-Host "[!] ERROR: Failed to create $OutputTarMd5!" -ForegroundColor Red
    exit 1
}

# ============================================================================
# Hoàn tất
# ============================================================================
Write-Host ""
Write-Host "[=] SUCCESS!" -ForegroundColor Green
Write-Host "[=] Created: $OutputTar" -ForegroundColor Yellow
Write-Host "[=] Created: $OutputTarMd5" -ForegroundColor Yellow
Write-Host "[=] MD5: $md5Hash" -ForegroundColor Cyan
Write-Host ""















