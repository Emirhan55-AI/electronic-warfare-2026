$ErrorActionPreference = "Stop"
$secret = Read-Host "ZedBoard petalinux parolası" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $env:TEKNO_BOARD_SETUP_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    python output/parameter-review-20260918/board_access.py output/parameter-review-20260918/stage-v3.json
    if ($LASTEXITCODE -ne 0) { throw "Kart dosya hazırlığı başarısız." }
    python output/parameter-review-20260918/board_access.py output/parameter-review-20260918/activate-v3.json
    if ($LASTEXITCODE -ne 0) { throw "Kart hizmeti etkinleştirilemedi; geri alma planı çalıştırıldı." }
    Write-Host "CANLI HİZMET GÜNCELLENDİ" -ForegroundColor Green
}
finally {
    Remove-Item Env:TEKNO_BOARD_SETUP_PASSWORD -ErrorAction SilentlyContinue
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}
