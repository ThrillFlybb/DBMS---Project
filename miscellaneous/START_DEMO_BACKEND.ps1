Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Demo Backend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will start a demo backend server on port 5001" -ForegroundColor Yellow
Write-Host "that demonstrates the REST API functionality." -ForegroundColor Yellow
Write-Host ""
Write-Host "To use it:" -ForegroundColor Green
Write-Host "1. Keep this window open" -ForegroundColor White
Write-Host "2. Go to Settings in the main app" -ForegroundColor White
Write-Host "3. Change Data Source to 'REST'" -ForegroundColor White
Write-Host "4. Set Backend URL to: http://localhost:5001" -ForegroundColor White
Write-Host "5. Save settings" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

python demo_backend.py

Read-Host "Press Enter to exit"

