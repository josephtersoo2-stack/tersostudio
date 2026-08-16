# Syncs current repository changes to Google Drive mirror
$GdrivePath = "G:\My Drive\Tersuite Studio"

if (Test-Path $GdrivePath) {
    Write-Host "Syncing Tersuite Studio to Google Drive ($GdrivePath)..." -ForegroundColor Cyan
    git -C $GdrivePath pull origin main
    Write-Host "Google Drive is now up to date with main!" -ForegroundColor Green
} else {
    Write-Host "Google Drive path not found: $GdrivePath" -ForegroundColor Red
}
